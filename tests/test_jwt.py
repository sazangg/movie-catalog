from pathlib import Path

import pytest
from catalog.api.api import create_app
from flask_jwt_extended import decode_token

VALID_CREDS = {"username": "admin", "password": "password123"}
INVALID_CREDS = {"username": "admin", "password": "wrongpass"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    from catalog.models import Catalog, Movie

    seed = Catalog()
    seed.add_movie(Movie(id=1, title="Titanic", year=1992))

    cfg = {
        "CATALOG_PATH": str(tmp_path / "movies.json"),
        "API_KEY": "supersecret123",
        "JWT_SECRET_KEY": "super-jwt-secret",
        "JWT_ACCESS_TOKEN_EXPIRES": False,
    }

    monkeypatch.setattr("catalog.api.api.load_catalog", lambda path: seed)

    exported = {}

    def fake_export(catalog: Catalog, path):
        exported["catalog"] = catalog
        exported["path"] = path

        from catalog.io_utils import export_catalog_to_json as real_export

        return real_export(catalog, path)

    monkeypatch.setattr(
        "catalog.api.movies.save_catalog",
        lambda catalog, path: fake_export(catalog, Path(path)),
    )

    app = create_app(cfg)

    app.testing = True
    client = app.test_client()
    client.app = app
    client.exported = exported
    return client


@pytest.mark.parametrize(
    "payload, status",
    [
        (VALID_CREDS, 200),
        (INVALID_CREDS, 401),
        ({}, 401),
    ],
)
def test_login_endpoint(client, payload, status):
    resp = client.post("/auth/login", json=payload)
    assert resp.status_code == status

    if status == 200:
        body = resp.get_json()
        assert "access_token" in body
        token = body["access_token"]

        with client.application.app_context():
            decoded = decode_token(token, allow_expired=True)

        assert decoded["sub"] == payload["username"]
        assert "roles" in decoded
    else:
        err = resp.get_json()
        assert "Bad credentials" in err.get("message", "") or err.get("error", "")


def test_protected_route_requires_jwt(client):
    resp = client.get("/movies")
    assert resp.status_code == 401
    body = resp.get_json()

    msg = body.get("message", "") or body.get("error", "")
    assert "authorization" in msg.lower() or "api key" in msg.lower()


def test_protected_route_with_malformed_jwt(client):
    headers = {"Authorization": "Bearer not.a.jwt"}
    resp = client.get("/movies", headers=headers)
    assert resp.status_code in (401, 422)
    body = resp.get_json()
    # either ‘Not enough segments’ or ‘Signature verification failed’
    assert body.get("message") or body.get("error")


def test_protected_route_with_valid_jwt_and_api_key(client):
    """With a valid token *and* API key header (if you still require it), access passes."""
    # 1) get a token
    login = client.post("/auth/login", json=VALID_CREDS)
    token = login.get_json()["access_token"]

    # 2) call protected endpoint
    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": client.application.config["API_KEY"],
    }
    resp = client.get("/movies", headers=headers)
    # OK even if the catalog is empty or has entries
    assert resp.status_code in (200, 404)
    data = resp.get_json()
    assert "movies" in data

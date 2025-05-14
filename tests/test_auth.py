from pathlib import Path

import pytest
from catalog.api.api import create_app

VALID_CREDS = {"username": "admin", "password": "password123"}


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

    login_resp = client.post("/auth/login", json=VALID_CREDS)
    assert login_resp.status_code == 200
    token = login_resp.get_json()["access_token"]

    client.environ_base = {
        **client.environ_base,
        "HTTP_AUTHORIZATION": f"Bearer {token}",
    }

    return client


@pytest.mark.parametrize(
    "method, path, data",
    [
        ("get", "/movies", None),
        ("post", "/movies", {"id": 42, "title": "Foo", "year": 2022}),
        ("put", "/movies/1", {"title": "Bar"}),
        ("delete", "/movies/1", None),
    ],
)
def test_requires_api_key(client, method, path, data):
    """
    Every protected route must 401 when NO X-API-Key header is sent,
    and also when the header is wrong.
    """
    # 1) No header → 401
    resp = getattr(client, method)(path, json=data)
    assert resp.status_code == 401
    body = resp.get_json()
    assert "Invalid or missing API key" in (
        body.get("message", "") or body.get("error", "")
    )

    # 2) Wrong header → 401
    headers = {"X-API-Key": "not-the-key"}
    resp = getattr(client, method)(path, json=data, headers=headers)
    assert resp.status_code == 401

    # 3) Correct header → passes (200 for GET/PUT/DELETE, 201 for POST)
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = getattr(client, method)(path, json=data, headers=headers)
    if method == "post":
        assert resp.status_code == 201
    elif method == "get":
        assert resp.status_code in (200, 404)  # if resource missing, still auth-passed
    else:
        # put/delete: either 200/204 or 404, but not 401
        assert resp.status_code in (200, 204, 404)

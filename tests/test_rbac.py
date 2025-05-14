# tests/test_rbac.py
import pytest
from flask_jwt_extended import create_access_token
from catalog.api.api import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # same fixture you already have in conftest.py...
    from catalog.models import Catalog, Movie

    seed = Catalog()
    seed.add_movie(Movie(id=1, title="Titanic", year=1992))
    cfg = {
        "CATALOG_PATH": str(tmp_path / "movies.json"),
        "API_KEY": "supersecret123",
        "JWT_SECRET_KEY": "super-jwt-secret",
        "JWT_ACCESS_TOKEN_EXPIRES": False,
    }
    # stub load_catalog so app.catalog == seed
    monkeypatch.setattr("catalog.api.api.load_catalog", lambda path: seed)
    # stub save_catalog so it doesn’t blow up on writes
    monkeypatch.setattr("catalog.api.movies.save_catalog", lambda c, p: None)

    app = create_app(cfg)
    client = app.test_client()
    client.testing = True

    # login and stash JWT+API-Key in every request
    login = client.post(
        "/auth/login", json={"username": "admin", "password": "password123"}
    )
    token = login.get_json()["access_token"]
    client.environ_base.update(
        {
            "HTTP_X_API_KEY": cfg["API_KEY"],
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
    )
    return client


def test_non_admin_role_forbidden(client):
    """
    Even with a valid JWT, if the token's "roles" claim lacks "admin",
    we should get a 403.
    """
    # Build a token that has role 'user' but not 'admin'
    with client.application.app_context():
        bad_token = create_access_token(
            identity="someuser",
            additional_claims={"roles": ["user"]},
        )

    headers = {
        "Authorization": f"Bearer {bad_token}",
        "X-API-Key": client.application.config["API_KEY"],
    }
    # Pick any admin-protected endpoint; DELETE /movies/1 works
    resp = client.delete("/movies/1", headers=headers)
    assert resp.status_code == 403

    body = resp.get_json() or {}
    msg = body.get("message", "") or body.get("error", "")
    assert "role: admin" in msg.lower()

# tests/test_rate_limit.py
import pytest
from catalog.api.api import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # reuse your existing fixture pattern for seeding & auth
    from catalog.models import Catalog, Movie

    seed = Catalog()
    seed.add_movie(Movie(id=1, title="Titanic", year=1992))

    cfg = {
        "CATALOG_PATH": str(tmp_path / "movies.json"),
        "API_KEY": "supersecret123",
        "JWT_SECRET_KEY": "super-jwt-secret",
        "JWT_ACCESS_TOKEN_EXPIRES": False,
        # tighten default for tests:
        "RATELIMIT_DEFAULT": "3 per minute",
    }

    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")
    app = create_app(cfg)
    client = app.test_client()

    # authenticate once to get JWT & API-Key in headers
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


def test_global_rate_limit(client):
    # default is 3 requests per minute
    for _ in range(3):
        resp = client.get("/movies")
        assert resp.status_code in (200, 404)  # OK
    # 4th request should be throttled
    resp = client.get("/movies")
    assert resp.status_code == 429
    # ensure Retry-After header present
    assert "Retry-After" in resp.headers


def test_login_rate_limit(client):
    # apply per-route limit of 5/min in your app
    for _ in range(5):
        r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        # each still yields 401 Bad credentials
        assert r.status_code == 401
    # 6th attempt => 429 too many login tries
    r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 429

import pytest
from catalog.api import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    from catalog.models import Catalog, Movie

    seed = Catalog()
    seed.add_movie(Movie(id=1, title="Titanic", year=1992))

    cfg = {"CATALOG_PATH": str(tmp_path / "movies.json")}

    monkeypatch.setattr("catalog.api.import_catalog_from_json", lambda path: seed)

    exported = {}

    def fake_export(catalog: Catalog, path):
        exported["catalog"] = catalog
        exported["path"] = path

        from catalog.io_utils import export_catalog_to_json as real_export

        return real_export(catalog, path)

    monkeypatch.setattr("catalog.api.export_catalog_to_json", fake_export)

    app = create_app(cfg)
    app.testing = True
    client = app.test_client()
    client.exported = exported
    return client


def test_list_movies(client):
    resp = client.get("/movies")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "movies" in data
    titles = [m["title"] for m in data["movies"]]
    assert titles == ["Titanic"]


def test_add_movie_success(client):
    payload = {"id": 2, "title": "Inception", "year": 2010}
    resp = client.post("/movies", json=payload)
    assert resp.status_code == 201

    data = resp.get_json()
    assert data["movie"]["id"] == 2
    assert data["movie"]["title"] == "Inception"

    exp = client.exported
    assert exp["path"].name == "movies.json"
    assert exp["path"].suffix == ".json"
    titles = [m.title for m in exp["catalog"]]
    assert "Inception" in titles


@pytest.mark.parametrize(
    "bad_payload",
    [
        {},
        {"id": 3},
        {"id": 3, "title": "X"},
    ],
)
def test_add_movie_bad_request(client, bad_payload):
    resp = client.post("/movies", json=bad_payload)
    assert resp.status_code == 400
    err = resp.get_json()
    assert "Missing fields" in err.get("message", "") or "Missing fields" in err.get(
        "error", ""
    )


def test_get_movie_by_id_success(client):
    # Seed includes movie with id=1
    resp = client.get("/movies/1")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["movie"]["id"] == 1
    assert data["movie"]["title"] == "Titanic"


def test_get_movie_by_id_not_found(client):
    resp = client.get("/movies/999")
    assert resp.status_code == 404
    err = resp.get_json()
    assert "not found" in err.get("error", "").lower()


def test_delete_movie_success(client):
    resp = client.delete("/movies/1")
    assert resp.status_code == 204  # No Content

    resp2 = client.get("/movies/1")
    assert resp2.status_code == 404


def test_delete_movie_not_found(client):
    resp = client.delete("/movies/999")
    assert resp.status_code == 404
    err = resp.get_json()
    assert "not found" in err.get("error", "").lower()


def test_update_movie_success(client):
    resp = client.put("/movies/1", json={"title": "New Titanic", "rating": 8.1})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["movie"]["title"] == "New Titanic"
    assert abs(data["movie"]["rating"] - 8.1) < 1e-6

    exp = client.exported
    titles = [m.title for m in exp["catalog"]]
    assert "New Titanic" in titles


def test_update_movie_not_allowed_field(client):
    resp = client.put("/movies/1", json={"id": 999, "foo": "bar"})
    assert resp.status_code == 400
    err = resp.get_json()
    assert "not allowed" in err["error"].lower()


def test_import_json(client):
    new_list = [
        {"id": 10, "title": "X", "year": 2020},
        {"id": 11, "title": "Y", "year": 2021},
    ]
    resp = client.post("/movies/import/json", json={"movies": new_list})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["count"] == 2

    resp2 = client.get("/movies")
    titles = [m["title"] for m in resp2.get_json()["movies"]]
    assert titles == ["X", "Y"]


def test_import_json_bad_payload(client):
    resp = client.post("/movies/import/json", json={})
    assert resp.status_code == 400
    err = resp.get_json()
    assert "must provide json with a 'movies' list".lower() in err["error"].lower()


def test_export_json(client):
    resp = client.get("/movies/export/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data["movies"], list)
    assert data["movies"][0]["title"] == "Titanic"

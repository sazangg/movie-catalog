import csv
import io
from pathlib import Path

import pytest
from catalog.api.api import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    from catalog.models import Catalog, Movie

    seed = Catalog()
    seed.add_movie(Movie(id=1, title="Titanic", year=1992))

    cfg = {"CATALOG_PATH": str(tmp_path / "movies.json"), "API_KEY": "supersecret123"}

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


def test_list_movies(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.get("/movies", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "movies" in data
    titles = [m["title"] for m in data["movies"]]
    assert titles == ["Titanic"]


def test_get_movie_by_id_success(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.get("/movies/1", headers=headers)
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["movie"]["id"] == 1
    assert data["movie"]["title"] == "Titanic"


def test_get_movie_by_id_not_found(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.get("/movies/999", headers=headers)
    assert resp.status_code == 404
    err = resp.get_json()
    assert "not found" in err.get("error", "").lower()


def test_add_movie_success(client):
    payload = {"id": 2, "title": "Inception", "year": 2010}
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post("/movies", json=payload, headers=headers)
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
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post("/movies", json=bad_payload, headers=headers)
    assert resp.status_code == 400
    err = resp.get_json()
    assert "Missing fields" in err.get("message", "") or "Missing fields" in err.get(
        "error", ""
    )


def test_update_movie_success(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.put(
        "/movies/1", json={"title": "New Titanic", "rating": 8.1}, headers=headers
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["movie"]["title"] == "New Titanic"
    assert abs(data["movie"]["rating"] - 8.1) < 1e-6

    exp = client.exported
    titles = [m.title for m in exp["catalog"]]
    assert "New Titanic" in titles


def test_update_movie_not_allowed_field(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.put("/movies/1", json={"id": 999, "foo": "bar"}, headers=headers)
    assert resp.status_code == 400
    err = resp.get_json()
    assert "not allowed" in err["error"].lower()


def test_delete_movie_success(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.delete("/movies/1", headers=headers)
    assert resp.status_code == 204

    resp2 = client.get("/movies/1", headers=headers)
    assert resp2.status_code == 404

    exp = client.exported

    assert exp["path"].name == "movies.json"

    ids = [m.id for m in exp["catalog"]]
    assert 1 not in ids


def test_delete_movie_not_found(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.delete("/movies/999", headers=headers)
    assert resp.status_code == 404
    err = resp.get_json()
    assert "not found" in err["error"].lower()


def test_import_json(client):
    new_list = [
        {"id": 10, "title": "X", "year": 2020},
        {"id": 11, "title": "Y", "year": 2021},
    ]
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post(
        "/movies/import/json", json={"movies": new_list}, headers=headers
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["count"] == 2

    resp2 = client.get("/movies", headers=headers)
    titles = [m["title"] for m in resp2.get_json()["movies"]]
    assert titles == ["X", "Y"]


def test_import_json_bad_payload(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post("/movies/import/json", json={}, headers=headers)
    assert resp.status_code == 400
    err = resp.get_json()
    assert "must provide json with a 'movies' list".lower() in err["error"].lower()


def test_export_json(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.get("/movies/export/json", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data["movies"], list)
    assert data["movies"][0]["title"] == "Titanic"


def test_enrich_ids(client, monkeypatch):
    def fake_fetch_ids(cat, max_concurrency=2):
        updated = 0
        for m in cat:
            m.imdb_id = "ttTEST"
            updated += 1
        return updated

    monkeypatch.setattr("catalog.api.enrich.enrich_ids_service", fake_fetch_ids)

    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post("/movies/enrich/ids", json={}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["updated"] == 1

    resp2 = client.get("/movies/1", headers=headers)
    assert resp2.get_json()["movie"]["imdb_id"] == "ttTEST"


def test_enrich_metadata(client, monkeypatch):
    client.app.catalog.movies[0].imdb_id = "ttDUMMY"

    def fake_enrich(cat, max_concurrency=2):
        enriched = 0
        for m in cat:
            m.poster = "url"
            m.plot = "plot"
            m.runtime = 123
            enriched += 1
        return enriched

    monkeypatch.setattr("catalog.api.enrich.enrich_metadata_service", fake_enrich)

    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post("/movies/enrich/metadata", json={}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["enriched"] == 1
    m = client.app.catalog.movies[0]
    assert m.poster == "url" and m.runtime == 123


def test_import_csv_file(client):
    rows = [
        ["id", "title", "year", "genres", "rating", "tags"],
        ["5", "Matrix", "1999", "action|sci-fi", "8.7", "neo|reality"],
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    buf.seek(0)

    data = {"file": (io.BytesIO(buf.read().encode("utf-8")), "movies.csv")}
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.post(
        "/movies/import/csv",
        data=data,
        content_type="multipart/form-data",
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["count"] == 1

    resp2 = client.get("/movies", headers=headers)
    titles = [m["title"] for m in resp2.get_json()["movies"]]
    assert titles == ["Matrix"]


def test_export_csv_file(client):
    correct = client.application.config["API_KEY"]
    headers = {"X-API-Key": correct}
    resp = client.get("/movies/export/csv", headers=headers)
    assert resp.status_code == 200

    assert resp.headers["Content-Type"].startswith("text/csv")

    text = resp.data.decode("utf-8").splitlines()
    reader = csv.reader(text)
    rows = list(reader)

    assert rows[0] == ["id", "title", "year", "genres", "rating", "tags"]

    assert rows[1][1] == "Titanic"

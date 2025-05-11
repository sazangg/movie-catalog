import json
import pytest
from catalog.api import create_app
from catalog.models import Catalog, Movie


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Create a Flask test client with a temp catalog file.
    We monkeypatch import_catalog_from_json to load our seeded catalog.
    """
    # Seed a Catalog
    seed = Catalog()
    m1 = Movie(id=1, title="Titanic", year=1992)
    m2 = Movie(id=2, title="Inception", year=2010)
    seed.add_movie(m1)
    seed.add_movie(m2)

    # Monkeypatch the import function to return our seed
    monkeypatch.setattr("catalog.api.import_catalog_from_json", lambda path: seed)

    app = create_app({"CATALOG_PATH": str(tmp_path / "dummy.json")})
    return app.test_client()


def test_list_movies(client):
    resp = client.get("/movies")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "movies" in data
    titles = [m["title"] for m in data["movies"]]
    assert titles == ["Titanic", "Inception"]

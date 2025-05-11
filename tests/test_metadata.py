import aiohttp
import catalog.metadata as meta
import pytest
from catalog.models import Catalog, Movie


class DummyResponse:
    """
    Simulates aiohttp.ClientResponse for our tests.
    You can control .json() return value and .raise_for_status() behavior.
    """

    def __init__(self, payload=None, status=200, exc=None):
        self._payload = payload or {}
        self.status = status
        self._exc = exc

    async def json(self):
        return self._payload

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    # For use with "async with"
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False  # don’t suppress exceptions


class DummySession:
    """
    Simulates aiohttp.ClientSession.  `url_map` maps URL → DummyResponse.
    """

    def __init__(self, url_map):
        self._map = url_map

    def get(self, url):
        # Return the DummyResponse you configured for this URL
        return self._map.get(url, DummyResponse(payload={}, exc=Exception("not found")))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_fetch_metadata_success(monkeypatch):
    """When the API returns 200 + valid JSON, fetch_metadata returns the dict."""
    # Prepare a fake payload and URL
    fake_id = "tt0000001"
    fake_payload = {"Title": "Foo", "imdbID": fake_id}
    fake_url = f"https://www.omdbapi.com/?i={fake_id}&apikey=KEY"

    # Monkeypatch ClientSession to use our DummySession
    monkeypatch.setenv("OMDB_API_KEY", "KEY")

    def fake_session_factory():
        return DummySession({fake_url: DummyResponse(payload=fake_payload)})

    monkeypatch.setattr(meta.aiohttp, "ClientSession", fake_session_factory)

    # Call fetch_metadata
    async with fake_session_factory() as session:
        result = await meta.fetch_metadata(fake_id, session)
    assert result == fake_payload


@pytest.mark.asyncio
async def test_fetch_metadata_http_error(monkeypatch):
    fake_id = "tt0000002"
    fake_url = f"https://www.omdbapi.com/?i={fake_id}&apikey=KEY"
    exc = aiohttp.ClientResponseError(None, None, status=404, message="Not Found")

    monkeypatch.setenv("OMDB_API_KEY", "KEY")

    def fake_session_factory():
        return DummySession({fake_url: DummyResponse(exc=exc)})

    monkeypatch.setattr(meta.aiohttp, "ClientSession", fake_session_factory)

    async with fake_session_factory() as session:
        with pytest.raises(aiohttp.ClientResponseError):
            await meta.fetch_metadata(fake_id, session)


@pytest.mark.asyncio
async def test_fetch_id_for_title_success(monkeypatch):
    title = "My Movie"
    encoded = meta.quote_plus(title)
    fake_url = f"https://www.omdbapi.com/?t={encoded}&apikey=KEY"
    fake_payload = {"imdbID": "tt12345"}

    monkeypatch.setenv("OMDB_API_KEY", "KEY")

    def fake_session_factory():
        return DummySession({fake_url: DummyResponse(payload=fake_payload)})

    monkeypatch.setattr(meta.aiohttp, "ClientSession", fake_session_factory)

    async with fake_session_factory() as session:
        iid = await meta.fetch_id_for_title(title, session)
    assert iid == "tt12345"


@pytest.mark.asyncio
async def test_fetch_id_for_title_not_found(monkeypatch):
    title = "Unknown"
    encoded = meta.quote_plus(title)
    fake_url = f"https://www.omdbapi.com/?t={encoded}&apikey=KEY"

    monkeypatch.setenv("OMDB_API_KEY", "KEY")

    def fake_session_factory():
        return DummySession({fake_url: DummyResponse(payload={})})

    monkeypatch.setattr(meta.aiohttp, "ClientSession", fake_session_factory)

    async with fake_session_factory() as session:
        iid = await meta.fetch_id_for_title(title, session)
    assert iid is None


@pytest.mark.asyncio
async def test__fetch_ids(monkeypatch):
    async def fake_fetch(title, session):
        return "ID_" + title.replace(" ", "_")

    monkeypatch.setattr(meta, "fetch_id_for_title", fake_fetch)

    titles = ["A", "B C"]
    result = await meta._fetch_ids(titles, max_concurrency=2)
    assert result == {"A": "ID_A", "B C": "ID_B_C"}


@pytest.mark.asyncio
async def test__enrich_all(monkeypatch):
    async def fake_fetch_meta(iid, session):
        return {
            "Poster": f"url/{iid}.jpg",
            "Plot": f"Plot for {iid}",
            "Runtime": "123 min",
        }

    monkeypatch.setattr(meta, "fetch_metadata", fake_fetch_meta)

    ids = ["tt1", "tt2"]
    meta_map = await meta._enrich_all(ids, max_concurrency=2)
    assert meta_map["tt1"]["Poster"].endswith("tt1.jpg")
    assert meta_map["tt2"]["Plot"] == "Plot for tt2"


def test_fetch_imdb_ids_and_enrich(monkeypatch):
    cat = Catalog(
        [
            Movie(id=1, title="Movie One", year=2000),
            Movie(id=2, title="Movie Two", year=2001),
        ]
    )

    async def fake_fetch_ids(titles, max_concurrency):
        return {"Movie One": "ttX", "Movie Two": None}

    async def fake_enrich_all(ids, max_concurrency):
        return {"ttX": {"Poster": "urlX", "Plot": "P", "Runtime": "45 min"}}

    monkeypatch.setattr(meta, "_fetch_ids", fake_fetch_ids)
    monkeypatch.setattr(meta, "_enrich_all", fake_enrich_all)

    meta.full_enrich(cat, max_concurrency=2)

    m1, m2 = list(cat)

    assert m1.imdb_id == "ttX"
    assert m1.poster == "urlX"
    assert m1.plot == "P"
    assert m1.runtime == 45

    assert m2.imdb_id is None
    assert m2.poster is None
    assert m2.plot is None
    assert m2.runtime is None

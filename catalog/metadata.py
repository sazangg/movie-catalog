import asyncio
import logging
import os
from typing import Dict
from urllib.parse import quote_plus

import aiohttp
from dotenv import load_dotenv

from catalog.models import Catalog

load_dotenv()
logger = logging.getLogger(__name__)


async def fetch_metadata(imdb_id: str, session: aiohttp.ClientSession) -> Dict:
    url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={os.getenv('OMDB_API_KEY')}"
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json()


async def _enrich_all(imdb_ids: list[str], max_concurrency: int = 5) -> Dict[str, Dict]:
    sem = asyncio.Semaphore(max_concurrency)
    async with aiohttp.ClientSession() as session:

        async def sem_fetch(iid: str):
            async with sem:
                return iid, await fetch_metadata(iid, session)

        tasks = [asyncio.create_task(sem_fetch(iid)) for iid in imdb_ids]
        results: list[tuple[str, Dict]] = await asyncio.gather(*tasks)

        meta = {}
        for iid, payload in results:
            if isinstance(payload, Exception):
                logger.warning("Error fetching metadata for %s: %s", iid, payload)
                meta[iid] = {"error": str(payload)}
            else:
                meta[iid] = payload
        return meta


def enrich_catalog(catalog: Catalog, max_concurrency: int = 5) -> None:
    imdb_ids = [m.imdb_id for m in catalog if m.imdb_id]
    metadata = asyncio.run(_enrich_all(imdb_ids, max_concurrency))

    for movie in catalog:
        data = metadata.get(movie.imdb_id, {})
        if "error" in data:
            logger.warning("No movie metadata for %s: %s", movie.imdb_id, data["error"])
        else:
            movie.poster = data.get("Poster")
            movie.plot = data.get("Plot")
            runtime_str = data.get("Runtime", "")
            movie.runtime = (
                int(runtime_str.split()[0])
                if runtime_str and runtime_str != "N/A"
                else None
            )


async def fetch_id_for_title(title: str, session: aiohttp.ClientSession) -> str | None:
    encoded = quote_plus(title)
    url = f"https://www.omdbapi.com/?t={encoded}&apikey={os.getenv('OMDB_API_KEY')}"
    async with session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data.get("imdbID")


async def _fetch_ids(
    titles: list[str], max_concurrency: int = 5
) -> Dict[str, str | None]:
    sem = asyncio.Semaphore(max_concurrency)
    async with aiohttp.ClientSession() as session:

        async def sem_fetch(title: str):
            async with sem:
                return title, await fetch_id_for_title(title, session)

        tasks = [asyncio.create_task(sem_fetch(t)) for t in titles]
        results: list[tuple[str, str]] = await asyncio.gather(*tasks)

        id_map: Dict[str, str | None] = {}
        for title, result in results:
            if isinstance(result, Exception):
                logger.warning("Error fetching ID for %s: %s", title, result)
                id_map[title] = None
            else:
                id_map[title] = result
        return id_map


def fetch_imdb_ids(catalog: Catalog, max_concurrency: int = 5) -> None:
    titles = [m.title for m in catalog]
    id_map = asyncio.run(_fetch_ids(titles, max_concurrency))
    for movie in catalog:
        movie.imdb_id = id_map.get(movie.title)


def full_enrich(catalog: Catalog, max_concurrency: int = 5) -> None:
    fetch_imdb_ids(catalog, max_concurrency)
    enrich_catalog(catalog, max_concurrency)

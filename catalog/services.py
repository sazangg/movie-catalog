import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from werkzeug.datastructures import FileStorage

from .io_utils import (
    export_catalog_to_csv,
    export_catalog_to_json,
    import_catalog_from_csv,
    import_catalog_from_json,
)
from .metadata import enrich_catalog, fetch_imdb_ids
from .models import Catalog, Movie


def load_catalog(path: Optional[str] = None) -> Catalog:
    return import_catalog_from_json(Path(path)) if path else import_catalog_from_json()


def save_catalog(catalog: Catalog, path: str) -> Path:
    return export_catalog_to_json(catalog, Path(path))


def load_movies_service(catalog: Catalog) -> list[dict]:
    return [asdict(m) for m in catalog]


def load_movie_by_id_service(catalog: Catalog, movie_id: int) -> Movie | None:
    return catalog.find_by_id(movie_id)


def add_movie_service(catalog: Catalog, data: dict) -> Movie:
    if not all(k in data for k in ("id", "title", "year")):
        raise ValueError("Missing fields")

    movie = Movie.from_dict(data)
    catalog.add_movie(movie)
    return movie


def update_movie_service(catalog: Catalog, movie_id: int, data: dict) -> Movie | None:
    movie = catalog.find_by_id(movie_id)
    if not movie:
        return None

    if not data:
        raise ValueError("Empty payload")

    allowed = {"title", "year", "genres", "rating", "tags", "imdb_id"}
    for key, val in data.items():
        if key in allowed:
            setattr(movie, key, val)
        else:
            raise ValueError(f"Field not allowed: {key}")
    return movie


def delete_movie_service(catalog: Catalog, movie_id: int) -> bool:
    return catalog.remove(movie_id)


def import_json_service(payload: dict, target_path: str) -> Catalog:
    if (
        not payload
        or "movies" not in payload
        or not isinstance(payload["movies"], list)
    ):
        raise ValueError("Must provide JSON with a 'movies' list")

    catalog = Catalog.from_json(payload["movies"])

    save_catalog(catalog, target_path)
    return catalog


def import_csv_service(uploaded_file: FileStorage, target_path: str) -> Catalog:
    if uploaded_file.filename == "":
        raise ValueError("No file selected")
    
    if not uploaded_file.filename.lower().endswith(".csv"):
        raise ValueError("Uploaded file must be .csv")

    tmp_dir = tempfile.mkdtemp()
    tmp_path = Path(tmp_dir) / uploaded_file.filename
    uploaded_file.save(tmp_path)
    catalog = import_catalog_from_csv(tmp_path)
    shutil.rmtree(tmp_dir)

    save_catalog(catalog, target_path)
    return catalog


def export_json_service(catalog: Catalog) -> List[dict]:
    return load_movies_service(catalog)


def export_csv_service(catalog: Catalog, filename: str = "export.csv") -> Path:
    tmp_dir = tempfile.mkdtemp()
    tmp_path = Path(tmp_dir) / filename
    export_catalog_to_csv(catalog, tmp_path)
    return tmp_path


def enrich_ids_service(catalog: Catalog, max_concurrency: int = 5) -> int:
    return fetch_imdb_ids(catalog, max_concurrency)


def enrich_metadata_service(catalog: Catalog, max_concurrency: int = 5) -> int:
    return enrich_catalog(catalog, max_concurrency)

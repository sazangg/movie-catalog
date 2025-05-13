import csv
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Sequence

from .models import Catalog, Movie

logger = logging.getLogger(__name__)


def export_catalog_to_csv(catalog: Catalog, path: Path | str | None = None) -> Path:
    if isinstance(path, str):
        path = Path(path)

    logger.debug("Export catalog as CSV to path: %s", path)
    if path is None:
        path = Path.home() / "catalog.csv"

    if path.suffix.lower() != ".csv":
        path = path.with_suffix(".csv")

    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + "tmp")
    with tmp.open(mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "title", "year", "genres", "rating", "tags"])
        for movie in catalog:
            writer.writerow(
                [
                    movie.id,
                    movie.title,
                    movie.year,
                    "|".join(movie.genres),
                    movie.rating,
                    "|".join(movie.tags),
                ]
            )

    tmp.replace(path)
    logger.info("Successfully exported catalog to csv file to: %s", path)
    return path


def import_catalog_from_csv(path: Path | None = None) -> "Catalog":
    logger.debug("Importing catalog from CSV: %s", path)
    if path is None:
        path = Path.home() / "catalog.csv"

    if path.suffix.lower() != ".csv":
        logger.error("Path doesn't end with .csv")
        raise ValueError("CSV path must end with .csv")

    if not path.is_file() or path.stat().st_size == 0:
        logger.warning("CSV file missing/empty, returning empty catalog: %s", path)
        return Catalog()

    cat = Catalog()
    with path.open(mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        required = {"id", "title", "year", "genres", "rating", "tags"}
        fieldnames: Sequence[str] = reader.fieldnames or []
        if not required.issubset(fieldnames):
            missing = required - set(fieldnames)
            raise ValueError(f"CSV missing columns: {missing}")

        for row in reader:
            movie_data = {
                "id": int(row["id"]),
                "title": row["title"],
                "year": int(row["year"]),
                "genres": row["genres"].split("|") if row["genres"] else [],
                "rating": float(row["rating"]),
                "tags": row["tags"].split("|") if row["tags"] else [],
            }
            cat.add_movie(Movie.from_dict(movie_data))

    return cat


def export_catalog_to_json(catalog: Catalog, path: Path | str | None = None) -> Path:
    if isinstance(path, str):
        path = Path(path)

    logger.debug("Starting process to export catalog to json")
    try:
        if path is None:
            path = Path.home() / "catalog.json"
            logger.warning(f"No path specified, using default path: {str(path)}")

        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
            logger.warning("Correcting file extension to .json")

        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(catalog.to_json(), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        logger.exception("Failed to export catalog to JSON at %s", path)
        raise

    logger.info("Successfully exported catalog to json at: %s", path)
    return path


def import_catalog_from_json(path: Path | None = None) -> "Catalog":
    if path is None:
        path = Path.home() / "catalog.json"

    if path.suffix.lower() != ".json":
        logger.error("File extension not correct, must end with .json")
        raise ValueError("JSON path must end with .json")

    if not path.is_file() or path.stat().st_size == 0:
        logger.warning("Path is not a file or is empty")
        return Catalog()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        logger.exception("The file is not a valid JSON format")
        raise ValueError("Not a valid JSON file") from err

    if not isinstance(raw, list):
        logger.error("The file should contain a list of objects, but didn't.")
        raise ValueError(f"Expected list of movies in {path}")

    return Catalog.from_json(raw)


@contextmanager
def open_catalog(path: Path | None = None, mode: Literal["r", "w"] = "r"):
    logger.debug("Started context manager with '%s' mode", mode)
    if path is None:
        path = Path.home() / "catalog.json"

    suffix = path.suffix.lower()
    if suffix not in (".json", ".csv"):
        path = path.with_suffix(".json")
        suffix = ".json"

    if mode == "r":
        if suffix == ".json":
            catalog = import_catalog_from_json(path)
        else:
            catalog = import_catalog_from_csv(path)

        yield catalog

        return

    elif mode == "w":
        catalog = Catalog()
        try:
            yield catalog
        finally:
            if suffix == ".json":
                export_catalog_to_json(catalog, path)
            else:
                export_catalog_to_csv(catalog, path)

    else:
        logging.error("Entered wrong mode (%s), must be 'r' or 'w'", mode)
        raise ValueError(f"Mode must be 'r' or 'w', got {mode!r}")

from pathlib import Path


class Config:
    CATALOG_PATH: str = str(Path.home() / "catalog.json")
    MAX_CONCURRENCY: int = 5

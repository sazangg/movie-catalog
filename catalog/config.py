import os
from pathlib import Path


class Config:
    CATALOG_PATH: str = str(Path.home() / "catalog.json")
    API_KEY: str = os.getenv("API_KEY", "changeme")
    MAX_CONCURRENCY: int = 5

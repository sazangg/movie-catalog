import os
from pathlib import Path


class Config:
    CATALOG_PATH: str = str(Path.home() / "catalog.json")
    API_KEY: str = os.getenv("API_KEY", "changeme")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = False  # timedelta(minutes=60)
    MAX_CONCURRENCY: int = 5
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "3 per minute")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

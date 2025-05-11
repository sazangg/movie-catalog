import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Movie:
    id: int
    title: str
    year: int
    genres: List[str] = field(default_factory=list)
    rating: float = 0.0
    tags: List[str] = field(default_factory=list)
    imdb_id: str | None = None
    poster: str | None = None
    plot: str | None = None
    runtime: int | None = None

    def __post_init__(self):
        if not self.validate_year(self.year):
            raise ValueError(f"Invalid movie year: {self.year}")

    def __repr__(self):
        return f"<Movie id: {self.id!r}, title:{self.title!r}, year: {self.year!r}>"

    def __eq__(self, other):
        return isinstance(other, Movie) and self.id == other.id

    @property
    def age(self):
        return datetime.now().year - self.year

    @staticmethod
    def validate_year(year: int) -> bool:
        return 1800 <= year <= datetime.now().year

    @classmethod
    def from_dict(cls, data: dict) -> "Movie":
        return cls(**data)


@dataclass
class Catalog:
    movies: List[Movie] = field(default_factory=list)

    def add_movie(self, movie: Movie) -> None:
        self.movies.append(movie)

    def get_all_titles(self) -> list[str]:
        return [m.title for m in self.movies]

    def __len__(self):
        return len(self.movies)

    def __iter__(self):
        yield from self.movies

    def find_by_title(self, title: str) -> list[Movie]:
        return [m for m in self.movies if title.lower() in m.title.lower()]

    def to_json(self) -> str:
        return json.dumps([asdict(m) for m in self.movies], indent=2)

    @classmethod
    def from_json(cls, data: list[dict]) -> "Catalog":
        cat = cls()
        for entry in data:
            if not {"id", "title", "year"}.issubset(entry):
                raise ValueError(f"Missing keys in JSON entry: {entry}")

            entry["id"] = int(entry["id"])
            entry["year"] = int(entry["year"])
            entry["rating"] = float(entry["rating"])
            entry["genres"] = entry.get("genres", [])
            entry["tags"] = entry.get("tags", [])
            cat.add_movie(Movie.from_dict(entry))

        return cat

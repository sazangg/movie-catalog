import functools
import os
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from itertools import combinations
from typing import Callable, DefaultDict, Iterator, Tuple

from .models import Catalog, Movie


def genre_to_movies_map(catalog: Catalog) -> DefaultDict[str, list[Movie]]:
    # all_genres = {g for m in catalog.movies for g in m.genres}
    # return {g: [m for m in catalog.movies if g in m.genres] for g in all_genres}
    gd = defaultdict(list)
    for movie in catalog.movies:
        for genre in movie.genres:
            gd[genre].append(movie)

    return gd


def count_tags(catalog: Catalog) -> Counter[str]:
    return Counter(tag for m in catalog.movies for tag in (m.tags or []))


def movie_pairs(catalog: Catalog) -> Iterator[Tuple[Movie, Movie]]:
    yield from combinations(catalog.movies, 2)


def retry(times: int):
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
            raise last_exc

        return wrapper

    return decorator


def timed(fn: Callable):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{wrapper.__name__} took: {elapsed:.4f}s")
        return result

    return wrapper


@contextmanager
def temporary_env(name: str, new_value: str):
    old_value = os.environ.get(name)
    os.environ[name] = new_value
    try:
        yield
    finally:
        if old_value is None:
            del os.environ[name]
        else:
            os.environ[name] = old_value

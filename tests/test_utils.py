from collections import Counter
from typing import Tuple

from catalog.models import Catalog, Movie
from catalog.utils import count_tags, genre_to_movies_map, movie_pairs


def seed_catalog() -> Tuple[Movie, Movie, Catalog]:
    seeded_catalog = Catalog()
    m1 = Movie(
        id=1,
        title="Titanic",
        year=1990,
        genres=["action", "drama", "romance"],
        rating=7.9,
        tags=["ship", "love", "ocean", "sea", "tragedy"],
    )
    m2 = Movie(
        id=2,
        title="Taxi",
        year=1995,
        genres=["action", "comedy", "romance"],
        rating=8.4,
        tags=["taxi", "love", "fun", "sea", "laugh", "happy ending"],
    )

    seeded_catalog.add_movie(m1)
    seeded_catalog.add_movie(m2)

    return m1, m2, seeded_catalog


def test_genre_to_movies_map():
    m1, m2, sc = seed_catalog()
    gm = genre_to_movies_map(sc)

    expected = {"action": [m1, m2], "drama": [m1], "romance": [m1, m2], "comedy": [m2]}

    assert set(gm.keys()) == set(expected.keys())
    for genre, movies in expected.items():
        assert [m.id for m in gm[genre]] == [m.id for m in movies]

    assert genre_to_movies_map(Catalog()) == {}


def test_count_tags():
    _, _, sc = seed_catalog()
    tags = count_tags(sc)

    assert count_tags(Catalog()) == Counter()
    assert set(tags) == {
        "ship",
        "love",
        "ocean",
        "sea",
        "tragedy",
        "taxi",
        "fun",
        "laugh",
        "happy ending",
    }
    assert tags["love"] == 2
    assert tags["sea"] == 2
    assert tags["taxi"] == 1
    assert tags["ship"] == 1


def test_movie_pairs():
    m1, m2, sc = seed_catalog()
    pairs = list(movie_pairs(sc))
    assert len(pairs) == 1
    assert pairs[0] == (m1, m2) or pairs[0] == (m2, m1)

from typing import Tuple

import pytest
from catalog.models import Catalog, Movie


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


def test_repr_eq_age():
    m = Movie(4, "Prison Break", 2000)
    m2 = Movie(4, "Titanic", 1900)

    expected_string = "<Movie id: 4, title:'Prison Break', year: 2000>"
    assert m.__repr__() == expected_string
    assert m == m2
    assert m.age == 25


def test_post_init():
    with pytest.raises(ValueError, match="Invalid movie year:"):
        Movie(1, "Titanic", 200)


def test_len_catalog():
    _, _, sc = seed_catalog()
    assert len(sc) == 2


def test_iteration_catalog():
    m1, m2, sc = seed_catalog()
    for movie in sc:
        assert movie in [m1, m2]


def test_find_by_title():
    m1, m2, sc = seed_catalog()

    assert sc.find_by_title("tit") == [m1]
    assert sc.find_by_title("T") == [m1, m2]


def test_from_dict():
    data = {
        "id": 10,
        "title": "Inception",
        "year": 2010,
        "genres": ["sci‑fi", "thriller"],
        "rating": 8.8,
        "tags": ["dream", "mind‑bender"],
    }
    m = Movie.from_dict(data)
    assert isinstance(m, Movie)
    # All attributes copied over:
    assert m.id == 10
    assert m.title == "Inception"
    assert m.year == 2010
    assert m.genres == ["sci‑fi", "thriller"]
    assert m.rating == 8.8
    assert m.tags == ["dream", "mind‑bender"]

import pytest
from catalog.io_utils import (
    export_catalog_to_csv,
    export_catalog_to_json,
    import_catalog_from_csv,
    import_catalog_from_json,
    open_catalog,
)
from catalog.models import Catalog, Movie


def test_export_import_csv(tmp_path):
    path = tmp_path / "catalog.csv"

    cat = Catalog()
    mov = Movie(1, "Titanic", 1992, rating=7.9)
    cat.add_movie(mov)

    target = export_catalog_to_csv(cat, path)
    assert path == target

    imp_cat = import_catalog_from_csv(path)
    assert imp_cat.movies[0] == mov

    with open_catalog(path, mode="r") as catalog:
        assert catalog.movies[0] == mov

    with open_catalog(path, mode="w") as catalog:
        catalog.add_movie(Movie(2, "Inception", 2019, rating=9.1))

    imp_cat = import_catalog_from_csv(path)
    assert imp_cat.movies[0].title == "Inception"


def test_export_import_json(tmp_path):
    path = tmp_path / "catalog.json"

    cat = Catalog()
    mov = Movie(1, "Titanic", 1992, rating=7.9)
    cat.add_movie(mov)

    target = export_catalog_to_json(cat, path)
    assert path == target

    imp_cat = import_catalog_from_json(path)
    assert imp_cat.movies[0] == mov

    with open_catalog(path, mode="r") as catalog:
        assert catalog.movies[0] == mov

    with open_catalog(path, mode="w") as catalog:
        catalog.add_movie(Movie(2, "Inception", 2019, rating=9.1))

    imp_cat = import_catalog_from_json(path)
    assert imp_cat.movies[0].title == "Inception"


def test_import_missing_csv(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    cat = import_catalog_from_csv(missing)
    assert isinstance(cat, Catalog)
    assert len(cat) == 0

    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    cat2 = import_catalog_from_csv(empty)
    assert len(cat2) == 0


def test_import_missing_json(tmp_path):
    missing = tmp_path / "nope.json"
    cat = import_catalog_from_json(missing)
    assert len(cat) == 0

    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    cat2 = import_catalog_from_json(empty)
    assert len(cat2) == 0


@pytest.mark.parametrize("inp", ["id,title\n1,Titanic\n", "id,\nTitanic\n"])
def test_import_bad_csv_header(tmp_path, inp: str):
    bad = tmp_path / "bad.csv"
    bad.write_text(inp, encoding="utf-8")
    with pytest.raises(ValueError, match="CSV missing columns:"):
        import_catalog_from_csv(bad)


def test_import_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not a json list", encoding="utf-8")
    with pytest.raises(ValueError, match="Not a valid JSON"):
        import_catalog_from_json(bad)


def test_default_extension_csv(tmp_path):
    p = tmp_path / "mydata"
    cat = Catalog([Movie(1, "A", 2000)])
    out = export_catalog_to_csv(cat, p)
    assert out.suffix == ".csv"

    imp = import_catalog_from_csv(p.with_suffix(".csv"))
    assert imp.movies[0].id == 1

    with pytest.raises(ValueError, match="CSV path must end with .csv"):
        imp = import_catalog_from_csv(p)


def test_default_extension_json(tmp_path):
    p = tmp_path / "mydata"
    cat = Catalog([Movie(2, "B", 2010)])
    out = export_catalog_to_json(cat, p)
    assert out.suffix == ".json"

    imp = import_catalog_from_json(p.with_suffix(".json"))
    assert imp.movies[0].id == 2

    with pytest.raises(ValueError, match="JSON path must end with .json"):
        imp = import_catalog_from_json(p)

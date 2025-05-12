from dataclasses import asdict
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request

from catalog.io_utils import export_catalog_to_json
from catalog.models import Movie

movies_bp = Blueprint("movies", __name__, url_prefix="/movies")


@movies_bp.route("", methods=["GET"])
def list_movies():
    app = current_app
    movies = [asdict(m) for m in app.catalog]
    return jsonify(movies=movies), 200


@movies_bp.route("", methods=["POST"])
def add_movie():
    app = current_app
    data = request.get_json(force=True)
    if not all(k in data for k in ("id", "title", "year")):
        abort(400, description="Missing fields")

    m = Movie.from_dict(data)
    app.catalog.add_movie(m)

    path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
    export_catalog_to_json(app.catalog, Path(path_str))

    return jsonify(movie=asdict(m)), 201


@movies_bp.route("/<int:movie_id>", methods=["GET"])
def get_movie(movie_id: int):
    app = current_app
    m = app.catalog.find_by_id(movie_id)
    if not m:
        abort(404, description=f"Movie {movie_id} not found")
    return jsonify(movie=asdict(m)), 200


@movies_bp.route("/<int:movie_id>", methods=["DELETE"])
def delete_movie(movie_id: int):
    app = current_app
    removed = app.catalog.remove(movie_id)
    if not removed:
        abort(404, description=f"Movie {movie_id} not found")

    path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
    export_catalog_to_json(app.catalog, Path(path_str))

    return "", 204


@movies_bp.route("/<int:movie_id>", methods=["PUT"])
def update_movie(movie_id: int):
    app = current_app
    data = request.get_json(force=True)
    if not data:
        abort(400, description="Empty payload")

    m = app.catalog.find_by_id(movie_id)
    if not m:
        abort(404, description=f"Movie {movie_id} not found")

    allowed = {"title", "year", "genres", "rating", "tags", "imdb_id"}
    for key, val in data.items():
        if key in allowed:
            setattr(m, key, val)
        else:
            abort(400, description=f"Field not allowed: {key}")

    path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
    export_catalog_to_json(app.catalog, Path(path_str))

    return jsonify(movie=asdict(m)), 200

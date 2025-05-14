from dataclasses import asdict

# from functools import lru_cache
from typing import cast

from flask import Blueprint, abort, current_app, jsonify, request

from catalog.api.auth import require_api_key, requires_role
from catalog.api.my_flask import Flask
from catalog.services import (
    add_movie_service,
    delete_movie_service,
    load_movie_by_id_service,
    load_movies_service,
    save_catalog,
    update_movie_service,
)

movies_bp = Blueprint("movies", __name__, url_prefix="/movies")


@movies_bp.route("", methods=["GET"])
@require_api_key
@requires_role("admin")
def list_movies():
    app = cast(Flask, current_app)

    # @lru_cache(maxsize=1)
    # def load_movies_cached() -> list[dict]:
    #     return load_movies_service(app.catalog)

    return jsonify(movies=load_movies_service(app.catalog)), 200


@movies_bp.route("/<int:movie_id>", methods=["GET"])
@require_api_key
@requires_role("admin")
def get_movie(movie_id: int):
    app = cast(Flask, current_app)
    m = load_movie_by_id_service(app.catalog, movie_id)
    if not m:
        abort(404, description=f"Movie {movie_id} not found")
    return jsonify(movie=asdict(m)), 200


@movies_bp.route("", methods=["POST"])
@require_api_key
@requires_role("admin")
def add_movie():
    app = cast(Flask, current_app)
    data = request.get_json(force=True)

    movie = add_movie_service(app.catalog, data)
    save_catalog(app.catalog, current_app.config["CATALOG_PATH"])
    return jsonify(movie=asdict(movie)), 201


@movies_bp.route("/<int:movie_id>", methods=["PUT"])
@require_api_key
@requires_role("admin")
def update_movie(movie_id: int):
    app = cast(Flask, current_app)
    data = request.get_json(force=True)

    m = update_movie_service(app.catalog, movie_id, data)
    if not m:
        abort(404, description=f"Movie {movie_id} not found")

    save_catalog(app.catalog, current_app.config["CATALOG_PATH"])
    return jsonify(movie=asdict(m)), 200


@movies_bp.route("/<int:movie_id>", methods=["DELETE"])
@require_api_key
@requires_role("admin")
def delete_movie(movie_id: int):
    app = cast(Flask, current_app)
    removed = delete_movie_service(app.catalog, movie_id)
    if not removed:
        abort(404, description=f"Movie {movie_id} not found")

    save_catalog(app.catalog, current_app.config["CATALOG_PATH"])
    return "", 204

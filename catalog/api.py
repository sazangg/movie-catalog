import logging
import os
import tempfile
from dataclasses import asdict
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask as _Flask
from flask import abort, jsonify, request, send_file

from catalog.io_utils import (
    export_catalog_to_csv,
    export_catalog_to_json,
    import_catalog_from_csv,
    import_catalog_from_json,
)
from catalog.metadata import enrich_catalog, fetch_imdb_ids
from catalog.models import Catalog, Movie


class Flask(_Flask):
    catalog: Catalog


def configure_logging(log_file: str = "logs/app.log") -> None:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s")
    )
    root.addHandler(ch)

    fh = RotatingFileHandler(
        filename=log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s"
        )
    )
    root.addHandler(fh)


def create_app(config: dict | None = None) -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.update(config or {})

    @app.errorhandler(400)
    def handle_bad_request(err):
        return jsonify(error=err.description), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify(error=err.description), 404

    catalog = import_catalog_from_json(app.config.get("CATALOG_PATH"))
    app.catalog = catalog

    @app.route("/movies", methods=["GET"])
    def list_movies():
        movies = [asdict(m) for m in app.catalog]
        return jsonify(movies=movies), 200

    @app.route("/movies", methods=["POST"])
    def add_movie():
        data = request.get_json(force=True)
        if not all(k in data for k in ("id", "title", "year")):
            abort(400, description="Missing fields")

        m = Movie.from_dict(data)
        app.catalog.add_movie(m)

        path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
        export_catalog_to_json(catalog, Path(path_str))

        return jsonify(movie=asdict(m)), 201

    @app.route("/movies/<int:movie_id>", methods=["GET"])
    def get_movie(movie_id: int):
        m = app.catalog.find_by_id(movie_id)
        if not m:
            abort(404, description=f"Movie {movie_id} not found")
        return jsonify(movie=asdict(m)), 200

    @app.route("/movies/<int:movie_id>", methods=["DELETE"])
    def delete_movie(movie_id: int):
        removed = app.catalog.remove(movie_id)
        if not removed:
            abort(404, description=f"Movie {movie_id} not found")

        path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
        export_catalog_to_json(app.catalog, Path(path_str))

        return "", 204

    @app.route("/movies/<int:movie_id>", methods=["PUT"])
    def update_movie(movie_id: int):
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

    @app.route("/movies/import/json", methods=["POST"])
    def import_json_movies():
        payload = request.get_json(force=True)
        if (
            not payload
            or "movies" not in payload
            or not isinstance(payload["movies"], list)
        ):
            abort(400, description="Must provide JSON with a 'movies' list")

        new_cat = Catalog.from_json(payload["movies"])

        path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
        export_catalog_to_json(new_cat, Path(path_str))

        app.catalog = new_cat

        return jsonify(message="Imported successfully", count=len(new_cat)), 201

    @app.route("/movies/export/json", methods=["GET"])
    def export_json_movies():
        movies = [asdict(m) for m in app.catalog]
        return jsonify(movies=movies), 200

    @app.route("/movies/enrich/ids", methods=["POST"])
    def enrich_movies_with_iids():
        updated_count = fetch_imdb_ids(app.catalog)

        path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
        export_catalog_to_json(app.catalog, Path(path_str))

        return jsonify(message="Update successful", updated=updated_count), 200

    @app.route("/movies/enrich/metadata", methods=["POST"])
    def enrich_movies_with_metadata():
        enriched_count = enrich_catalog(app.catalog)

        path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
        export_catalog_to_json(app.catalog, Path(path_str))

        return jsonify(message="Update successful", enriched=enriched_count), 200

    @app.route("/movies/import/csv", methods=["POST"])
    def import_csv_movies():
        if "file" not in request.files:
            abort(400, description="Missing 'file' part")
        file = request.files["file"]
        if file.filename == "":
            abort(400, description="No file selected")

        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / file.filename
        file.save(tmp_path)

        new_catalog = import_catalog_from_csv(tmp_path)

        path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
        export_catalog_to_json(new_catalog, Path(path_str))

        app.catalog = new_catalog

        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass

        return jsonify(message="Imported CSV", count=len(new_catalog)), 201

    @app.route("/movies/export/csv", methods=["GET"])
    def export_csv_movies():
        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / "export.csv"
        export_catalog_to_csv(app.catalog, tmp_path)

        response = send_file(
            tmp_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name="movies.csv",
        )

        @response.call_on_close
        def cleanup():
            try:
                os.remove(tmp_path)
                os.rmdir(tmp_dir)
            except OSError:
                pass

        return response

    return app


def main():
    app = create_app()
    app.run(host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()

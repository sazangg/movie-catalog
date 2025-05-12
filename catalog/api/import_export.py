import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request, send_file

from catalog.io_utils import (
    export_catalog_to_csv,
    export_catalog_to_json,
    import_catalog_from_csv,
)
from catalog.models import Catalog

io_bp = Blueprint("io", __name__, url_prefix="/movies")


@io_bp.route("/import/json", methods=["POST"])
def import_json_movies():
    app = current_app

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


@io_bp.route("/export/json", methods=["GET"])
def export_json_movies():
    app = current_app
    movies = [asdict(m) for m in app.catalog]
    return jsonify(movies=movies), 200


@io_bp.route("/import/csv", methods=["POST"])
def import_csv_movies():
    if "file" not in request.files:
        abort(400, description="Missing 'file' part")
    file = request.files["file"]
    if file.filename == "":
        abort(400, description="No file selected")

    app = current_app

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


@io_bp.route("/export/csv", methods=["GET"])
def export_csv_movies():
    app = current_app

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

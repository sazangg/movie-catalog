import shutil
from typing import cast

from flask import Blueprint, abort, current_app, jsonify, request, send_file
from catalog.api.my_flask import Flask

from catalog.services import (
    export_csv_service,
    export_json_service,
    import_csv_service,
    import_json_service
)

io_bp = Blueprint("io", __name__, url_prefix="/movies")


@io_bp.route("/import/json", methods=["POST"])
def import_json_movies():
    app = cast(Flask, current_app)
    payload = request.get_json(force=True)

    app.catalog = import_json_service(payload, current_app.config["CATALOG_PATH"])
    return jsonify(message="Imported successfully", count=len(app.catalog)), 201


@io_bp.route("/export/json", methods=["GET"])
def export_json_movies():
    app = cast(Flask, current_app)
    movies = export_json_service(app.catalog)
    return jsonify(movies=movies), 200


@io_bp.route("/import/csv", methods=["POST"])
def import_csv_movies():
    if "file" not in request.files:
        abort(400, description="Missing 'file' part")
    
    uploaded_file = request.files["file"]
    app = cast(Flask, current_app)
    app.catalog = import_csv_service(uploaded_file, current_app.config["CATALOG_PATH"])

    return jsonify(message="Imported CSV", count=len(app.catalog)), 201


@io_bp.route("/export/csv", methods=["GET"])
def export_csv_movies():
    app = cast(Flask, current_app)
    tmp_path = export_csv_service(app.catalog)

    response = send_file(
        tmp_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="movies.csv",
    )

    @response.call_on_close
    def cleanup():
        shutil.rmtree(tmp_path.parent)

    return response

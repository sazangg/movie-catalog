from pathlib import Path

from flask import Blueprint, current_app, jsonify

from catalog.io_utils import export_catalog_to_json
from catalog.metadata import enrich_catalog, fetch_imdb_ids

enrich_bp = Blueprint("enrich", __name__, url_prefix="/movies")


@enrich_bp.route("/enrich/ids", methods=["POST"])
def enrich_movies_with_iids():
    app = current_app
    updated_count = fetch_imdb_ids(app.catalog)

    path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
    export_catalog_to_json(app.catalog, Path(path_str))

    return jsonify(message="Update successful", updated=updated_count), 200


@enrich_bp.route("/enrich/metadata", methods=["POST"])
def enrich_movies_with_metadata():
    app = current_app
    enriched_count = enrich_catalog(app.catalog)

    path_str = app.config.get("CATALOG_PATH") or str(Path.home() / "catalog.json")
    export_catalog_to_json(app.catalog, Path(path_str))

    return jsonify(message="Update successful", enriched=enriched_count), 200

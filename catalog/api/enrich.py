from typing import cast
from flask import Blueprint, current_app, jsonify, request
from catalog.api.my_flask import Flask

from catalog.services import enrich_ids_service, enrich_metadata_service, save_catalog

enrich_bp = Blueprint("enrich", __name__, url_prefix="/movies")


@enrich_bp.route("/enrich/ids", methods=["POST"])
def enrich_movies_with_iids():
    payload = request.get_json(silent=True) or {}
    max_conc = payload.get("max_concurrency", 5)
    app = cast(Flask, current_app)
    updated_count = enrich_ids_service(app.catalog, max_conc)

    save_catalog(current_app.catalog, current_app.config["CATALOG_PATH"])
    return jsonify(message="Update successful", updated=updated_count), 200


@enrich_bp.route("/enrich/metadata", methods=["POST"])
def enrich_movies_with_metadata():
    payload = request.get_json(silent=True) or {}
    max_conc = payload.get("max_concurrency", 5)
    app = cast(Flask, current_app)
    enriched_count = enrich_metadata_service(app.catalog, max_conc)

    save_catalog(current_app.catalog, current_app.config["CATALOG_PATH"])
    return jsonify(message="Update successful", enriched=enriched_count), 200

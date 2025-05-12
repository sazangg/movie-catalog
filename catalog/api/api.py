from catalog.api.enrich import enrich_bp
from catalog.api.import_export import io_bp
from catalog.api.movies import movies_bp
from flask import Flask as _Flask, jsonify

from catalog.io_utils import import_catalog_from_json
from catalog.logging_config import configure_logging
from catalog.models import Catalog


class Flask(_Flask):
    catalog: Catalog


def create_app(config = None) -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.update(config or {})

    app.catalog = import_catalog_from_json(app.config.get("CATALOG_PATH"))

    app.register_blueprint(movies_bp)
    app.register_blueprint(io_bp)
    app.register_blueprint(enrich_bp)

    @app.errorhandler(400)
    def handle_bad_request(err):
        return jsonify(error=err.description), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify(error=err.description), 404

    return app

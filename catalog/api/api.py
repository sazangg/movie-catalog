from flask import jsonify
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from catalog.api.enrich import enrich_bp
from catalog.api.import_export import io_bp
from catalog.api.movies import movies_bp
from catalog.api.auth import auth_bp
from catalog.api.my_flask import Flask
from catalog.config import Config
from catalog.logging_config import configure_logging
from catalog.services import load_catalog


def create_app(config: dict | None = None) -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(config or {})

    app.catalog = load_catalog(app.config["CATALOG_PATH"])

    JWTManager(app)

    app.register_blueprint(movies_bp)
    app.register_blueprint(io_bp)
    app.register_blueprint(enrich_bp)
    app.register_blueprint(auth_bp)

    @app.errorhandler(400)
    def handle_bad_request(err):
        return jsonify(error=err.description), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify(error=err.description), 404

    @app.errorhandler(ValueError)
    def handle_bad_data(err):
        return jsonify(error=str(err)), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        payload = {"error": e.description, "message": e.description}
        return jsonify(payload), e.code

    return app

from flask import jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_seasurf import SeaSurf
from flask_talisman import Talisman
from werkzeug.exceptions import HTTPException

from catalog.api.auth import auth_bp
from catalog.api.enrich import enrich_bp
from catalog.api.extensions import limiter
from catalog.api.import_export import io_bp
from catalog.api.movies import movies_bp
from catalog.api.my_flask import Flask
from catalog.config import Config
from catalog.logging_config import configure_logging
from catalog.services import load_catalog

csrf = SeaSurf()


def create_app(config: dict | None = None) -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(config or {})

    app.catalog = load_catalog(app.config["CATALOG_PATH"])

    CORS(
        app,
        origins=["http://localhost:3000"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    )
    JWTManager(app)
    limiter.init_app(app)
    Talisman(
        app,
        content_security_policy={
            "default-src": ["'self'"],
            # you can add cdn domains, etc.
        },
        force_https=False,  # set True if you ALWAYS run HTTPS
        strict_transport_security=True,
        frame_options="DENY",
    )
    csrf.init_app(app)

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

    @app.errorhandler(429)
    def handle_rate_limits(e):
        return jsonify(error="Rate limit exceeded", details=str(e.description)), 429

    return app

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify

from catalog.io_utils import import_catalog_from_json


def configure_logging(log_file: str = "logs/app.log") -> None:
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
    app.logger.info(config or {})

    catalog = import_catalog_from_json(app.config.get("CATALOG_PATH"))

    app.catalog = catalog

    @app.route("/movies", methods=["GET"])
    def list_movies():
        movies = [m.__dict__ for m in app.catalog]
        return jsonify(movies=movies), 200

    return app


def main():
    app = create_app()
    app.run(host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()

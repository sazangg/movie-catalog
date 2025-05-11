import logging
from logging.handlers import RotatingFileHandler

from flask import Flask


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


def create_app() -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.logger.info("Flask app initialized")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000)

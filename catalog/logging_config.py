import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


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

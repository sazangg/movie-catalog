from pathlib import Path

from catalog.api.api import create_app


def main():
    app = create_app()
    base = Path(__file__).resolve().parent.parent  # project root
    cert = base / "certs" / "server.crt"
    key = base / "certs" / "server.key"
    app.run(
        host="127.0.0.1",
        port=5000,
        ssl_context=(str(cert), str(key)),
    )


if __name__ == "__main__":
    main()

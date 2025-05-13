from functools import wraps
from typing import Callable

from flask import abort, current_app, request


def require_api_key(fn: Callable):
    @wraps(fn)
    def decorated(*args, **kwargs):
        client_key = request.headers.get("X-API-Key")
        expected = current_app.config["API_KEY"]
        if not client_key or client_key != expected:
            abort(401, description="Invalid or missing API key")
        return fn(*args, **kwargs)

    return decorated

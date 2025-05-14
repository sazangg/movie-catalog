from datetime import timedelta
from functools import wraps
from typing import Callable

from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, jwt_required
from catalog.api.extensions import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

USER_DB = {
    "admin": {
        "password": "password123",
        "roles": ["admin"],
    },
}


def require_api_key(fn: Callable):
    @wraps(fn)
    def decorated(*args, **kwargs):
        client_key = request.headers.get("X-API-Key")
        expected = current_app.config["API_KEY"]
        if not client_key or client_key != expected:
            abort(401, description="Invalid or missing API key")
        return fn(*args, **kwargs)

    return decorated


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(limit_value="6 per minute")
def login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")

    user = USER_DB.get(username)
    if not user or user["password"] != password:
        abort(401, description="Bad credentials")

    token = create_access_token(
        identity=username,
        additional_claims={"roles": user["roles"]},
        expires_delta=timedelta(hours=1),
    )
    return jsonify(access_token=token), 200


def requires_role(role: str = "admin"):
    def decorator(fn):
        @jwt_required()
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if role not in claims["roles"]:
                abort(403, description=f"Access not authorized for role: {role}")
            return fn(*args, **kwargs)

        return wrapper

    return decorator

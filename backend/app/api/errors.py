"""Format d'erreur unique : {"error": {"code": ..., "message": ..., "fields"?: [...]}}."""

import logging

from flask import Flask, jsonify
from flask_limiter.errors import RateLimitExceeded
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: list[dict] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields


def error_response(status: int, code: str, message: str, fields: list[dict] | None = None):
    error = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return jsonify({"error": error}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return error_response(err.status, err.code, err.message, err.fields)

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(_err):
        return error_response(
            429, "rate_limited", "Trop de demandes en peu de temps. Réessayez dans quelques minutes."
        )

    @app.errorhandler(HTTPException)
    def handle_http(err: HTTPException):
        return error_response(err.code or 500, "http_error", err.description or "Erreur HTTP")

    @app.errorhandler(Exception)
    def handle_unexpected(_err):
        logger.exception("Erreur inattendue")
        return error_response(500, "internal_error", "Une erreur interne est survenue.")

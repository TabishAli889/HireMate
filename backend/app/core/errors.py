"""Global exception handlers so clients always receive a JSON `{"detail": "<message>"}` body."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError

logger = logging.getLogger("hiremate")


def _first_validation_message(exc: RequestValidationError) -> str:
    """Turn Pydantic's error list into one human sentence for toasts."""
    errors = exc.errors()
    if not errors:
        return "Some of the data sent was invalid."
    first = errors[0]
    message = str(first.get("msg", "Invalid value")).removeprefix("Value error, ")
    location = [str(part) for part in first.get("loc", ()) if part != "body"]
    if first.get("type") == "value_error" or not location:
        return message
    return f"{'.'.join(location)}: {message}"


def register_exception_handlers(app: FastAPI) -> None:
    """Map AppError subclasses to their status codes; hide internals for anything else."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.warning("%s on %s %s: %s", type(exc).__name__, request.method, request.url.path, exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": _first_validation_message(exc), "errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side. Please try again."},
        )

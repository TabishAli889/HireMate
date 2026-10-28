"""Domain exceptions that map cleanly to HTTP responses."""


class AppError(Exception):
    """Base error with a user-facing message, HTTP status and optional headers."""

    status_code: int = 400
    default_detail: str = "Request could not be completed."

    def __init__(self, detail: str | None = None, *, status_code: int | None = None, headers: dict[str, str] | None = None):
        self.detail = detail or self.default_detail
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    default_detail = "Not found."


class ConflictError(AppError):
    status_code = 409
    default_detail = "That already exists."


class InvalidFileError(AppError):
    status_code = 422
    default_detail = "That file could not be read."


class FileTooLargeError(AppError):
    status_code = 413
    default_detail = "That file is too large."


class RateLimitedError(AppError):
    status_code = 429
    default_detail = "You're going a bit fast. Please wait a moment and try again."

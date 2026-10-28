"""API key gate for production.

The browser never talks to this API directly: the Next.js proxy does, server-to-server, and adds
`X-API-Key`. With API_KEY set, every other caller gets 401, so the public Render URL can't be used
to read your profile or spend your Groq quota. `/health` stays open for uptime checks.

A plain ASGI middleware (not BaseHTTPMiddleware) so streamed SSE responses pass through untouched.
"""

import hmac

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

OPEN_PATHS = frozenset({"/health"})


class ApiKeyMiddleware:
    def __init__(self, app: ASGIApp, api_key: str):
        self.app = app
        self.api_key = api_key.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS" or scope["path"] in OPEN_PATHS:
            await self.app(scope, receive, send)
            return
        provided = dict(scope["headers"]).get(b"x-api-key", b"")
        if hmac.compare_digest(provided, self.api_key):
            await self.app(scope, receive, send)
            return
        response = JSONResponse({"detail": "Missing or invalid API key."}, status_code=401)
        await response(scope, receive, send)

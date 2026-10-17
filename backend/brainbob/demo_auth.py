"""Shared demo gate. Selected members remain fictional personas, not authenticated users."""
import base64
import secrets
from starlette.responses import JSONResponse


class DemoAuth:
    def __init__(self, app, password):
        self.app = app
        self.expected = base64.b64encode(f"brainbob:{password}".encode())

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or (scope["path"] == "/healthz" and scope["method"] in ("GET", "HEAD")):
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        parts = headers.get(b"authorization", b"").split(b" ", 1)
        allowed = len(parts) == 2 and parts[0].lower() == b"basic" and secrets.compare_digest(parts[1], self.expected)
        # Basic credentials are ambient browser credentials: reject cross-site writes.
        cross_site = scope["method"] not in ("GET", "HEAD", "OPTIONS") and headers.get(b"sec-fetch-site") == b"cross-site"
        if not allowed or cross_site:
            response = JSONResponse({"detail": "Demo access required"}, status_code=403 if cross_site else 401,
                                    headers={"WWW-Authenticate": 'Basic realm="BrainBob demo", charset="UTF-8"',
                                             "Cache-Control": "no-store"})
            return await response(scope, receive, send)
        async def no_cache(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"]
                message = {**message, "headers": headers + [(b"cache-control", b"no-store, no-transform")]}
            await send(message)
        await self.app(scope, receive, no_cache)

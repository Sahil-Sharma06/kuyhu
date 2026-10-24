"""FastAPI application entrypoint."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "public, max-age=300",
}

app = FastAPI(title="Wind Forecast Monitor", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_methods=["GET"],
    allow_headers=[],
)


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    # The interactive docs need scripts/styles, so leave their CSP to FastAPI.
    if request.url.path.startswith("/api/"):
        response.headers.update(SECURITY_HEADERS)
    return response


app.include_router(router)

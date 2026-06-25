from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import chat


def create_app() -> FastAPI:
    app = FastAPI(
        title="Marx AI Assistant API",
        description="3D Marx AI floating assistant backend",
        version="1.0.0",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Marx-Reply"],   # expose custom header to browser
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(chat.router, prefix="/api")

    return app

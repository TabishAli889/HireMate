"""FastAPI application factory. Run with: uvicorn app.main:app --reload"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal, init_db
from app.core.errors import register_exception_handlers
from app.core.security import ApiKeyMiddleware
from app.routers import agent, applications, dashboard, documents, health, jobs, profile
from app.services.seed import remove_demo_profile, seed_demo_profile


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create tables; seed demo data only when SEED_DEMO_DATA=true, otherwise clear any old demo profile."""
    init_db()
    with SessionLocal() as db:
        if get_settings().seed_demo_data:
            seed_demo_profile(db)
        else:
            remove_demo_profile(db)
    yield


class InsecureProductionConfig(RuntimeError):
    """Raised at startup when production settings would expose the API."""


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI app."""
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if settings.is_production and len(settings.api_key_value) < 24:
        raise InsecureProductionConfig(
            "ENVIRONMENT=production needs API_KEY set to a long random secret (24+ characters). "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # Interactive docs are handy locally but advertise every endpoint in production.
    docs = {} if not settings.is_production else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan, **docs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    if settings.api_key_value:
        app.add_middleware(ApiKeyMiddleware, api_key=settings.api_key_value)

    app.include_router(health.router)
    app.include_router(profile.router)
    app.include_router(jobs.router)
    app.include_router(documents.router)
    app.include_router(applications.router)
    app.include_router(dashboard.router)
    app.include_router(agent.router)
    return app


app = create_app()

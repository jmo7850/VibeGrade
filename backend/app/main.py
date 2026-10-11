"""Main FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import rubric, scans
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging(settings.log_level, settings.log_format)
    logger.info("Starting VibeGrade API", env=settings.app_env)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Load rubric
    from app.services.rubric import get_rubric as load_rubric
    load_rubric(settings.rubric_version)
    logger.info("Rubric loaded", version=settings.rubric_version)

    yield

    # Shutdown
    logger.info("Shutting down VibeGrade API")
    await close_db()


app = FastAPI(
    title="VibeGrade API",
    description="Evidence-driven software quality and production-readiness evaluation",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.app_debug else None,
    redoc_url="/api/redoc" if settings.app_debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scans.router)
app.include_router(rubric.router)


# Serve frontend in production
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"detail": "Not found"}


@app.get("/api/health")
async def health():
    """Simple health check."""
    return {"status": "ok", "service": "vibegrade-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )

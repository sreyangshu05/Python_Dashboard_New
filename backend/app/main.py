"""WindScope UK Backend — FastAPI Application."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="WindScope UK API",
    description=(
        "Wind Forecast Intelligence & Procurement Decision Support. "
        "Provides forecast vs. actual wind generation analysis using Elexon BMRS data."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)

# Locate frontend dist if built
dist_candidates = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),
    Path("./frontend/dist"),
]

dist_dir = None
for candidate in dist_candidates:
    if candidate.exists() and (candidate / "index.html").exists():
        dist_dir = candidate
        break

def root():
    """Root endpoint redirect to API docs."""
    return {
        "service": "WindScope UK API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }


if dist_dir:
    logging.info("Serving frontend static assets from %s", dist_dir)
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api"):
            return None
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")
else:
    app.add_api_route("/", root, methods=["GET"])

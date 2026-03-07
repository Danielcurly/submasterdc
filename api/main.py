#!/usr/bin/env python3
"""
FastAPI Backend for SubMasterDC
Thin API layer over the existing Python core logic
"""

import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database.connection import init_database
from core.worker import start_worker

from api.routers import config, libraries, tasks, scan, ai, explorer, debug


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Initialize database
    init_database()
    # Start background worker
    if not any(t.name == "SubtitleWorker" for t in threading.enumerate()):
        start_worker()
    yield


app = FastAPI(
    title="SubmasterDC API",
    description="Backend API for SubmasterDC Subtitle Automation",
    version="v0.1.2",
    lifespan=lifespan
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(config.router, prefix="/api/config", tags=["Config"])
app.include_router(libraries.router, prefix="/api/libraries", tags=["Libraries"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(scan.router, prefix="/api/scan", tags=["Scan"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(explorer.router, prefix="/api/explorer", tags=["Explorer"])
app.include_router(debug.router, prefix="/api/debug", tags=["Debug"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Serve Next.js Frontend Static Files in Production
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "out")
if os.path.exists(FRONTEND_DIR):
    app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_DIR, "_next")), name="next_assets")
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        # Catch-all for Next.js client-side routing
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), status_code=200)
        return HTMLResponse(content="Frontend build not found.", status_code=404)

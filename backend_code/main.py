import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from routers.api_router import api_router

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Social Web App API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend_code"
INDEX_FILE = FRONTEND_DIR / "index.html"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Backend API for a social web application with authentication, posts, messaging, moderation, and admin capabilities.",
)

origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()]
if not origins:
    origins = ["*"]

allow_credentials = origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", tags=["root"])
async def root():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))

    return {
        "message": "Welcome to Social Web App API",
        "status": "ok",
        "version": APP_VERSION,
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api") or full_path in {"health", "docs", "openapi.json", "redoc"}:
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_DIR.exists():
        requested = FRONTEND_DIR / full_path
        if requested.exists() and requested.is_file():
            return FileResponse(str(requested))
        if INDEX_FILE.exists():
            return FileResponse(str(INDEX_FILE))

    raise HTTPException(status_code=404, detail="Not found")

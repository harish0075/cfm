"""
CFM V1 — Financial Input Ingestion & Normalization Backend

Main application entry point.
Registers all API routers and initializes the database on startup.

Run with:
    uvicorn main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine

# Import all models so they are registered with Base.metadata
from models import User, Asset, FinancialEntry  # noqa: F401

# Import API routers
from api.onboard import router as onboard_router
from api.inputs import router as inputs_router
from api.state import router as state_router


# ── Lifespan — DB table creation on startup ───────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup, dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="CFM V1 — Financial Input Engine",
    description=(
        "Multi-source financial input ingestion and normalization system. "
        "Accepts text, SMS, receipt images (OCR), bank statements (PDF), "
        "and audio inputs. Normalizes all into a unified financial dataset per user."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────────────────
app.include_router(onboard_router, tags=["Onboarding"])
app.include_router(inputs_router, tags=["Inputs"])
app.include_router(state_router, tags=["State"])


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "CFM V1 — Financial Input Engine",
        "version": "1.0.0",
    }

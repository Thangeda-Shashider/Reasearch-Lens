"""
ResearchLens — FastAPI entry point.
Run: uvicorn main:app --reload  (from backend/ directory)
"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
# Import models so SQLAlchemy registers them before init_db creates tables
import models.db_models  # noqa: F401
from routers import upload, analysis, gaps, visualizations, report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="ResearchLens API",
    description="Citation-Aware Research Gap Identification System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(gaps.router)
app.include_router(visualizations.router)
app.include_router(report.router)


@app.on_event("startup")
async def startup():
    logger.info("Initialising database…")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()

    # Pre-download NLTK data silently
    try:
        import nltk
        for pkg in ("stopwords", "punkt", "punkt_tab"):
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass
    except Exception:
        pass

    # Warm up spaCy model (optional — fails gracefully if not installed)
    try:
        import spacy
        spacy.load("en_core_web_sm")
        logger.info("spaCy en_core_web_sm loaded ✓")
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' not found. "
            "Run: python -m spacy download en_core_web_sm"
        )
    except Exception as e:
        logger.warning("spaCy load error: %s", e)

    logger.info("ResearchLens API ready ✓")


@app.get("/")
async def root():
    return {
        "name": "ResearchLens API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

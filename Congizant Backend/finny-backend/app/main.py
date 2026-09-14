import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.database.database import init_db
from app.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("finny")

# Silence noisy third-party debug logging that degrades I/O and freezes PDF parsing
for noisy_logger in ("pdfminer", "pdfplumber", "PIL", "urllib3"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    logger.info("Initializing database schema...")
    try:
        init_db()
        # Ensure user_id column exists on documents table if migrating existing DB
        from app.database.database import engine
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("documents")]
        if "user_id" not in columns:
            logger.info("Migrating schema: Adding user_id column to documents table...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)"))
                conn.commit()
            logger.info("Migration complete: user_id column added.")
        logger.info("Database schema initialized successfully.")
        # Ensure demo documents exist for grounded demo analysis & chatbot
        try:
            from app.database.database import SessionLocal
            from app.database.demo_seeder import ensure_demo_documents
            with SessionLocal() as db_session:
                ensure_demo_documents(db_session)
        except Exception as seed_err:
            logger.warning("Demo document seeding error: %s", seed_err)

        # Pre-warm Ollama model in background daemon thread to eliminate first-token cold start latency
        try:
            import threading
            def _warm_ollama():
                try:
                    import urllib.request, json
                    req = urllib.request.Request(
                        f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                        data=json.dumps({
                            "model": settings.OLLAMA_MODEL,
                            "keep_alive": "30m",
                            "prompt": "ping"
                        }).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        resp.read()
                    logger.info("Ollama model pre-warmed and resident in memory.")
                except Exception as warm_e:
                    logger.debug("Ollama warm-up notice (non-fatal): %s", warm_e)
            threading.Thread(target=_warm_ollama, daemon=True).start()
        except Exception as t_err:
            logger.debug("Failed to spawn Ollama warm-up thread: %s", t_err)
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
    yield
    logger.info("Finny Backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-ready backend service for financial document ingestion, "
        "table extraction (PDF, Excel, CSV), and canonical accounting normalization."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors cleanly without exposing internals."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors()}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Capture unexpected internal exceptions, log stack trace, return 500 without leaking details."""
    logger.exception("Unhandled server exception processing %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."}
    )


# Health Check
@app.get("/api/health", tags=["Health"], summary="System health check")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "supported_extensions": list(sorted(settings.ALLOWED_EXTENSIONS)),
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB
    }


# Mount API V1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Mount Frontend Static Assets if built
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


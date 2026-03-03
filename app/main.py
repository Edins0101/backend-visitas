import logging
import os
import time
from typing import Optional
from dotenv import load_dotenv

# Ensure Paddle uses legacy executor (avoid oneDNN/PIR crashes on some Windows builds)
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.twilio import router as twilio_router
from app.api.routers.ocr import router as ocr_router
from app.api.routers.qr import router as qr_router
from app.api.routers.catalogo import router as catalogo_router
from app.api.routers.acceso import router as acceso_router
from app.api.routers.reporte_acceso import router as reporte_acceso_router


def _configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


_configure_logging()
logger = logging.getLogger("app.http")


app = FastAPI()


def _parse_cors_allowed_origins(raw: Optional[str]) -> list[str]:
    if not raw:
        return ["*"]
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]


allowed_origins = _parse_cors_allowed_origins(os.getenv("CORS_ALLOWED_ORIGINS"))
allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"

if allow_credentials and "*" in allowed_origins:
    logger.warning("CORS_ALLOW_CREDENTIALS=true is incompatible with wildcard origins. Falling back to false.")
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    start = time.perf_counter()
    client = request.client.host if request.client else "-"
    logger.info(
        "request_started method=%s path=%s client=%s",
        request.method,
        request.url.path,
        client,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "request_failed method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request_finished method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(qr_router)

app.include_router(ocr_router)
app.include_router(catalogo_router)
app.include_router(twilio_router)
app.include_router(acceso_router)
app.include_router(reporte_acceso_router)

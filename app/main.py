import logging
import os
import time
from dotenv import load_dotenv

# Ensure Paddle uses legacy executor (avoid oneDNN/PIR crashes on some Windows builds)
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

load_dotenv()

from fastapi import FastAPI, Request
from app.api.routers.twilio import router as twilio_router
from app.api.routers.ocr import router as ocr_router
from app.api.routers.qr import router as qr_router
from app.api.routers.catalogo import router as catalogo_router


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

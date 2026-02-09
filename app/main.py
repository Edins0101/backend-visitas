import os
from dotenv import load_dotenv

# Ensure Paddle uses legacy executor (avoid oneDNN/PIR crashes on some Windows builds)
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

load_dotenv()

from fastapi import FastAPI
from app.api.routers.qr import router as qr_router
from app.api.routers.ocr import router as ocr_router
from app.api.routers.catalogo import router as catalogo_router
from app.api.routers.twilio import router as twilio_router

app = FastAPI()
app.include_router(qr_router)
app.include_router(ocr_router)
app.include_router(catalogo_router)
app.include_router(twilio_router)

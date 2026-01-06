from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.routers.qr import router as qr_router

app = FastAPI()
app.include_router(qr_router)

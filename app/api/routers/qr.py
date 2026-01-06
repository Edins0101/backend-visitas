from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.services.qr_service import QRService
from app.infrastructure.qr_repository import QRRepository

router = APIRouter(prefix="/qrs", tags=["QR"])

def get_qr_service(db: Session = Depends(get_db)) -> QRService:
    return QRService(repo=QRRepository(db))

@router.post("/{qr_id}/validar")
def validar_qr(qr_id: int, marcar_usado: bool = True, usuario: str = "system",
               service: QRService = Depends(get_qr_service)):
    return service.validar_por_id(qr_id, marcar_usado, usuario)

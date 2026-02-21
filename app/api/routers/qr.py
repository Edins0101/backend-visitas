import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.services.qr_service import QRService
from app.infrastructure.qr_repository import QRRepository

router = APIRouter(prefix="/qrs", tags=["QR"])
logger = logging.getLogger(__name__)


def get_qr_service(db: Session = Depends(get_db)) -> QRService:
    return QRService(repo=QRRepository(db))

@router.post("/{qr_id}/validar")
def validar_qr(qr_id: int, marcar_usado: bool = True, usuario: str = "system",
               service: QRService = Depends(get_qr_service)):
    logger.info(
        "validar_qr_request qr_id=%s marcar_usado=%s usuario=%s",
        qr_id,
        marcar_usado,
        usuario,
    )

    response = service.validar_por_id(qr_id, marcar_usado, usuario)
    if response.success:
        logger.info("validar_qr_response status=200 payload=%s", response.model_dump())
        return response

    code = response.error.code if response.error else None
    status_code = status.HTTP_400_BAD_REQUEST
    if code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND

    logger.warning("validar_qr_response status=%s payload=%s", status_code, response.model_dump())
    return JSONResponse(status_code=status_code, content=response.model_dump())

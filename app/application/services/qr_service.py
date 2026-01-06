from datetime import datetime, timezone
from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.errors import NotFoundError, BusinessRuleError
from app.infrastructure.qr_repository import QRRepository

class QRService:
    def __init__(self, repo: QRRepository):
        self.repo = repo

    def validar_por_id(self, qr_id: int, marcar_usado: bool, usuario: str) -> GeneralResponse[dict]:
        qr = self.repo.get_by_id(qr_id)
        if not qr:
            return GeneralResponse(success=False, error=ErrorDTO(code="NOT_FOUND", message="QR no existe"))

        ahora = datetime.now(timezone.utc)
        if not qr.es_vigente(ahora):
            return GeneralResponse(success=False, error=ErrorDTO(code="QR_INVALID", message="QR no vigente"))

        if marcar_usado:
            self.repo.mark_used(qr_id, ahora, usuario)

        return GeneralResponse(success=True, data={"qr_id": qr.qr_pk})
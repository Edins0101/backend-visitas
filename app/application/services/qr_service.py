from datetime import datetime
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

        # Keep naive timestamps to match DB columns without timezone.
        ahora = datetime.now()
        if not qr.es_vigente(ahora):
            return GeneralResponse(success=False, error=ErrorDTO(code="QR_INVALID", message="QR no vigente"))

        if marcar_usado:
            self.repo.mark_used(qr_id, ahora, usuario)
            self.repo.db.commit()
            message = "QR marcado como usado"
        else:
            message = "QR consultado"

        return GeneralResponse(success=True, message=message, data={"qr_id": qr.qr_pk})

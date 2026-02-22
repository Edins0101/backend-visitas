import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.dtos.requests.acceso_create_request import AccesoCreateRequestDTO
from app.application.dtos.requests.acceso_twilio_decision_request import AccesoTwilioDecisionRequestDTO
from app.application.services.acceso_service import AccesoService
from app.infrastructure.acceso_repository import AccesoRepository

router = APIRouter(prefix="/accesos", tags=["Accesos"])
logger = logging.getLogger(__name__)


def _as_loggable_payload(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def get_acceso_service(db: Session = Depends(get_db)) -> AccesoService:
    return AccesoService(repo=AccesoRepository(db))


@router.post("")
def crear_acceso_pendiente(payload: AccesoCreateRequestDTO, service: AccesoService = Depends(get_acceso_service)):
    logger.info(
        "crear_acceso_request vivienda_visita_fk=%s motivo=%s",
        payload.viviendaVisitaFk,
        payload.motivo,
    )
    response = service.crear_acceso_pendiente(
        vivienda_visita_fk=payload.viviendaVisitaFk,
        motivo=payload.motivo,
        visitor_name=payload.visitorName,
    )

    if response.success:
        logger.info("crear_acceso_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    code = response.error.code if response.error else None
    status_code = status.HTTP_400_BAD_REQUEST
    if code in {"RESIDENT_NOT_FOUND", "NOT_FOUND"}:
        status_code = status.HTTP_404_NOT_FOUND
    logger.warning("crear_acceso_response status=%s payload=%s", status_code, _as_loggable_payload(response))
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.post("/twilio-decision")
def aplicar_decision_twilio(
    payload: AccesoTwilioDecisionRequestDTO,
    service: AccesoService = Depends(get_acceso_service),
):
    logger.info(
        "aplicar_decision_twilio_request decision=%s visit_id=%s call_sid=%s digit=%s",
        payload.decision,
        payload.visitId,
        payload.callSid,
        payload.digit,
    )
    response = service.aplicar_decision_twilio(
        decision=payload.decision,
        visit_id=payload.visitId,
        digit=payload.digit,
        call_sid=payload.callSid,
    )

    if response.success:
        logger.info("aplicar_decision_twilio_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    code = response.error.code if response.error else None
    status_code = status.HTTP_400_BAD_REQUEST
    if code in {"ACCESS_NOT_FOUND", "NOT_FOUND"}:
        status_code = status.HTTP_404_NOT_FOUND
    logger.warning("aplicar_decision_twilio_response status=%s payload=%s", status_code, _as_loggable_payload(response))
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.get("/{acceso_pk}")
def obtener_acceso(acceso_pk: int, service: AccesoService = Depends(get_acceso_service)):
    logger.info("obtener_acceso_request acceso_pk=%s", acceso_pk)
    response = service.obtener_por_id(acceso_pk)
    if response.success:
        logger.info("obtener_acceso_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    logger.warning("obtener_acceso_response status=404 payload=%s", _as_loggable_payload(response))
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=response.model_dump())

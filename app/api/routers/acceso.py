import logging
import os

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.dtos.requests.acceso_create_request import AccesoCreateRequestDTO
from app.application.dtos.requests.acceso_start_call_request import AccesoStartCallRequestDTO
from app.application.dtos.requests.acceso_twilio_decision_request import AccesoTwilioDecisionRequestDTO
from app.application.dtos.requests.acceso_update_placa_request import AccesoUpdatePlacaRequestDTO
from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.application.services.acceso_service import AccesoService
from app.application.services.twilio_service import TwilioService
from app.infrastructure.acceso_repository import AccesoRepository
from app.infrastructure.twilio_call_adapter import TwilioCallAdapter
from app.infrastructure.twilio_decision_notifier_adapter import WebhookAccessDecisionNotifierAdapter
from app.infrastructure.twilio_twiml_adapter import TwilioTwimlAdapter

router = APIRouter(prefix="/accesos", tags=["Accesos"])
logger = logging.getLogger(__name__)


def _as_loggable_payload(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def get_acceso_service(db: Session = Depends(get_db)) -> AccesoService:
    return AccesoService(repo=AccesoRepository(db))


def get_twilio_service() -> TwilioService:
    return TwilioService.from_env(
        call_port=TwilioCallAdapter(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        ),
        twiml_port=TwilioTwimlAdapter(),
        notifier_port=WebhookAccessDecisionNotifierAdapter(
            webhook_url=os.getenv("TWILIO_DECISION_WEBHOOK_URL"),
        ),
    )


@router.post("")
def crear_acceso_pendiente(payload: AccesoCreateRequestDTO, service: AccesoService = Depends(get_acceso_service)):
    logger.info(
        "crear_acceso_request vivienda_visita_fk=%s motivo=%s foto_base64_len=%s",
        payload.viviendaVisitaFk,
        payload.motivo,
        len(payload.fotoRostroVivoBase64 or ""),
    )
    response = service.crear_acceso_pendiente(
        vivienda_visita_fk=payload.viviendaVisitaFk,
        motivo=payload.motivo,
        visitor_name=payload.visitorName,
        foto_rostro_vivo_base64=payload.fotoRostroVivoBase64,
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


@router.post("/manual")
def crear_acceso_manual_extraordinario(
    viviendaVisitaFk: int = Form(...),
    motivo: str = Form(...),
    detalle: str | None = Form(default=None),
    personaGuardiaFk: int | None = Form(default=None),
    personaResidenteAutorizaFk: int | None = Form(default=None),
    placa: str | None = Form(default=None),
    usuarioCreado: str | None = Form(default=None),
    imagen: UploadFile = File(...),
    service: AccesoService = Depends(get_acceso_service),
):
    allowed_content_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if (imagen.content_type or "").lower() not in allowed_content_types:
        response = GeneralResponse(
            success=False,
            message="Tipo de imagen no soportado",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Tipo de imagen no soportado"),
        )
        logger.warning("crear_acceso_manual_response status=415 payload=%s", _as_loggable_payload(response))
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = imagen.file.read()
    logger.info(
        "crear_acceso_manual_request vivienda_visita_fk=%s motivo=%s guardia_fk=%s residente_fk=%s placa=%s "
        "filename=%s content_type=%s image_size=%s",
        viviendaVisitaFk,
        motivo,
        personaGuardiaFk,
        personaResidenteAutorizaFk,
        placa,
        imagen.filename,
        imagen.content_type,
        len(image_bytes),
    )
    response = service.crear_acceso_manual_extraordinario(
        vivienda_visita_fk=viviendaVisitaFk,
        motivo=motivo,
        detalle=detalle,
        persona_guardia_fk=personaGuardiaFk,
        persona_residente_autoriza_fk=personaResidenteAutorizaFk,
        placa=placa,
        image_bytes=image_bytes,
        image_content_type=imagen.content_type,
        image_filename=imagen.filename,
        usuario_creado=usuarioCreado,
    )

    if response.success:
        logger.info("crear_acceso_manual_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    code = response.error.code if response.error else None
    status_code = status.HTTP_400_BAD_REQUEST
    if code in {"VIVIENDA_NOT_FOUND", "GUARD_NOT_FOUND", "RESIDENT_AUTH_NOT_FOUND"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif code == "UNSUPPORTED_MEDIA":
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    logger.warning("crear_acceso_manual_response status=%s payload=%s", status_code, _as_loggable_payload(response))
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


@router.post("/{acceso_pk}/llamar")
def iniciar_llamada_autorizacion(
    acceso_pk: int,
    payload: AccesoStartCallRequestDTO | None = None,
    service: AccesoService = Depends(get_acceso_service),
):
    visitor_name = payload.visitorName if payload else None
    logger.info("iniciar_llamada_acceso_request acceso_pk=%s visitor=%s", acceso_pk, visitor_name)

    response = service.iniciar_llamada_autorizacion(
        acceso_pk=acceso_pk,
        twilio_service=get_twilio_service(),
        visitor_name=visitor_name,
    )

    if response.success:
        logger.info("iniciar_llamada_acceso_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    code = response.error.code if response.error else None
    status_code = status.HTTP_400_BAD_REQUEST
    if code in {"NOT_FOUND", "RESIDENT_NOT_FOUND"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif code in {"MISSING_ENV", "CALL_ERROR"}:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.warning("iniciar_llamada_acceso_response status=%s payload=%s", status_code, _as_loggable_payload(response))
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.get("/{acceso_pk}/estado")
def obtener_estado_acceso(acceso_pk: int, service: AccesoService = Depends(get_acceso_service)):
    logger.info("obtener_estado_acceso_request acceso_pk=%s", acceso_pk)
    response = service.obtener_estado_para_polling(acceso_pk)
    if response.success:
        logger.info("obtener_estado_acceso_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    logger.warning("obtener_estado_acceso_response status=404 payload=%s", _as_loggable_payload(response))
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=response.model_dump())


@router.get("/{acceso_pk}")
def obtener_acceso(acceso_pk: int, service: AccesoService = Depends(get_acceso_service)):
    logger.info("obtener_acceso_request acceso_pk=%s", acceso_pk)
    response = service.obtener_por_id(acceso_pk)
    if response.success:
        logger.info("obtener_acceso_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    logger.warning("obtener_acceso_response status=404 payload=%s", _as_loggable_payload(response))
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=response.model_dump())


@router.patch("/{acceso_pk}/placa")
def actualizar_placa_acceso(
    acceso_pk: int,
    payload: AccesoUpdatePlacaRequestDTO,
    service: AccesoService = Depends(get_acceso_service),
):
    logger.info(
        "actualizar_placa_acceso_request acceso_pk=%s placa=%s usuario=%s",
        acceso_pk,
        payload.placa,
        payload.usuarioActualizado,
    )
    response = service.actualizar_placa(
        acceso_pk=acceso_pk,
        placa=payload.placa,
        usuario_actualizado=payload.usuarioActualizado,
    )

    if response.success:
        logger.info("actualizar_placa_acceso_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    code = response.error.code if response.error else None
    status_code = status.HTTP_400_BAD_REQUEST
    if code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    logger.warning("actualizar_placa_acceso_response status=%s payload=%s", status_code, _as_loggable_payload(response))
    return JSONResponse(status_code=status_code, content=response.model_dump())

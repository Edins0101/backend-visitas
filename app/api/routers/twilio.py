import os
import logging
from uuid import uuid4

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import Response, JSONResponse

from app.application.dtos.requests.twilio_call_request import TwilioCallRequestDTO
from app.application.services.twilio_service import TwilioService
from app.infrastructure.in_memory_call_tracking_store import InMemoryCallTrackingStore
from app.infrastructure.twilio_call_adapter import TwilioCallAdapter
from app.infrastructure.twilio_decision_notifier_adapter import WebhookAccessDecisionNotifierAdapter
from app.infrastructure.twilio_twiml_adapter import TwilioTwimlAdapter

router = APIRouter(tags=["Twilio"])
logger = logging.getLogger(__name__)
call_tracking_store = InMemoryCallTrackingStore()


def _truncate(value: str, max_len: int = 320) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[:max_len]}..."


def _normalize_digit(value: str | None) -> str:
    raw_digit = (value or "").strip()
    extracted_digits = "".join(ch for ch in raw_digit if ch.isdigit())
    return extracted_digits[:1]


def _get_service() -> TwilioService:
    service = TwilioService.from_env(
        call_port=TwilioCallAdapter(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        ),
        twiml_port=TwilioTwimlAdapter(),
        notifier_port=WebhookAccessDecisionNotifierAdapter(
            webhook_url=os.getenv("TWILIO_DECISION_WEBHOOK_URL"),
        ),
    )
    return service


@router.post("/api/call")
def start_call(payload: TwilioCallRequestDTO, visitId: str | None = None):
    visit_id = (visitId or "").strip() or uuid4().hex
    logger.info(
        "start_call_request to=%s resident=%s visitor=%s visit_id=%s",
        payload.to,
        payload.residentName,
        payload.visitorName,
        visit_id,
    )

    service = _get_service()
    response = service.start_call(
        to=payload.to,
        resident_name=payload.residentName,
        visitor_name=payload.visitorName,
        visit_id=visit_id,
    )

    if response.success:
        call_sid = ""
        if response.data:
            call_sid = str(response.data.get("callSid", ""))

        if call_sid:
            record = call_tracking_store.register_call(
                call_sid=call_sid,
                visit_id=visit_id,
                to=payload.to,
                resident_name=payload.residentName or "",
                visitor_name=payload.visitorName or "",
            )
            logger.info("start_call_tracked call_sid=%s visit_id=%s", record["callSid"], record["visitId"])

        logger.info("start_call_response status=200 payload=%s", response.model_dump())
        return response

    status_code = status.HTTP_400_BAD_REQUEST
    if response.error and response.error.code in {"MISSING_ENV", "CALL_ERROR"}:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.warning("start_call_response status=%s payload=%s", status_code, response.model_dump())
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.api_route("/twilio/voice", methods=["GET", "POST"])
def twilio_voice(
    residentName: str | None = None,
    visitorName: str | None = None,
    visitId: str | None = None,
):
    logger.info(
        "twilio_voice_request resident=%s visitor=%s visit_id=%s",
        residentName,
        visitorName,
        visitId,
    )

    service = _get_service()
    twiml = service.build_voice_twiml(
        resident_name=residentName,
        visitor_name=visitorName,
        visit_id=visitId,
    )
    logger.info("twilio_voice_response status=200 twiml=%s", _truncate(twiml))
    return Response(content=twiml, media_type="text/xml")


@router.api_route("/twilio/voice/handle-input", methods=["GET", "POST"])
def twilio_handle_input(
    request: Request,
    Digits: str | None = Form(default=None),
    CallSid: str | None = Form(default=None),
    residentName: str | None = None,
    visitorName: str | None = None,
    visitId: str | None = None,
):
    digit = Digits if Digits is not None else request.query_params.get("Digits")
    call_sid = CallSid if CallSid is not None else request.query_params.get("CallSid")
    normalized_digit = _normalize_digit(digit)
    logger.info(
        "twilio_handle_input_request raw_digits=%s resolved_digit=%s normalized_digit=%s call_sid=%s resident=%s visitor=%s visit_id=%s",
        Digits,
        digit,
        normalized_digit,
        call_sid,
        residentName,
        visitorName,
        visitId,
    )

    if normalized_digit == "1":
        call_tracking_store.update_decision(
            call_sid=call_sid,
            visit_id=visitId,
            decision="authorized",
            digit=normalized_digit,
        )
    elif normalized_digit == "2":
        call_tracking_store.update_decision(
            call_sid=call_sid,
            visit_id=visitId,
            decision="rejected",
            digit=normalized_digit,
        )

    service = _get_service()
    twiml = service.build_handle_input_twiml(
        digit=digit,
        resident_name=residentName,
        visitor_name=visitorName,
        visit_id=visitId,
        call_sid=call_sid,
    )
    logger.info("twilio_handle_input_response status=200 twiml=%s", _truncate(twiml))
    return Response(content=twiml, media_type="text/xml")


@router.post("/twilio/voice/status")
def twilio_voice_status(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str | None = Form(default=None),
    AnsweredBy: str | None = Form(default=None),
    From: str | None = Form(default=None),
    To: str | None = Form(default=None),
    visitId: str | None = None,
):
    resolved_visit_id = visitId or request.query_params.get("visitId")
    record = call_tracking_store.update_status(
        call_sid=CallSid,
        visit_id=resolved_visit_id,
        call_status=CallStatus,
        duration=CallDuration,
        answered_by=AnsweredBy,
        from_number=From,
        to_number=To,
    )

    logger.info(
        "twilio_status_callback call_sid=%s visit_id=%s call_status=%s duration=%s answered_by=%s",
        CallSid,
        resolved_visit_id,
        CallStatus,
        CallDuration,
        AnsweredBy,
    )
    return {"success": True, "data": record}


@router.get("/api/call/{call_sid}/status")
def get_call_status(call_sid: str):
    record = call_tracking_store.get_by_call_sid(call_sid)
    if not record:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "No se encontro llamada",
                "error": {"code": "CALL_NOT_FOUND", "message": "No se encontro llamada"},
            },
        )
    return {"success": True, "data": record}


@router.get("/api/visit/{visit_id}/status")
def get_visit_call_status(visit_id: str):
    record = call_tracking_store.get_by_visit_id(visit_id)
    if not record:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "message": "No se encontro visita",
                "error": {"code": "VISIT_NOT_FOUND", "message": "No se encontro visita"},
            },
        )
    return {"success": True, "data": record}

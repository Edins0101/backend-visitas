import os

from fastapi import APIRouter, Form, status
from fastapi.responses import Response, JSONResponse

from app.application.dtos.requests.twilio_call_request import TwilioCallRequestDTO
from app.application.services.twilio_service import TwilioService
from app.infrastructure.twilio_call_adapter import TwilioCallAdapter
from app.infrastructure.twilio_decision_notifier_adapter import WebhookAccessDecisionNotifierAdapter
from app.infrastructure.twilio_twiml_adapter import TwilioTwimlAdapter

router = APIRouter(tags=["Twilio"])


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


@router.get("/")
def twilio_health():
    return {"status": "ok", "service": "twilio"}


@router.post("/api/call")
def start_call(payload: TwilioCallRequestDTO):
    service = _get_service()
    response = service.start_call(
        to=payload.to,
        resident_name=payload.residentName,
        visitor_name=payload.visitorName,
        plate=payload.plate,
    )

    if response.success:
        return response

    status_code = status.HTTP_400_BAD_REQUEST
    if response.error and response.error.code in {"MISSING_ENV", "CALL_ERROR"}:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.api_route("/twilio/voice", methods=["GET", "POST"])
def twilio_voice(
    residentName: str | None = None,
    visitorName: str | None = None,
    plate: str | None = None,
):
    service = _get_service()
    twiml = service.build_voice_twiml(
        resident_name=residentName,
        visitor_name=visitorName,
        plate=plate,
    )
    return Response(content=twiml, media_type="text/xml")


@router.post("/twilio/voice/handle-input")
def twilio_handle_input(
    Digits: str | None = Form(default=None),
    residentName: str | None = None,
    visitorName: str | None = None,
    plate: str | None = None,
):
    service = _get_service()
    twiml = service.build_handle_input_twiml(
        digit=Digits,
        resident_name=residentName,
        visitor_name=visitorName,
        plate=plate,
    )
    return Response(content=twiml, media_type="text/xml")

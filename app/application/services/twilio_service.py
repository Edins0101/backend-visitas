import os
import logging
from dataclasses import dataclass
from urllib.parse import urlencode

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.domain.twilio import AccessDecisionNotifierPort, CallProviderPort, TwimlBuilderPort


logger = logging.getLogger(__name__)


@dataclass
class TwilioConfig:
    account_sid: str | None
    auth_token: str | None
    phone_number: str | None
    base_url: str | None


class TwilioService:
    def __init__(
        self,
        call_port: CallProviderPort,
        twiml_port: TwimlBuilderPort,
        notifier_port: AccessDecisionNotifierPort,
        config: TwilioConfig,
    ):
        self._call_port = call_port
        self._twiml_port = twiml_port
        self._notifier_port = notifier_port
        self._config = config

    @staticmethod
    def from_env(
        call_port: CallProviderPort,
        twiml_port: TwimlBuilderPort,
        notifier_port: AccessDecisionNotifierPort,
    ) -> "TwilioService":
        def _get_env(name: str) -> str | None:
            value = os.getenv(name)
            return value.strip() if value else None

        config = TwilioConfig(
            account_sid=_get_env("TWILIO_ACCOUNT_SID"),
            auth_token=_get_env("TWILIO_AUTH_TOKEN"),
            phone_number=_get_env("TWILIO_PHONE_NUMBER"),
            base_url=_get_env("BASE_URL"),
        )
        return TwilioService(
            call_port=call_port,
            twiml_port=twiml_port,
            notifier_port=notifier_port,
            config=config,
        )

    def start_call(
        self,
        to: str,
        resident_name: str | None,
        visitor_name: str | None,
        plate: str | None,
        visit_id: str,
    ) -> GeneralResponse[dict]:
        if not to:
            return GeneralResponse(
                success=False,
                message='Parametro "to" es requerido',
                error=ErrorDTO(code="MISSING_TO", message='Parametro "to" es requerido'),
            )

        missing = []
        if not self._config.account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not self._config.auth_token:
            missing.append("TWILIO_AUTH_TOKEN")
        if not self._config.phone_number:
            missing.append("TWILIO_PHONE_NUMBER")
        if not self._config.base_url:
            missing.append("BASE_URL")

        if missing:
            logger.warning("start_call_missing_env missing=%s", missing)
            return GeneralResponse(
                success=False,
                message="Faltan variables de entorno",
                error=ErrorDTO(code="MISSING_ENV", message="Faltan variables de entorno", details={"missing": missing}),
            )

        qs = urlencode(
            {
                "residentName": resident_name or "",
                "visitorName": visitor_name or "",
                "plate": plate or "",
                "visitId": visit_id,
            }
        )
        normalized_base_url = (self._config.base_url or "").rstrip("/")
        url = f"{normalized_base_url}/twilio/voice?{qs}"
        status_callback_qs = urlencode({"visitId": visit_id})
        status_callback_url = f"{normalized_base_url}/twilio/voice/status?{status_callback_qs}"

        try:
            logger.info(
                "start_call_provider_request to=%s from=%s url=%s status_callback=%s visit_id=%s",
                to,
                self._config.phone_number,
                url,
                status_callback_url,
                visit_id,
            )
            call_sid = self._call_port.create_call(
                to=to,
                from_number=self._config.phone_number,
                url=url,
                status_callback_url=status_callback_url,
            )
        except Exception as exc:
            logger.exception("start_call_provider_error to=%s", to)
            return GeneralResponse(
                success=False,
                message="Error creando llamada",
                error=ErrorDTO(code="CALL_ERROR", message="Error creando llamada", details={"error": str(exc)}),
            )

        logger.info("start_call_provider_response call_sid=%s", call_sid)

        return GeneralResponse(
            success=True,
            message="Llamada iniciada",
            data={"callSid": call_sid, "visitId": visit_id},
        )

    def build_voice_twiml(
        self,
        resident_name: str | None,
        visitor_name: str | None,
        plate: str | None,
        visit_id: str | None,
    ) -> str:
        return self._twiml_port.build_voice(
            resident_name or "",
            visitor_name or "",
            plate or "",
            visit_id or "",
            self._config.base_url,
        )

    def build_handle_input_twiml(
        self,
        digit: str | None,
        resident_name: str | None,
        visitor_name: str | None,
        plate: str | None,
        visit_id: str | None,
        call_sid: str | None,
    ) -> str:
        raw_digit = (digit or "").strip()
        extracted_digits = "".join(ch for ch in raw_digit if ch.isdigit())
        normalized_digit = extracted_digits[:1]
        normalized_resident = resident_name or ""
        normalized_visitor = visitor_name or ""
        normalized_plate = plate or ""
        normalized_visit_id = visit_id or ""

        logger.info(
            "handle_input_digit_resolved raw=%s normalized=%s resident=%s visitor=%s plate=%s visit_id=%s call_sid=%s",
            raw_digit,
            normalized_digit,
            normalized_resident,
            normalized_visitor,
            normalized_plate,
            normalized_visit_id,
            call_sid,
        )

        if normalized_digit == "1":
            self._notify_decision_safe(
                decision="authorized",
                resident_name=normalized_resident,
                visitor_name=normalized_visitor,
                plate=normalized_plate,
                digit=normalized_digit,
                visit_id=normalized_visit_id,
                call_sid=call_sid,
            )
        elif normalized_digit == "2":
            self._notify_decision_safe(
                decision="rejected",
                resident_name=normalized_resident,
                visitor_name=normalized_visitor,
                plate=normalized_plate,
                digit=normalized_digit,
                visit_id=normalized_visit_id,
                call_sid=call_sid,
            )
        else:
            logger.info("handle_input_no_decision normalized=%s", normalized_digit or "<empty>")

        return self._twiml_port.build_handle_input(
            normalized_digit,
            normalized_resident,
            normalized_visitor,
            normalized_plate,
            normalized_visit_id,
            self._config.base_url,
        )

    def _notify_decision_safe(
        self,
        decision: str,
        resident_name: str,
        visitor_name: str,
        plate: str,
        digit: str,
        visit_id: str,
        call_sid: str | None,
    ) -> None:
        try:
            logger.info(
                "notify_decision_request decision=%s resident=%s visitor=%s plate=%s digit=%s visit_id=%s call_sid=%s",
                decision,
                resident_name,
                visitor_name,
                plate,
                digit,
                visit_id,
                call_sid,
            )
            self._notifier_port.notify_decision(
                decision=decision,
                resident_name=resident_name,
                visitor_name=visitor_name,
                plate=plate,
                digit=digit,
                visit_id=visit_id,
                call_sid=call_sid,
            )
        except Exception as exc:
            # Twilio flow must continue even if backend notification fails.
            logger.exception("notify_decision_error decision=%s digit=%s error=%s", decision, digit, exc)

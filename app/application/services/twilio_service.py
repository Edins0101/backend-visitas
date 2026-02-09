import os
from dataclasses import dataclass
from urllib.parse import urlencode

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.domain.twilio import CallProviderPort, TwimlBuilderPort


@dataclass
class TwilioConfig:
    account_sid: str | None
    auth_token: str | None
    phone_number: str | None
    base_url: str | None


class TwilioService:
    def __init__(self, call_port: CallProviderPort, twiml_port: TwimlBuilderPort, config: TwilioConfig):
        self._call_port = call_port
        self._twiml_port = twiml_port
        self._config = config

    @staticmethod
    def from_env(call_port: CallProviderPort, twiml_port: TwimlBuilderPort) -> "TwilioService":
        def _get_env(name: str) -> str | None:
            value = os.getenv(name)
            return value.strip() if value else None

        config = TwilioConfig(
            account_sid=_get_env("TWILIO_ACCOUNT_SID"),
            auth_token=_get_env("TWILIO_AUTH_TOKEN"),
            phone_number=_get_env("TWILIO_PHONE_NUMBER"),
            base_url=_get_env("BASE_URL"),
        )
        return TwilioService(call_port=call_port, twiml_port=twiml_port, config=config)

    def start_call(
        self,
        to: str,
        resident_name: str | None,
        visitor_name: str | None,
        plate: str | None,
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
            }
        )
        url = f"{self._config.base_url}/twilio/voice?{qs}"

        try:
            call_sid = self._call_port.create_call(
                to=to,
                from_number=self._config.phone_number,
                url=url,
            )
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Error creando llamada",
                error=ErrorDTO(code="CALL_ERROR", message="Error creando llamada", details={"error": str(exc)}),
            )

        return GeneralResponse(
            success=True,
            message="Llamada iniciada",
            data={"callSid": call_sid},
        )

    def build_voice_twiml(
        self,
        resident_name: str | None,
        visitor_name: str | None,
        plate: str | None,
    ) -> str:
        return self._twiml_port.build_voice(
            resident_name or "",
            visitor_name or "",
            plate or "",
            self._config.base_url,
        )

    def build_handle_input_twiml(
        self,
        digit: str | None,
        resident_name: str | None,
        visitor_name: str | None,
        plate: str | None,
    ) -> str:
        return self._twiml_port.build_handle_input(
            digit or "",
            resident_name or "",
            visitor_name or "",
            plate or "",
            self._config.base_url,
        )

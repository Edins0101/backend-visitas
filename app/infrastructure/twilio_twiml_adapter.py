from urllib.parse import urlencode

from twilio.twiml.voice_response import VoiceResponse

from app.domain.twilio import TwimlBuilderPort


class TwilioTwimlAdapter(TwimlBuilderPort):
    def build_voice(
        self,
        resident_name: str,
        visitor_name: str,
        plate: str,
        visit_id: str,
        base_url: str | None,
    ) -> str:
        twiml = VoiceResponse()

        name = resident_name or ""
        visitor = visitor_name or "no identificado"
        plate_info = f"con placa {plate} " if plate else ""

        info_message = (
            f"Hola. Se solicita autorizacion de ingreso para el visitante {visitor} "
            f"{plate_info}. "
            f"Estimado residente {name}, "
            "si desea autorizar el ingreso, presione 1. "
            "Si desea rechazar el ingreso, presione 2. "
            "Si desea escuchar nuevamente la informacion, presione 3."
        )

        qs = urlencode(
            {
                "residentName": name,
                "visitorName": visitor_name or "",
                "plate": plate or "",
                "visitId": visit_id,
            }
        )
        action_url = self._join_url(base_url, "/twilio/voice/handle-input", qs)

        gather = twiml.gather(
            input="dtmf",
            num_digits=1,
            timeout=8,
            action=action_url,
            method="POST",
        )
        gather.say(info_message, voice="alice", language="es-ES")
        twiml.say(
            "No se recibio ninguna opcion. Finalizando la llamada.",
            voice="alice",
            language="es-ES",
        )
        twiml.hangup()

        return str(twiml)

    def build_handle_input(
        self,
        digit: str,
        resident_name: str,
        visitor_name: str,
        plate: str,
        visit_id: str,
        base_url: str | None,
    ) -> str:
        twiml = VoiceResponse()

        qs = urlencode(
            {
                "residentName": resident_name or "",
                "visitorName": visitor_name or "",
                "plate": plate or "",
                "visitId": visit_id,
            }
        )
        redirect_url = self._join_url(base_url, "/twilio/voice", qs)

        if digit == "1":
            twiml.say(
                "Has autorizado el ingreso del visitante. Muchas gracias.",
                voice="alice",
                language="es-ES",
            )
            twiml.hangup()
        elif digit == "2":
            twiml.say(
                "Has rechazado el ingreso del visitante. Muchas gracias.",
                voice="alice",
                language="es-ES",
            )
            twiml.hangup()
        elif digit == "3":
            twiml.say(
                "Reproduciendo nuevamente la informacion.",
                voice="alice",
                language="es-ES",
            )
            twiml.redirect(redirect_url)
        else:
            twiml.say(
                "Opcion no valida. Finalizando la llamada.",
                voice="alice",
                language="es-ES",
            )
            twiml.hangup()

        return str(twiml)

    @staticmethod
    def _join_url(base_url: str | None, path: str, qs: str) -> str:
        if base_url:
            normalized_base_url = base_url.rstrip("/")
            return f"{normalized_base_url}{path}?{qs}" if qs else f"{normalized_base_url}{path}"
        return f"{path}?{qs}" if qs else path

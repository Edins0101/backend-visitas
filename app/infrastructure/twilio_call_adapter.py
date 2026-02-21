from twilio.rest import Client

from app.domain.twilio import CallProviderPort


class TwilioCallAdapter(CallProviderPort):
    def __init__(self, account_sid: str, auth_token: str):
        self._client = Client(account_sid, auth_token)

    def create_call(
        self,
        to: str,
        from_number: str,
        url: str,
        status_callback_url: str | None = None,
    ) -> str:
        payload = {
            "to": to,
            "from_": from_number,
            "url": url,
        }
        if status_callback_url:
            payload["status_callback"] = status_callback_url
            payload["status_callback_method"] = "POST"
            payload["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]

        call = self._client.calls.create(**payload)
        return call.sid

from twilio.rest import Client

from app.domain.twilio import CallProviderPort


class TwilioCallAdapter(CallProviderPort):
    def __init__(self, account_sid: str, auth_token: str):
        self._client = Client(account_sid, auth_token)

    def create_call(self, to: str, from_number: str, url: str) -> str:
        call = self._client.calls.create(to=to, from_=from_number, url=url)
        return call.sid

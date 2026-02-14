import httpx

from app.domain.twilio import AccessDecisionNotifierPort


class WebhookAccessDecisionNotifierAdapter(AccessDecisionNotifierPort):
    def __init__(self, webhook_url: str | None, timeout_seconds: float = 5.0):
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    def notify_decision(
        self,
        decision: str,
        resident_name: str,
        visitor_name: str,
        plate: str,
        digit: str,
    ) -> None:
        if not self._webhook_url:
            return

        payload = {
            "decision": decision,
            "residentName": resident_name,
            "visitorName": visitor_name,
            "plate": plate,
            "digit": digit,
        }

        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(self._webhook_url, json=payload)
            response.raise_for_status()

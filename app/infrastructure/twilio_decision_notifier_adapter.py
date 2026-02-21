import httpx
import logging

from app.domain.twilio import AccessDecisionNotifierPort


logger = logging.getLogger(__name__)


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
        visit_id: str,
        call_sid: str | None,
    ) -> None:
        if not self._webhook_url:
            logger.warning("decision_webhook_skipped reason=missing_webhook_url")
            return

        payload = {
            "decision": decision,
            "residentName": resident_name,
            "visitorName": visitor_name,
            "plate": plate,
            "digit": digit,
            "visitId": visit_id,
            "callSid": call_sid,
        }

        logger.info("decision_webhook_request url=%s payload=%s", self._webhook_url, payload)
        with httpx.Client(timeout=self._timeout_seconds) as client:
            response = client.post(self._webhook_url, json=payload)
            response.raise_for_status()
            logger.info("decision_webhook_response status=%s", response.status_code)

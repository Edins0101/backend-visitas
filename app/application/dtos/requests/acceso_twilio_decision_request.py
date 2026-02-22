from pydantic import BaseModel


class AccesoTwilioDecisionRequestDTO(BaseModel):
    decision: str
    visitId: str
    digit: str | None = None
    callSid: str | None = None
    residentName: str | None = None
    visitorName: str | None = None

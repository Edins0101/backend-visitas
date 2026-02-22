from pydantic import BaseModel


class TwilioCallRequestDTO(BaseModel):
    to: str
    residentName: str | None = None
    visitorName: str | None = None

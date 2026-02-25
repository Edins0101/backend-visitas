from pydantic import BaseModel


class AccesoStartCallRequestDTO(BaseModel):
    visitorName: str | None = None

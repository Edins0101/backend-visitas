from pydantic import BaseModel


class AccesoCreateRequestDTO(BaseModel):
    viviendaVisitaFk: int
    motivo: str
    visitorName: str | None = None

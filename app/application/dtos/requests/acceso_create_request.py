from pydantic import BaseModel


class AccesoCreateRequestDTO(BaseModel):
    viviendaVisitaFk: int
    motivo: str
    visitorName: str | None = None
    fotoRostroVivoBase64: str | None = None

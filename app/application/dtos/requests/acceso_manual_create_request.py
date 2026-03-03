from pydantic import BaseModel


class AccesoManualCreateRequestDTO(BaseModel):
    viviendaVisitaFk: int
    motivo: str
    detalle: str | None = None
    personaGuardiaFk: int | None = None
    personaResidenteAutorizaFk: int | None = None
    placa: str | None = None
    usuarioCreado: str | None = None

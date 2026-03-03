from pydantic import BaseModel


class AccesoUpdatePlacaRequestDTO(BaseModel):
    placa: str
    usuarioActualizado: str | None = None

# app/domain/qr.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class QR:
    qr_pk: int
    hora_inicio_vigencia: datetime
    hora_fin_vigencia: datetime
    hora_usado: Optional[datetime]
    estado: str
    eliminado: bool

    def es_vigente(self, ahora: datetime) -> bool:
        return (
            not self.eliminado
            and self.estado == "vigente"
            and self.hora_usado is None
            and self.hora_inicio_vigencia <= ahora <= self.hora_fin_vigencia
        )

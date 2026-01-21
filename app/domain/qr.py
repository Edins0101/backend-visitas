# app/domain/qr.py
from dataclasses import dataclass
from datetime import datetime, timezone
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
        inicio, fin, ahora = _normalize_for_compare(
            self.hora_inicio_vigencia,
            self.hora_fin_vigencia,
            ahora,
        )
        return (
            not self.eliminado
            and self.estado == "vigente"
            and self.hora_usado is None
            and inicio <= ahora <= fin
        )


def _normalize_for_compare(*values: datetime) -> list[datetime]:
    any_naive = any(v.tzinfo is None or v.tzinfo.utcoffset(v) is None for v in values)
    if any_naive:
        normalized = []
        for v in values:
            if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
                normalized.append(v)
            else:
                normalized.append(v.astimezone(timezone.utc).replace(tzinfo=None))
        return normalized
    return [v.astimezone(timezone.utc) for v in values]

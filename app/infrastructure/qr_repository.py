from sqlalchemy import text
from datetime import datetime
from app.domain.qr import QR

class QRRepository:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, qr_id: int) -> QR | None:
        row = self.db.execute(text("""
            SELECT qr_pk, hora_inicio_vigencia, hora_fin_vigencia, hora_usado, estado, eliminado
            FROM qr
            WHERE qr_pk = :id
        """), {"id": qr_id}).mappings().one_or_none()

        return QR(**row) if row else None

    def mark_used(self, qr_id: int, when: datetime, usuario: str) -> None:
        self.db.execute(text("""
            UPDATE qr
            SET hora_usado = :when,
                estado = 'usado',
                fecha_actualizado = NOW(),
                usuario_actualizado = :usr
            WHERE qr_pk = :id AND eliminado = FALSE
        """), {"when": when, "usr": usuario, "id": qr_id})

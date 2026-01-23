from sqlalchemy import text


class ViviendaRepository:
    def __init__(self, db):
        self.db = db

    def get_villas_por_manzana(self) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT manzana, villa
                FROM vivienda
                WHERE eliminado = FALSE
                ORDER BY manzana, villa
                """
            )
        ).mappings().all()

        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["manzana"], []).append(row["villa"])

        return [
            {"manzana": manzana, "villas": villas}
            for manzana, villas in grouped.items()
        ]

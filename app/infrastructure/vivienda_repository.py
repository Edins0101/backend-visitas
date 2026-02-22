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

    def get_residente_contacto_por_manzana_villa(self, manzana: str, villa: str) -> dict | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    v.vivienda_pk,
                    p.celular
                FROM vivienda v
                INNER JOIN residente_vivienda rv
                    ON rv.vivienda_reside_fk = v.vivienda_pk
                INNER JOIN persona p
                    ON p.persona_pk = rv.persona_residente_fk
                WHERE v.eliminado = FALSE
                  AND rv.eliminado = FALSE
                  AND p.eliminado = FALSE
                  AND LOWER(TRIM(v.manzana)) = LOWER(TRIM(:manzana))
                  AND LOWER(TRIM(v.villa)) = LOWER(TRIM(:villa))
                ORDER BY
                    CASE
                        WHEN LOWER(COALESCE(rv.estado, '')) IN ('activo', 'activa', 'vigente') THEN 0
                        ELSE 1
                    END,
                    rv.fecha_hasta NULLS FIRST,
                    rv.fecha_desde DESC NULLS LAST,
                    rv.fecha_actualizado DESC NULLS LAST,
                    rv.residente_vivienda_pk DESC
                LIMIT 1
                """
            ),
            {"manzana": manzana, "villa": villa},
        ).mappings().first()

        if not row:
            return None

        return {
            "vivienda_pk": row["vivienda_pk"],
            "celular": row["celular"],
        }

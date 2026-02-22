from __future__ import annotations

from sqlalchemy import text


class AccesoRepository:
    def __init__(self, db):
        self.db = db

    def supports_resultado_pendiente(self) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_constraint c
                    JOIN pg_class t ON t.oid = c.conrelid
                    WHERE t.relname = 'acceso'
                      AND c.contype = 'c'
                      AND pg_get_constraintdef(c.oid) ILIKE '%pendiente%'
                ) AS supports_pending
                """
            )
        ).mappings().one()
        return bool(row["supports_pending"])

    def get_residente_por_manzana_villa(self, manzana: str, villa: str) -> dict | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    v.vivienda_pk,
                    p.persona_pk AS persona_residente_pk,
                    p.nombres,
                    p.apellidos,
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

        return dict(row) if row else None

    def get_residente_por_vivienda_pk(self, vivienda_pk: int) -> dict | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    v.vivienda_pk,
                    p.persona_pk AS persona_residente_pk,
                    p.nombres,
                    p.apellidos,
                    p.celular
                FROM vivienda v
                INNER JOIN residente_vivienda rv
                    ON rv.vivienda_reside_fk = v.vivienda_pk
                INNER JOIN persona p
                    ON p.persona_pk = rv.persona_residente_fk
                WHERE v.eliminado = FALSE
                  AND rv.eliminado = FALSE
                  AND p.eliminado = FALSE
                  AND v.vivienda_pk = :vivienda_pk
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
            {"vivienda_pk": vivienda_pk},
        ).mappings().first()

        return dict(row) if row else None

    def create_acceso(
        self,
        *,
        tipo: str,
        vivienda_visita_fk: int,
        resultado: str,
        motivo: str | None,
        persona_guardia_fk: int | None,
        persona_residente_autoriza_fk: int | None,
        visita_ingreso_fk: int | None,
        vehiculo_ingreso_fk: int | None,
        placa_detectada: str | None,
        biometria_ok: bool | None,
        placa_ok: bool | None,
        observacion: str | None,
        usuario_creado: str,
    ) -> dict:
        row = self.db.execute(
            text(
                """
                INSERT INTO acceso (
                    tipo,
                    vivienda_visita_fk,
                    resultado,
                    motivo,
                    persona_guardia_fk,
                    persona_residente_autoriza_fk,
                    visita_ingreso_fk,
                    vehiculo_ingreso_fk,
                    placa_detectada,
                    biometria_ok,
                    placa_ok,
                    intentos,
                    observacion,
                    eliminado,
                    usuario_creado
                )
                VALUES (
                    :tipo,
                    :vivienda_visita_fk,
                    :resultado,
                    :motivo,
                    :persona_guardia_fk,
                    :persona_residente_autoriza_fk,
                    :visita_ingreso_fk,
                    :vehiculo_ingreso_fk,
                    :placa_detectada,
                    :biometria_ok,
                    :placa_ok,
                    0,
                    :observacion,
                    FALSE,
                    :usuario_creado
                )
                RETURNING
                    acceso_pk,
                    tipo,
                    vivienda_visita_fk,
                    resultado,
                    motivo,
                    persona_guardia_fk,
                    persona_residente_autoriza_fk,
                    visita_ingreso_fk,
                    vehiculo_ingreso_fk,
                    placa_detectada,
                    biometria_ok,
                    placa_ok,
                    intentos,
                    observacion,
                    eliminado,
                    fecha_creado,
                    usuario_creado,
                    fecha_actualizado,
                    usuario_actualizado
                """
            ),
            {
                "tipo": tipo,
                "vivienda_visita_fk": vivienda_visita_fk,
                "resultado": resultado,
                "motivo": motivo,
                "persona_guardia_fk": persona_guardia_fk,
                "persona_residente_autoriza_fk": persona_residente_autoriza_fk,
                "visita_ingreso_fk": visita_ingreso_fk,
                "vehiculo_ingreso_fk": vehiculo_ingreso_fk,
                "placa_detectada": placa_detectada,
                "biometria_ok": biometria_ok,
                "placa_ok": placa_ok,
                "observacion": observacion,
                "usuario_creado": usuario_creado,
            },
        ).mappings().one()

        return dict(row)

    def get_by_id(self, acceso_pk: int) -> dict | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    acceso_pk,
                    tipo,
                    vivienda_visita_fk,
                    resultado,
                    motivo,
                    persona_guardia_fk,
                    persona_residente_autoriza_fk,
                    visita_ingreso_fk,
                    vehiculo_ingreso_fk,
                    placa_detectada,
                    biometria_ok,
                    placa_ok,
                    intentos,
                    observacion,
                    eliminado,
                    fecha_creado,
                    usuario_creado,
                    fecha_actualizado,
                    usuario_actualizado
                FROM acceso
                WHERE acceso_pk = :acceso_pk
                  AND eliminado = FALSE
                """
            ),
            {"acceso_pk": acceso_pk},
        ).mappings().first()

        return dict(row) if row else None

    def update_resultado(
        self,
        *,
        acceso_pk: int,
        resultado: str,
        usuario_actualizado: str,
        observacion: str | None,
    ) -> dict | None:
        row = self.db.execute(
            text(
                """
                UPDATE acceso
                SET resultado = :resultado,
                    observacion = :observacion,
                    fecha_actualizado = NOW(),
                    usuario_actualizado = :usuario_actualizado
                WHERE acceso_pk = :acceso_pk
                  AND eliminado = FALSE
                RETURNING
                    acceso_pk,
                    tipo,
                    vivienda_visita_fk,
                    resultado,
                    motivo,
                    persona_guardia_fk,
                    persona_residente_autoriza_fk,
                    visita_ingreso_fk,
                    vehiculo_ingreso_fk,
                    placa_detectada,
                    biometria_ok,
                    placa_ok,
                    intentos,
                    observacion,
                    eliminado,
                    fecha_creado,
                    usuario_creado,
                    fecha_actualizado,
                    usuario_actualizado
                """
            ),
            {
                "acceso_pk": acceso_pk,
                "resultado": resultado,
                "observacion": observacion,
                "usuario_actualizado": usuario_actualizado,
            },
        ).mappings().first()

        return dict(row) if row else None

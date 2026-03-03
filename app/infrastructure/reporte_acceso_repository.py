from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import text


_BASE_FROM_SQL = """
FROM acceso a
LEFT JOIN vivienda v
    ON v.vivienda_pk = a.vivienda_visita_fk
LEFT JOIN visita vi
    ON vi.visita_pk = a.visita_ingreso_fk
LEFT JOIN persona pr
    ON pr.persona_pk = a.persona_residente_autoriza_fk
LEFT JOIN persona pg
    ON pg.persona_pk = a.persona_guardia_fk
LEFT JOIN vehiculo vh
    ON vh.vehiculo_pk = a.vehiculo_ingreso_fk
LEFT JOIN LATERAL (
    SELECT
        at.autorizacion_tel_pk,
        at.telefono,
        at.respuesta,
        at.numero_intentos,
        at.hora_inicio,
        at.hora_fin,
        at.fecha_creado
    FROM autorizacion_telefonica at
    WHERE at.acceso_ingreso_fk = a.acceso_pk
      AND at.eliminado = FALSE
    ORDER BY at.fecha_creado DESC, at.autorizacion_tel_pk DESC
    LIMIT 1
) atel ON TRUE
"""

_RESULTADO_NORMALIZADO_SQL = """
CASE
    WHEN LOWER(COALESCE(a.resultado, '')) = 'no_autorizado' THEN 'rechazado'
    ELSE LOWER(COALESCE(a.resultado, ''))
END
"""


class ReporteAccesoRepository:
    def __init__(self, db):
        self.db = db

    def listar_accesos(
        self,
        *,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        tipo: str | None,
        resultado: str | None,
        vivienda_pk: int | None,
        manzana: str | None,
        villa: str | None,
        visitante_identificacion: str | None,
        visitante_nombre: str | None,
        placa: str | None,
        respuesta_llamada: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        where_sql, params = self._build_where_clause(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            tipo=tipo,
            resultado=resultado,
            vivienda_pk=vivienda_pk,
            manzana=manzana,
            villa=villa,
            visitante_identificacion=visitante_identificacion,
            visitante_nombre=visitante_nombre,
            placa=placa,
            respuesta_llamada=respuesta_llamada,
        )

        total = int(
            self.db.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS total
                    {_BASE_FROM_SQL}
                    WHERE {where_sql}
                    """
                ),
                params,
            ).scalar_one()
        )

        query_params = {
            **params,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        rows = self.db.execute(
            text(
                f"""
                SELECT
                    a.acceso_pk AS "accesoPk",
                    COALESCE(
                        NULLIF(TRIM(CONCAT(COALESCE(vi.nombres, ''), ' ', COALESCE(vi.apellidos, ''))), ''),
                        NULLIF(TRIM(CONCAT(COALESCE(pr.nombres, ''), ' ', COALESCE(pr.apellidos, ''))), ''),
                        NULLIF(TRIM(CONCAT(COALESCE(pg.nombres, ''), ' ', COALESCE(pg.apellidos, ''))), ''),
                        'No identificado'
                    ) AS "personaIngreso",
                    a.tipo AS "tipoAcceso",
                    {_RESULTADO_NORMALIZADO_SQL} AS "resultado",
                    TRIM(CONCAT(COALESCE(v.manzana, ''), ' ', COALESCE(v.villa, ''))) AS "residencia"
                {_BASE_FROM_SQL}
                WHERE {where_sql}
                ORDER BY a.fecha_creado DESC, a.acceso_pk DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            query_params,
        ).mappings().all()

        return {
            "total": total,
            "items": [dict(row) for row in rows],
        }

    def obtener_resumen_accesos(
        self,
        *,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        tipo: str | None,
        resultado: str | None,
        vivienda_pk: int | None,
        manzana: str | None,
        villa: str | None,
        visitante_identificacion: str | None,
        visitante_nombre: str | None,
        placa: str | None,
        respuesta_llamada: str | None,
    ) -> dict:
        where_sql, params = self._build_where_clause(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            tipo=tipo,
            resultado=resultado,
            vivienda_pk=vivienda_pk,
            manzana=manzana,
            villa=villa,
            visitante_identificacion=visitante_identificacion,
            visitante_nombre=visitante_nombre,
            placa=placa,
            respuesta_llamada=respuesta_llamada,
        )

        totals_row = self.db.execute(
            text(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE {_RESULTADO_NORMALIZADO_SQL} = 'autorizado') AS autorizados,
                    COUNT(*) FILTER (WHERE {_RESULTADO_NORMALIZADO_SQL} = 'rechazado') AS rechazados,
                    COUNT(*) FILTER (WHERE {_RESULTADO_NORMALIZADO_SQL} = 'pendiente') AS pendientes,
                    COUNT(*) FILTER (WHERE atel.autorizacion_tel_pk IS NOT NULL) AS con_llamada
                {_BASE_FROM_SQL}
                WHERE {where_sql}
                """
            ),
            params,
        ).mappings().one()

        resultado_rows = self.db.execute(
            text(
                f"""
                SELECT
                    COALESCE(NULLIF({_RESULTADO_NORMALIZADO_SQL}, ''), 'sin_resultado') AS "resultado",
                    COUNT(*) AS "total"
                {_BASE_FROM_SQL}
                WHERE {where_sql}
                GROUP BY 1
                ORDER BY COUNT(*) DESC, 1 ASC
                """
            ),
            params,
        ).mappings().all()

        tipo_rows = self.db.execute(
            text(
                f"""
                SELECT
                    COALESCE(NULLIF(TRIM(a.tipo), ''), 'sin_tipo') AS "tipo",
                    COUNT(*) AS "total"
                {_BASE_FROM_SQL}
                WHERE {where_sql}
                GROUP BY 1
                ORDER BY COUNT(*) DESC, 1 ASC
                """
            ),
            params,
        ).mappings().all()

        dia_rows = self.db.execute(
            text(
                f"""
                SELECT
                    CAST(a.fecha_creado AS DATE) AS "fecha",
                    COUNT(*) AS "total"
                {_BASE_FROM_SQL}
                WHERE {where_sql}
                GROUP BY CAST(a.fecha_creado AS DATE)
                ORDER BY "fecha" DESC
                LIMIT 31
                """
            ),
            params,
        ).mappings().all()

        total = int(totals_row["total"] or 0)
        con_llamada = int(totals_row["con_llamada"] or 0)
        return {
            "totales": {
                "accesos": total,
                "autorizados": int(totals_row["autorizados"] or 0),
                "rechazados": int(totals_row["rechazados"] or 0),
                "pendientes": int(totals_row["pendientes"] or 0),
                "conLlamada": con_llamada,
                "sinLlamada": max(total - con_llamada, 0),
            },
            "porResultado": [dict(row) for row in resultado_rows],
            "porTipo": [dict(row) for row in tipo_rows],
            "porDia": [dict(row) for row in dia_rows],
        }

    def obtener_acceso_detalle(self, acceso_pk: int) -> dict | None:
        row = self.db.execute(
            text(
                f"""
                SELECT
                    a.acceso_pk AS "accesoPk",
                    a.tipo AS "tipoAcceso",
                    {_RESULTADO_NORMALIZADO_SQL} AS "resultado",
                    a.motivo AS "motivo",
                    COALESCE(
                        NULLIF(TRIM(CONCAT(COALESCE(vi.nombres, ''), ' ', COALESCE(vi.apellidos, ''))), ''),
                        NULLIF(TRIM(CONCAT(COALESCE(pr.nombres, ''), ' ', COALESCE(pr.apellidos, ''))), ''),
                        NULLIF(TRIM(CONCAT(COALESCE(pg.nombres, ''), ' ', COALESCE(pg.apellidos, ''))), ''),
                        'No identificado'
                    ) AS "personaIngreso",
                    v.manzana AS "manzana",
                    v.villa AS "villa",
                    v.estado AS "estadoVivienda",
                    pg.identificacion AS "guardiaIdentificacion",
                    TRIM(CONCAT(COALESCE(pg.nombres, ''), ' ', COALESCE(pg.apellidos, ''))) AS "guardiaNombreCompleto",
                    pg.celular AS "guardiaCelular",
                    pr.identificacion AS "residenteIdentificacion",
                    TRIM(CONCAT(COALESCE(pr.nombres, ''), ' ', COALESCE(pr.apellidos, ''))) AS "residenteNombreCompleto",
                    pr.celular AS "residenteCelular",
                    vi.identificacion AS "visitanteIdentificacion",
                    TRIM(CONCAT(COALESCE(vi.nombres, ''), ' ', COALESCE(vi.apellidos, ''))) AS "visitanteNombreCompleto",
                    vh.placa AS "vehiculoPlaca",
                    vh.estado AS "vehiculoEstado",
                    a.placa_detectada AS "placaDetectada",
                    a.biometria_ok AS "biometriaOk",
                    a.placa_ok AS "placaOk",
                    a.observacion AS "observacion",
                    atel.telefono AS "telefonoAutorizacion",
                    atel.respuesta AS "respuestaAutorizacion",
                    atel.numero_intentos AS "numeroIntentosAutorizacion",
                    atel.hora_inicio AS "horaInicioAutorizacion",
                    atel.hora_fin AS "horaFinAutorizacion",
                    atel.fecha_creado AS "fechaCreadoAutorizacion",
                    a.fecha_creado AS "fechaCreado",
                    a.fecha_actualizado AS "fechaActualizado",
                    a.usuario_actualizado AS "usuarioActualizado"
                {_BASE_FROM_SQL}
                WHERE a.eliminado = FALSE
                  AND a.acceso_pk = :acceso_pk
                LIMIT 1
                """
            ),
            {"acceso_pk": acceso_pk},
        ).mappings().first()

        return dict(row) if row else None

    @staticmethod
    def _build_where_clause(
        *,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        tipo: str | None,
        resultado: str | None,
        vivienda_pk: int | None,
        manzana: str | None,
        villa: str | None,
        visitante_identificacion: str | None,
        visitante_nombre: str | None,
        placa: str | None,
        respuesta_llamada: str | None,
    ) -> tuple[str, dict]:
        clauses = ["a.eliminado = FALSE"]
        params: dict[str, object] = {}

        if fecha_desde is not None:
            params["fecha_desde"] = datetime.combine(fecha_desde, time.min)
            clauses.append("a.fecha_creado >= :fecha_desde")

        if fecha_hasta is not None:
            fecha_hasta_exclusive = datetime.combine(fecha_hasta + timedelta(days=1), time.min)
            params["fecha_hasta_exclusive"] = fecha_hasta_exclusive
            clauses.append("a.fecha_creado < :fecha_hasta_exclusive")

        if tipo:
            params["tipo"] = tipo.strip().lower()
            clauses.append("LOWER(COALESCE(a.tipo, '')) = :tipo")

        if resultado:
            normalized_resultado = resultado.strip().lower()
            if normalized_resultado == "no_autorizado":
                normalized_resultado = "rechazado"
            params["resultado"] = normalized_resultado
            clauses.append(f"{_RESULTADO_NORMALIZADO_SQL} = :resultado")

        if vivienda_pk is not None:
            params["vivienda_pk"] = int(vivienda_pk)
            clauses.append("a.vivienda_visita_fk = :vivienda_pk")

        if manzana:
            params["manzana"] = f"%{manzana.strip().lower()}%"
            clauses.append("LOWER(COALESCE(v.manzana, '')) LIKE :manzana")

        if villa:
            params["villa"] = f"%{villa.strip().lower()}%"
            clauses.append("LOWER(COALESCE(v.villa, '')) LIKE :villa")

        if visitante_identificacion:
            params["visitante_identificacion"] = f"%{visitante_identificacion.strip().lower()}%"
            clauses.append("LOWER(COALESCE(vi.identificacion, '')) LIKE :visitante_identificacion")

        if visitante_nombre:
            normalized_name = " ".join(visitante_nombre.strip().lower().split())
            params["visitante_nombre"] = f"%{normalized_name}%"
            clauses.append(
                "LOWER(TRIM(CONCAT(COALESCE(vi.nombres, ''), ' ', COALESCE(vi.apellidos, '')))) LIKE :visitante_nombre"
            )

        if placa:
            normalized_plate = placa.strip().lower()
            params["placa"] = f"%{normalized_plate}%"
            clauses.append(
                "(LOWER(COALESCE(a.placa_detectada, '')) LIKE :placa OR LOWER(COALESCE(vh.placa, '')) LIKE :placa)"
            )

        if respuesta_llamada:
            params["respuesta_llamada"] = respuesta_llamada.strip().lower()
            clauses.append("LOWER(COALESCE(atel.respuesta, '')) = :respuesta_llamada")

        return " AND ".join(clauses), params

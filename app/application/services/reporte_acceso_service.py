from __future__ import annotations

import base64
import mimetypes
from datetime import date
from pathlib import Path

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.infrastructure.reporte_acceso_repository import ReporteAccesoRepository


class ReporteAccesoService:
    def __init__(self, repo: ReporteAccesoRepository):
        self.repo = repo

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
    ) -> GeneralResponse[dict]:
        invalid_range = self._validate_date_range(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
        if invalid_range:
            return invalid_range

        query_data = self.repo.listar_accesos(
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
            page=page,
            page_size=page_size,
        )

        total = int(query_data["total"])
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return GeneralResponse(
            success=True,
            message="Reporte de accesos generado",
            data={
                "items": query_data["items"],
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                    "totalPages": total_pages,
                }
            },
        )

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
    ) -> GeneralResponse[dict]:
        invalid_range = self._validate_date_range(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
        if invalid_range:
            return invalid_range

        summary = self.repo.obtener_resumen_accesos(
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

        summary["filters"] = self._build_filters_data(
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

        return GeneralResponse(
            success=True,
            message="Resumen de accesos generado",
            data=summary,
        )

    def obtener_detalle_acceso(self, acceso_pk: int) -> GeneralResponse[dict]:
        row = self.repo.obtener_acceso_detalle(acceso_pk=acceso_pk)
        if not row:
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(
                    code="NOT_FOUND",
                    message="Acceso no existe",
                    details={"accesoPk": acceso_pk},
                ),
            )

        observacion_data = self._parse_observacion(row.get("observacion"))
        imagen_path = observacion_data.get("faceCompareImage") or observacion_data.get("evidencia")
        imagen_data = self._build_image_data(imagen_path)
        residencia_desc = " ".join(
            part for part in [self._null_if_blank(row.get("manzana")), self._null_if_blank(row.get("villa"))] if part
        ).strip()
        residencia = self._section(
            {
                "descripcion": residencia_desc or None,
                "manzana": self._null_if_blank(row.get("manzana")),
                "villa": self._null_if_blank(row.get("villa")),
                "estado": self._null_if_blank(row.get("estadoVivienda")),
            }
        )
        llamada = self._section(
            {
                "decision": self._normalize_decision(observacion_data.get("decision_twilio")),
                "digit": self._null_if_blank(observacion_data.get("digit")),
                "callSid": self._null_if_blank(observacion_data.get("callSid")),
                "telefono": self._null_if_blank(row.get("telefonoAutorizacion")),
                "respuesta": self._null_if_blank(row.get("respuestaAutorizacion")),
                "numeroIntentos": row.get("numeroIntentosAutorizacion"),
                "horaInicio": row.get("horaInicioAutorizacion"),
                "horaFin": row.get("horaFinAutorizacion"),
                "fecha": row.get("fechaCreadoAutorizacion"),
            }
        )
        validaciones = self._section(
            {
                "biometriaOk": row.get("biometriaOk"),
                "placaOk": row.get("placaOk"),
                "placaDetectada": self._null_if_blank(row.get("placaDetectada")),
            }
        )
        data = {
            "accesoPk": row["accesoPk"],
            "personaIngreso": self._null_if_blank(row.get("personaIngreso")) or "No identificado",
            "tipoAcceso": self._null_if_blank(row.get("tipoAcceso")),
            "resultado": self._null_if_blank(row.get("resultado")),
            "motivo": self._null_if_blank(row.get("motivo")),
            "placa": self._null_if_blank(row.get("placaDetectada")) or self._null_if_blank(row.get("vehiculoPlaca")),
            "imagen": imagen_data,
            "residencia": residencia,
            "residenteAutoriza": self._section(
                {
                    "identificacion": self._null_if_blank(row.get("residenteIdentificacion")),
                    "nombreCompleto": self._null_if_blank(row.get("residenteNombreCompleto")),
                    "celular": self._null_if_blank(row.get("residenteCelular")),
                }
            ),
            "visitante": self._section(
                {
                    "identificacion": self._null_if_blank(row.get("visitanteIdentificacion")),
                    "nombreCompleto": self._null_if_blank(row.get("visitanteNombreCompleto")),
                }
            ),
            "guardia": self._section(
                {
                    "identificacion": self._null_if_blank(row.get("guardiaIdentificacion")),
                    "nombreCompleto": self._null_if_blank(row.get("guardiaNombreCompleto")),
                    "celular": self._null_if_blank(row.get("guardiaCelular")),
                }
            ),
            "vehiculo": self._section(
                {
                    "placa": self._null_if_blank(row.get("vehiculoPlaca")),
                    "estado": self._null_if_blank(row.get("vehiculoEstado")),
                }
            ),
            "validaciones": validaciones,
            "llamadaAutorizacion": llamada,
            "fechas": self._section(
                {
                    "creado": row.get("fechaCreado"),
                    "actualizado": row.get("fechaActualizado"),
                    "usuarioActualizado": self._null_if_blank(row.get("usuarioActualizado")),
                }
            ),
        }
        data = {key: value for key, value in data.items() if value is not None or key in {"placa", "imagen"}}

        return GeneralResponse(
            success=True,
            message="Detalle de acceso obtenido",
            data=data,
        )

    @staticmethod
    def _validate_date_range(
        *,
        fecha_desde: date | None,
        fecha_hasta: date | None,
    ) -> GeneralResponse[dict] | None:
        if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
            return GeneralResponse(
                success=False,
                message="Rango de fechas invalido",
                error=ErrorDTO(
                    code="INVALID_DATE_RANGE",
                    message="Rango de fechas invalido",
                    details={"fechaDesde": str(fecha_desde), "fechaHasta": str(fecha_hasta)},
                ),
            )
        return None

    @staticmethod
    def _build_filters_data(
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
        return {
            "fechaDesde": str(fecha_desde) if fecha_desde else None,
            "fechaHasta": str(fecha_hasta) if fecha_hasta else None,
            "tipo": tipo,
            "resultado": resultado,
            "viviendaPk": vivienda_pk,
            "manzana": manzana,
            "villa": villa,
            "visitanteIdentificacion": visitante_identificacion,
            "visitanteNombre": visitante_nombre,
            "placa": placa,
            "respuestaLlamada": respuesta_llamada,
        }

    @staticmethod
    def _null_if_blank(value):
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @staticmethod
    def _section(data: dict) -> dict | None:
        cleaned: dict = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, str):
                normalized = value.strip()
                if not normalized:
                    continue
                cleaned[key] = normalized
                continue
            cleaned[key] = value
        return cleaned or None

    @staticmethod
    def _normalize_decision(value: str | None) -> str | None:
        normalized = (value or "").strip().lower()
        if normalized == "authorized":
            return "autorizado"
        if normalized == "rejected":
            return "rechazado"
        return None

    @staticmethod
    def _parse_observacion(observacion: str | None) -> dict[str, str]:
        if not observacion:
            return {}
        parts = [part.strip() for part in str(observacion).split("|") if part.strip()]
        data: dict[str, str] = {}
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                data[key] = value
        return data

    @staticmethod
    def _build_image_data(evidencia_path: str | None) -> dict | None:
        normalized = (evidencia_path or "").strip()
        if not normalized:
            return None

        path = Path(normalized)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists() or not path.is_file():
            return {"path": normalized, "available": False}

        try:
            raw = path.read_bytes()
        except Exception:
            return {"path": normalized, "available": False}

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(raw).decode("ascii")
        return {
            "path": normalized,
            "available": True,
            "contentType": content_type,
            "base64": encoded,
        }

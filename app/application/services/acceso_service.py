from __future__ import annotations

import base64
import binascii

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.application.services.twilio_service import TwilioService
from app.domain.placa import extraer_placa
from app.infrastructure.acceso_repository import AccesoRepository
from app.infrastructure.face_compare_image_storage import LocalFaceCompareImageStorage
from app.infrastructure.manual_access_image_storage import LocalManualAccessImageStorage


ALLOWED_TIPOS = {
    "qr_residente",
    "qr_visita",
    "visita_sin_qr",
    "visita_peatonal",
    "residente_automatico",
    "manual_guardia",
}


class AccesoService:
    def __init__(
        self,
        repo: AccesoRepository,
        image_storage: LocalManualAccessImageStorage | None = None,
        face_compare_image_storage: LocalFaceCompareImageStorage | None = None,
    ):
        self.repo = repo
        self.image_storage = image_storage or LocalManualAccessImageStorage()
        self.face_compare_image_storage = face_compare_image_storage or LocalFaceCompareImageStorage()

    def crear_acceso_manual_extraordinario(
        self,
        *,
        vivienda_visita_fk: int,
        motivo: str,
        detalle: str | None,
        persona_guardia_fk: int | None,
        persona_residente_autoriza_fk: int | None,
        placa: str | None,
        image_bytes: bytes,
        image_content_type: str | None,
        image_filename: str | None,
        usuario_creado: str | None,
    ) -> GeneralResponse[dict]:
        normalized_motivo = (motivo or "").strip()
        if not normalized_motivo:
            return GeneralResponse(
                success=False,
                message="Motivo es requerido",
                error=ErrorDTO(code="MISSING_MOTIVO", message="Motivo es requerido"),
            )

        if not self.repo.exists_vivienda(int(vivienda_visita_fk)):
            return GeneralResponse(
                success=False,
                message="Vivienda no existe",
                error=ErrorDTO(
                    code="VIVIENDA_NOT_FOUND",
                    message="Vivienda no existe",
                    details={"viviendaVisitaFk": vivienda_visita_fk},
                ),
            )

        if persona_guardia_fk is not None and not self.repo.exists_persona(int(persona_guardia_fk)):
            return GeneralResponse(
                success=False,
                message="Guardia no existe",
                error=ErrorDTO(
                    code="GUARD_NOT_FOUND",
                    message="Guardia no existe",
                    details={"personaGuardiaFk": persona_guardia_fk},
                ),
            )

        if persona_residente_autoriza_fk is not None and not self.repo.exists_persona(int(persona_residente_autoriza_fk)):
            return GeneralResponse(
                success=False,
                message="Residente autorizador no existe",
                error=ErrorDTO(
                    code="RESIDENT_AUTH_NOT_FOUND",
                    message="Residente autorizador no existe",
                    details={"personaResidenteAutorizaFk": persona_residente_autoriza_fk},
                ),
            )

        if not image_bytes:
            return GeneralResponse(
                success=False,
                message="Imagen es requerida",
                error=ErrorDTO(code="MISSING_IMAGE", message="Imagen es requerida"),
            )

        placa_detectada = None
        raw_placa = (placa or "").strip()
        if raw_placa:
            placa_detectada = extraer_placa(raw_placa)
            if not placa_detectada:
                return GeneralResponse(
                    success=False,
                    message="Formato de placa invalido",
                    error=ErrorDTO(
                        code="INVALID_PLACA",
                        message="Formato de placa invalido",
                        details={"received": raw_placa, "expected": ["ABC-123", "GVC-1233"]},
                    ),
                )

        try:
            evidencia_path = self.image_storage.save(
                image_bytes=image_bytes,
                content_type=image_content_type,
                original_filename=image_filename,
            )
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="No se pudo guardar la imagen",
                error=ErrorDTO(
                    code="IMAGE_SAVE_ERROR",
                    message="No se pudo guardar la imagen",
                    details={"error": str(exc)},
                ),
            )

        observacion_parts = []
        normalized_detalle = (detalle or "").strip()
        if normalized_detalle:
            observacion_parts.append(normalized_detalle)
        observacion_parts.append(f"evidencia={evidencia_path}")
        observacion = " | ".join(observacion_parts)
        record = self.repo.create_acceso(
            tipo="manual_guardia",
            vivienda_visita_fk=int(vivienda_visita_fk),
            resultado="autorizado",
            motivo=normalized_motivo,
            persona_guardia_fk=int(persona_guardia_fk) if persona_guardia_fk is not None else None,
            persona_residente_autoriza_fk=(
                int(persona_residente_autoriza_fk) if persona_residente_autoriza_fk is not None else None
            ),
            visita_ingreso_fk=None,
            vehiculo_ingreso_fk=None,
            placa_detectada=placa_detectada,
            biometria_ok=None,
            placa_ok=None,
            observacion=observacion,
            usuario_creado=(usuario_creado or "guardia"),
        )
        self.repo.db.commit()

        return GeneralResponse(
            success=True,
            message="Acceso manual extraordinario registrado",
            data={
                "accesoPk": record["acceso_pk"],
                "tipo": record["tipo"],
                "resultado": record["resultado"],
                "motivo": record["motivo"],
                "viviendaPk": record["vivienda_visita_fk"],
                "placaDetectada": record["placa_detectada"],
                "personaGuardiaFk": record["persona_guardia_fk"],
                "personaResidenteAutorizaFk": record["persona_residente_autoriza_fk"],
                "evidenciaImagenPath": evidencia_path,
                "observacion": record["observacion"],
                "fechaCreado": record["fecha_creado"],
                "usuarioCreado": record["usuario_creado"],
            },
        )

    def crear_acceso_pendiente(
        self,
        *,
        vivienda_visita_fk: int,
        motivo: str,
        visitor_name: str | None,
        foto_rostro_vivo_base64: str | None,
    ) -> GeneralResponse[dict]:
        tipo = "visita_sin_qr"
        usuario = "system"
        persona_guardia_fk = None
        visita_ingreso_fk = None
        vehiculo_ingreso_fk = None
        placa_detectada = None
        biometria_ok = True
        placa_ok = None
        observacion = None
        normalized_motivo = (motivo or "").strip()
        if not normalized_motivo:
            return GeneralResponse(
                success=False,
                message="Motivo es requerido",
                error=ErrorDTO(code="MISSING_MOTIVO", message="Motivo es requerido"),
            )

        normalized_tipo = (tipo or "").strip()
        if normalized_tipo not in ALLOWED_TIPOS:
            return GeneralResponse(
                success=False,
                message="Tipo de acceso invalido",
                error=ErrorDTO(
                    code="INVALID_TIPO",
                    message="Tipo de acceso invalido",
                    details={"allowed": sorted(ALLOWED_TIPOS), "received": normalized_tipo},
                ),
            )

        residente = self.repo.get_residente_por_vivienda_pk(vivienda_pk=vivienda_visita_fk)
        if not residente:
            return GeneralResponse(
                success=False,
                message="No se encontro residente para la vivienda",
                error=ErrorDTO(
                    code="RESIDENT_NOT_FOUND",
                    message="No se encontro residente para la vivienda",
                    details={"viviendaVisitaFk": vivienda_visita_fk},
                ),
            )

        supports_pending = self.repo.supports_resultado_pendiente()
        resultado_inicial = "pendiente" if supports_pending else "no_autorizado"
        motivo_inicial = normalized_motivo
        normalized_base64 = (foto_rostro_vivo_base64 or "").strip()
        if normalized_base64:
            try:
                image_bytes = self._decode_base64(normalized_base64)
            except ValueError:
                return GeneralResponse(
                    success=False,
                    message="Base64 invalido",
                    error=ErrorDTO(code="INVALID_BASE64", message="Base64 invalido"),
                )

            try:
                live_image_path = self.face_compare_image_storage.save_live_image(image_bytes)
            except Exception as exc:
                return GeneralResponse(
                    success=False,
                    message="No se pudo guardar la imagen",
                    error=ErrorDTO(
                        code="IMAGE_SAVE_ERROR",
                        message="No se pudo guardar la imagen",
                        details={"error": str(exc)},
                    ),
                )

            observacion = self._merge_observacion(
                observacion=observacion,
                updates={"faceCompareImage": live_image_path},
            )

        record = self.repo.create_acceso(
            tipo=normalized_tipo,
            vivienda_visita_fk=int(vivienda_visita_fk),
            resultado=resultado_inicial,
            motivo=motivo_inicial,
            persona_guardia_fk=persona_guardia_fk,
            persona_residente_autoriza_fk=int(residente["persona_residente_pk"]),
            visita_ingreso_fk=visita_ingreso_fk,
            vehiculo_ingreso_fk=vehiculo_ingreso_fk,
            placa_detectada=placa_detectada,
            biometria_ok=biometria_ok,
            placa_ok=placa_ok,
            observacion=observacion,
            usuario_creado=(usuario or "system"),
        )
        self.repo.db.commit()

        data = {
            "accesoPk": record["acceso_pk"],
            "visitId": str(record["acceso_pk"]),
            "estado": "pendiente",
            "resultadoPersistido": record["resultado"],
            "motivo": record["motivo"],
            "tipo": record["tipo"],
            "viviendaPk": record["vivienda_visita_fk"],
            "faceCompareImagePath": self._parse_observacion(record.get("observacion")).get("faceCompareImage"),
            "schemaSupportsPendiente": supports_pending,
        }
        return GeneralResponse(success=True, message="Acceso creado en estado pendiente", data=data)

    def iniciar_llamada_autorizacion(
        self,
        *,
        acceso_pk: int,
        twilio_service: TwilioService,
        visitor_name: str | None = None,
    ) -> GeneralResponse[dict]:
        acceso = self.repo.get_by_id(acceso_pk)
        if not acceso:
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(code="NOT_FOUND", message="Acceso no existe", details={"accesoPk": acceso_pk}),
            )

        residente = self.repo.get_residente_por_vivienda_pk(vivienda_pk=int(acceso["vivienda_visita_fk"]))
        if not residente:
            return GeneralResponse(
                success=False,
                message="No se encontro residente para la vivienda del acceso",
                error=ErrorDTO(
                    code="RESIDENT_NOT_FOUND",
                    message="No se encontro residente para la vivienda del acceso",
                    details={"accesoPk": acceso_pk, "viviendaVisitaFk": acceso["vivienda_visita_fk"]},
                ),
            )

        to_number = self._normalizar_celular_ecuador(residente.get("celular"))
        if not to_number:
            return GeneralResponse(
                success=False,
                message="El residente no tiene celular configurado",
                error=ErrorDTO(
                    code="RESIDENT_PHONE_MISSING",
                    message="El residente no tiene celular configurado",
                    details={"accesoPk": acceso_pk, "personaPk": residente.get("persona_residente_pk")},
                ),
            )

        residente_nombre = f"{residente.get('nombres', '').strip()} {residente.get('apellidos', '').strip()}".strip()
        twilio_response = twilio_service.start_call(
            to=to_number,
            resident_name=residente_nombre or None,
            visitor_name=(visitor_name or "").strip() or None,
            visit_id=str(acceso_pk),
        )
        if not twilio_response.success:
            return twilio_response

        twilio_data = twilio_response.data or {}
        return GeneralResponse(
            success=True,
            message="Llamada de autorizacion iniciada",
            data={
                "accesoPk": acceso_pk,
                "callSid": twilio_data.get("callSid"),
                "visitId": twilio_data.get("visitId"),
                "estado": "pendiente",
            },
        )

    def aplicar_decision_twilio(
        self,
        *,
        decision: str,
        visit_id: str,
        digit: str | None,
        call_sid: str | None,
    ) -> GeneralResponse[dict]:
        normalized_decision = (decision or "").strip().lower()
        decision_map = {
            "authorized": "autorizado",
            "rejected": "rechazado",
        }
        if normalized_decision not in decision_map:
            return GeneralResponse(
                success=False,
                message="Decision de twilio invalida",
                error=ErrorDTO(
                    code="INVALID_DECISION",
                    message="Decision de twilio invalida",
                    details={"received": decision, "allowed": sorted(decision_map.keys())},
                ),
            )

        try:
            acceso_pk = int((visit_id or "").strip())
        except ValueError:
            return GeneralResponse(
                success=False,
                message="visitId invalido",
                error=ErrorDTO(
                    code="INVALID_VISIT_ID",
                    message="visitId invalido",
                    details={"visitId": visit_id},
                ),
            )

        acceso = self.repo.get_by_id(acceso_pk)
        if not acceso:
            return GeneralResponse(
                success=False,
                message="No se encontro acceso para actualizar",
                error=ErrorDTO(
                    code="ACCESS_NOT_FOUND",
                    message="No se encontro acceso para actualizar",
                    details={"accesoPk": acceso_pk},
                ),
            )

        observacion = self._merge_observacion(
            observacion=acceso.get("observacion"),
            updates={
                "decision_twilio": normalized_decision,
                "digit": digit,
                "callSid": call_sid,
            },
        )

        updated = self.repo.update_resultado(
            acceso_pk=acceso_pk,
            resultado=decision_map[normalized_decision],
            usuario_actualizado="twilio",
            observacion=observacion,
        )
        if not updated:
            self.repo.db.rollback()
            return GeneralResponse(
                success=False,
                message="No se encontro acceso para actualizar",
                error=ErrorDTO(
                    code="ACCESS_NOT_FOUND",
                    message="No se encontro acceso para actualizar",
                    details={"accesoPk": acceso_pk},
                ),
            )

        self.repo.db.commit()
        return GeneralResponse(
            success=True,
            message="Decision aplicada al acceso",
            data={
                "accesoPk": updated["acceso_pk"],
                "resultado": updated["resultado"],
                "observacion": updated["observacion"],
                "fechaActualizado": updated["fecha_actualizado"],
            },
        )

    def registrar_evidencia_face_compare(
        self,
        *,
        acceso_pk: int,
        image_path: str,
        usuario_actualizado: str | None = None,
    ) -> GeneralResponse[dict]:
        normalized_path = (image_path or "").strip()
        if not normalized_path:
            return GeneralResponse(
                success=False,
                message="Ruta de imagen es requerida",
                error=ErrorDTO(code="MISSING_IMAGE_PATH", message="Ruta de imagen es requerida"),
            )

        acceso = self.repo.get_by_id(acceso_pk)
        if not acceso:
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(code="NOT_FOUND", message="Acceso no existe", details={"accesoPk": acceso_pk}),
            )

        observacion = self._merge_observacion(
            observacion=acceso.get("observacion"),
            updates={"faceCompareImage": normalized_path},
        )
        updated = self.repo.update_observacion(
            acceso_pk=acceso_pk,
            observacion=observacion,
            usuario_actualizado=(usuario_actualizado or "face_compare"),
        )
        if not updated:
            self.repo.db.rollback()
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(code="NOT_FOUND", message="Acceso no existe", details={"accesoPk": acceso_pk}),
            )

        self.repo.db.commit()
        return GeneralResponse(
            success=True,
            message="Evidencia de face compare registrada",
            data={
                "accesoPk": updated["acceso_pk"],
                "faceCompareImage": normalized_path,
                "fechaActualizado": updated["fecha_actualizado"],
                "usuarioActualizado": updated["usuario_actualizado"],
            },
        )

    def obtener_estado_para_polling(self, acceso_pk: int) -> GeneralResponse[dict]:
        record = self.repo.get_by_id(acceso_pk)
        if not record:
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(code="NOT_FOUND", message="Acceso no existe", details={"accesoPk": acceso_pk}),
            )

        observacion_data = self._parse_observacion(record.get("observacion"))
        decision_twilio = (observacion_data.get("decision_twilio") or "").strip().lower()

        if decision_twilio == "authorized":
            estado = "autorizado"
        elif decision_twilio == "rejected":
            estado = "rechazado"
        elif str(record.get("resultado") or "").strip().lower() in {"autorizado", "rechazado"}:
            estado = str(record.get("resultado")).strip().lower()
        else:
            # Si el schema no soporta "pendiente", el backend pudo guardar "no_autorizado"
            # como valor inicial. Para polling se expone el estado logico.
            estado = "pendiente"

        finalizado = estado in {"autorizado", "rechazado"}
        puede_continuar = estado == "autorizado"

        data = {
            "accesoPk": record["acceso_pk"],
            "estado": estado,
            "finalizado": finalizado,
            "puedeContinuar": puede_continuar,
            "resultadoPersistido": record.get("resultado"),
            "motivo": record.get("motivo"),
            "digit": observacion_data.get("digit"),
            "callSid": observacion_data.get("callSid"),
            "fechaActualizado": record.get("fecha_actualizado"),
            "usuarioActualizado": record.get("usuario_actualizado"),
        }
        return GeneralResponse(success=True, message="Estado de acceso obtenido", data=data)

    def obtener_por_id(self, acceso_pk: int) -> GeneralResponse[dict]:
        record = self.repo.get_by_id(acceso_pk)
        if not record:
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(code="NOT_FOUND", message="Acceso no existe", details={"accesoPk": acceso_pk}),
            )
        return GeneralResponse(success=True, message="Acceso encontrado", data=record)

    def actualizar_placa(
        self,
        *,
        acceso_pk: int,
        placa: str,
        usuario_actualizado: str | None = None,
    ) -> GeneralResponse[dict]:
        raw_placa = (placa or "").strip()
        if not raw_placa:
            return GeneralResponse(
                success=False,
                message="Placa es requerida",
                error=ErrorDTO(code="MISSING_PLACA", message="Placa es requerida"),
            )

        placa_normalizada = extraer_placa(raw_placa)
        if not placa_normalizada:
            return GeneralResponse(
                success=False,
                message="Formato de placa invalido",
                error=ErrorDTO(
                    code="INVALID_PLACA",
                    message="Formato de placa invalido",
                    details={"received": raw_placa, "expected": ["ABC-123", "GVC-1233"]},
                ),
            )

        updated = self.repo.update_placa_detectada(
            acceso_pk=acceso_pk,
            placa_detectada=placa_normalizada,
            usuario_actualizado=(usuario_actualizado or "system"),
        )
        if not updated:
            self.repo.db.rollback()
            return GeneralResponse(
                success=False,
                message="Acceso no existe",
                error=ErrorDTO(code="NOT_FOUND", message="Acceso no existe", details={"accesoPk": acceso_pk}),
            )

        self.repo.db.commit()
        return GeneralResponse(
            success=True,
            message="Placa actualizada",
            data={
                "accesoPk": updated["acceso_pk"],
                "placaDetectada": updated["placa_detectada"],
                "fechaActualizado": updated["fecha_actualizado"],
                "usuarioActualizado": updated["usuario_actualizado"],
            },
        )

    @staticmethod
    def _normalizar_celular_ecuador(celular: str | None) -> str | None:
        if celular is None:
            return None
        raw = str(celular).strip()
        if not raw:
            return raw
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return raw
        if digits.startswith("0"):
            return f"+593{digits[1:]}"
        if digits.startswith("593"):
            return f"+{digits}"
        if raw.startswith("+"):
            return raw
        return raw

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
    def _merge_observacion(
        *,
        observacion: str | None,
        updates: dict[str, str | None],
    ) -> str | None:
        parts = [part.strip() for part in str(observacion).split("|") if part.strip()] if observacion else []
        free_parts: list[str] = []
        keyed_parts: dict[str, str] = {}
        keyed_order: list[str] = []

        for part in parts:
            if "=" not in part:
                free_parts.append(part)
                continue
            key, value = part.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                free_parts.append(part)
                continue
            if key not in keyed_order:
                keyed_order.append(key)
            keyed_parts[key] = value

        for key, value in updates.items():
            clean_key = (key or "").strip()
            if not clean_key:
                continue

            if value is None:
                keyed_parts.pop(clean_key, None)
                if clean_key in keyed_order:
                    keyed_order.remove(clean_key)
                continue

            clean_value = str(value).strip()
            if not clean_value:
                keyed_parts.pop(clean_key, None)
                if clean_key in keyed_order:
                    keyed_order.remove(clean_key)
                continue

            if clean_key not in keyed_order:
                keyed_order.append(clean_key)
            keyed_parts[clean_key] = clean_value

        merged_parts = [*free_parts, *[f"{key}={keyed_parts[key]}" for key in keyed_order if key in keyed_parts]]
        return " | ".join(merged_parts) or None

    @staticmethod
    def _decode_base64(value: str) -> bytes:
        raw = value.strip()
        if raw.lower().startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        try:
            return base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("invalid base64") from exc

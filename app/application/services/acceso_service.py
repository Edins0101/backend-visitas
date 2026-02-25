from __future__ import annotations

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.application.services.twilio_service import TwilioService
from app.infrastructure.acceso_repository import AccesoRepository


ALLOWED_TIPOS = {
    "qr_residente",
    "qr_visita",
    "visita_sin_qr",
    "visita_peatonal",
    "residente_automatico",
    "manual_guardia",
}


class AccesoService:
    def __init__(self, repo: AccesoRepository):
        self.repo = repo

    def crear_acceso_pendiente(
        self,
        *,
        vivienda_visita_fk: int,
        motivo: str,
        visitor_name: str | None,
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

        note_parts = [f"decision_twilio={normalized_decision}"]
        if digit:
            note_parts.append(f"digit={digit}")
        if call_sid:
            note_parts.append(f"callSid={call_sid}")
        observacion = " | ".join(note_parts)

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

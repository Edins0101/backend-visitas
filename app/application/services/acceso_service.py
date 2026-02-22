from __future__ import annotations

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
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
        biometria_ok = None
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

        residente_nombre = f"{residente.get('nombres', '').strip()} {residente.get('apellidos', '').strip()}".strip()
        data = {
            "accesoPk": record["acceso_pk"],
            "visitId": str(record["acceso_pk"]),
            "estado": "pendiente",
            "resultadoPersistido": record["resultado"],
            "tipo": record["tipo"],
            "viviendaPk": record["vivienda_visita_fk"],
            "residente": {
                "personaPk": residente["persona_residente_pk"],
                "nombreCompleto": residente_nombre,
                "celular": self._normalizar_celular_ecuador(residente.get("celular")),
            },
            "twilioPayload": {
                "to": self._normalizar_celular_ecuador(residente.get("celular")),
                "residentName": residente_nombre,
                "visitorName": visitor_name or "",
                "visitId": str(record["acceso_pk"]),
            },
            "schemaSupportsPendiente": supports_pending,
        }
        return GeneralResponse(success=True, message="Acceso creado en estado pendiente", data=data)

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

from app.application.dtos.responses.general_response import ErrorDTO, GeneralResponse
from app.infrastructure.vivienda_repository import ViviendaRepository


class CatalogoService:
    def __init__(self, repo: ViviendaRepository):
        self.repo = repo

    def obtener_villas_por_manzana(self) -> GeneralResponse[list[dict]]:
        data = self.repo.get_villas_por_manzana()
        return GeneralResponse(success=True, message="Catalogo de viviendas", data=data)

    def obtener_contacto_residente_por_vivienda(self, manzana: str, villa: str) -> GeneralResponse[dict]:
        data = self.repo.get_residente_contacto_por_manzana_villa(manzana=manzana, villa=villa)
        if not data:
            return GeneralResponse(
                success=False,
                message="No se encontro residente para la vivienda",
                error=ErrorDTO(
                    code="RESIDENT_NOT_FOUND",
                    message="No se encontro residente para la vivienda",
                    details={"manzana": manzana, "villa": villa},
                ),
            )

        data["celular"] = self._normalizar_celular_ecuador(data.get("celular"))

        return GeneralResponse(
            success=True,
            message="Contacto de residente encontrado",
            data=data,
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

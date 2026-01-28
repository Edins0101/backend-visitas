from app.application.dtos.responses.general_response import GeneralResponse
from app.infrastructure.vivienda_repository import ViviendaRepository


class CatalogoService:
    def __init__(self, repo: ViviendaRepository):
        self.repo = repo

    def obtener_villas_por_manzana(self) -> GeneralResponse[list[dict]]:
        data = self.repo.get_villas_por_manzana()
        return GeneralResponse(success=True, message="Catalogo de viviendas", data=data)

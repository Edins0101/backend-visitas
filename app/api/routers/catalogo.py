from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.services.catalogo_service import CatalogoService
from app.infrastructure.vivienda_repository import ViviendaRepository

router = APIRouter(prefix="/catalogo", tags=["Catalogo"])


def get_catalogo_service(db: Session = Depends(get_db)) -> CatalogoService:
    return CatalogoService(repo=ViviendaRepository(db))


@router.get("/viviendas")
def obtener_villas_por_manzana(service: CatalogoService = Depends(get_catalogo_service)):
    return service.obtener_villas_por_manzana()

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.services.catalogo_service import CatalogoService
from app.infrastructure.vivienda_repository import ViviendaRepository

router = APIRouter(prefix="/catalogo", tags=["Catalogo"])
logger = logging.getLogger(__name__)


def _as_loggable_payload(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def get_catalogo_service(db: Session = Depends(get_db)) -> CatalogoService:
    return CatalogoService(repo=ViviendaRepository(db))


@router.get("/viviendas")
def obtener_villas_por_manzana(service: CatalogoService = Depends(get_catalogo_service)):
    logger.info("obtener_viviendas_request")
    response = service.obtener_villas_por_manzana()
    logger.info("obtener_viviendas_response status=200 payload=%s", _as_loggable_payload(response))
    return response

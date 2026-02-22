import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
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


@router.get("/residente")
def obtener_contacto_residente(
    manzana: str,
    villa: str,
    service: CatalogoService = Depends(get_catalogo_service),
):
    logger.info("obtener_contacto_residente_request manzana=%s villa=%s", manzana, villa)
    response = service.obtener_contacto_residente_por_vivienda(manzana=manzana, villa=villa)

    if response.success:
        logger.info("obtener_contacto_residente_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    logger.warning("obtener_contacto_residente_response status=404 payload=%s", _as_loggable_payload(response))
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=response.model_dump())

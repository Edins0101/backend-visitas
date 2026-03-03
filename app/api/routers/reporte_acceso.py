import logging
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.application.services.reporte_acceso_service import ReporteAccesoService
from app.infrastructure.reporte_acceso_repository import ReporteAccesoRepository

router = APIRouter(prefix="/reportes", tags=["Reporteria"])
logger = logging.getLogger(__name__)


def _as_loggable_payload(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def get_reporte_acceso_service(db: Session = Depends(get_db)) -> ReporteAccesoService:
    return ReporteAccesoService(repo=ReporteAccesoRepository(db))


@router.get("/accesos")
def listar_reporte_accesos(
    fecha_desde: date | None = Query(default=None, alias="fechaDesde"),
    fecha_hasta: date | None = Query(default=None, alias="fechaHasta"),
    tipo: str | None = Query(default=None),
    resultado: str | None = Query(default=None),
    vivienda_pk: int | None = Query(default=None, alias="viviendaPk"),
    manzana: str | None = Query(default=None),
    villa: str | None = Query(default=None),
    visitante_identificacion: str | None = Query(default=None, alias="visitanteIdentificacion"),
    visitante_nombre: str | None = Query(default=None, alias="visitanteNombre"),
    placa: str | None = Query(default=None),
    respuesta_llamada: str | None = Query(default=None, alias="respuestaLlamada"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200, alias="pageSize"),
    service: ReporteAccesoService = Depends(get_reporte_acceso_service),
):
    logger.info(
        "reporte_accesos_request fecha_desde=%s fecha_hasta=%s tipo=%s resultado=%s vivienda_pk=%s manzana=%s villa=%s "
        "visitante_identificacion=%s visitante_nombre=%s placa=%s respuesta_llamada=%s page=%s page_size=%s",
        fecha_desde,
        fecha_hasta,
        tipo,
        resultado,
        vivienda_pk,
        manzana,
        villa,
        visitante_identificacion,
        visitante_nombre,
        placa,
        respuesta_llamada,
        page,
        page_size,
    )
    response = service.listar_accesos(
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

    if response.success:
        logger.info("reporte_accesos_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    logger.warning("reporte_accesos_response status=400 payload=%s", _as_loggable_payload(response))
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump())


@router.get("/accesos/resumen")
def obtener_resumen_reporte_accesos(
    fecha_desde: date | None = Query(default=None, alias="fechaDesde"),
    fecha_hasta: date | None = Query(default=None, alias="fechaHasta"),
    tipo: str | None = Query(default=None),
    resultado: str | None = Query(default=None),
    vivienda_pk: int | None = Query(default=None, alias="viviendaPk"),
    manzana: str | None = Query(default=None),
    villa: str | None = Query(default=None),
    visitante_identificacion: str | None = Query(default=None, alias="visitanteIdentificacion"),
    visitante_nombre: str | None = Query(default=None, alias="visitanteNombre"),
    placa: str | None = Query(default=None),
    respuesta_llamada: str | None = Query(default=None, alias="respuestaLlamada"),
    service: ReporteAccesoService = Depends(get_reporte_acceso_service),
):
    logger.info(
        "reporte_accesos_resumen_request fecha_desde=%s fecha_hasta=%s tipo=%s resultado=%s vivienda_pk=%s manzana=%s "
        "villa=%s visitante_identificacion=%s visitante_nombre=%s placa=%s respuesta_llamada=%s",
        fecha_desde,
        fecha_hasta,
        tipo,
        resultado,
        vivienda_pk,
        manzana,
        villa,
        visitante_identificacion,
        visitante_nombre,
        placa,
        respuesta_llamada,
    )
    response = service.obtener_resumen_accesos(
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

    if response.success:
        logger.info("reporte_accesos_resumen_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    logger.warning("reporte_accesos_resumen_response status=400 payload=%s", _as_loggable_payload(response))
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump())


@router.get("/accesos/{acceso_pk}")
def obtener_detalle_reporte_acceso(
    acceso_pk: int,
    service: ReporteAccesoService = Depends(get_reporte_acceso_service),
):
    logger.info("reporte_acceso_detalle_request acceso_pk=%s", acceso_pk)
    response = service.obtener_detalle_acceso(acceso_pk=acceso_pk)

    if response.success:
        logger.info("reporte_acceso_detalle_response status=200 payload=%s", _as_loggable_payload(response))
        return response

    status_code = status.HTTP_400_BAD_REQUEST
    if response.error and response.error.code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND

    logger.warning("reporte_acceso_detalle_response status=%s payload=%s", status_code, _as_loggable_payload(response))
    return JSONResponse(status_code=status_code, content=response.model_dump())

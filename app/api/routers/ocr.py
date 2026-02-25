import base64
import binascii
import logging

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.application.services.face_compare_service import FaceCompareService
from app.application.services.face_service import FaceService
from app.application.services.ocr_service import OcrService
from app.infrastructure.face_compare_adapter import MockFaceCompareAdapter
from app.infrastructure.face_adapter import OpenCvFaceAdapter
from app.infrastructure.ocr_adapter import EasyOcrAdapter
from app.infrastructure.paddle_ocr_adapter import PaddleOcrAdapter

router = APIRouter(prefix="/ocr", tags=["OCR"])
logger = logging.getLogger(__name__)
_adapter = PaddleOcrAdapter()
_fallback_adapter = EasyOcrAdapter()
_face_adapter = OpenCvFaceAdapter()
# Modo temporal: comparar rostros con resultado controlado localmente (sin proveedor externo).
# Cambia a False para simular no coincidencia.
_FACE_COMPARE_FORCE_MATCH = True


def _sanitize_for_log(value, key: str | None = None):
    if hasattr(value, "model_dump"):
        value = value.model_dump()

    if isinstance(value, dict):
        return {k: _sanitize_for_log(v, k) for k, v in value.items()}

    if isinstance(value, list):
        return [_sanitize_for_log(item, key) for item in value]

    if isinstance(value, str):
        if key and "base64" in key.lower():
            return f"<base64 len={len(value)}>"
        if len(value) > 240:
            return f"{value[:240]}..."

    return value


def get_ocr_service() -> OcrService:
    return OcrService(port=_adapter, fallback_port=_fallback_adapter)


def get_face_service() -> FaceService:
    return FaceService(port=_face_adapter)


def get_face_compare_service() -> FaceCompareService:
    return FaceCompareService(port=MockFaceCompareAdapter(match=_FACE_COMPARE_FORCE_MATCH))


class FaceCompareRequest(BaseModel):
    foto_cedula_base64: str
    foto_rostro_vivo_base64: str


# @router.post("/extract")
# async def extract_text(file: UploadFile = File(...), service: OcrService = Depends(get_ocr_service)):
#     if file.content_type not in {"image/jpeg", "image/png"}:
#         return GeneralResponse(
#             success=False,
#             error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
#         )

#     image_bytes = await file.read()
#     return service.extraer_texto(image_bytes)


@router.post("/cedula")
async def extract_cedula(
    file: UploadFile = File(...),
    service: OcrService = Depends(get_ocr_service),
    face_service: FaceService = Depends(get_face_service),
):
    logger.info(
        "extract_cedula_request filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    if file.content_type not in {"image/jpeg", "image/png"}:
        response = GeneralResponse(
            success=False,
            message="Solo se permiten imagenes JPG o PNG",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )
        logger.warning("extract_cedula_response status=415 payload=%s", _sanitize_for_log(response))
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = await file.read()
    logger.info("extract_cedula_image_bytes size=%s", len(image_bytes))
    ocr_response = service.extraer_cedula(image_bytes)
    if not ocr_response.success:
        logger.warning("extract_cedula_response status=500 payload=%s", _sanitize_for_log(ocr_response))
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=ocr_response.model_dump())

    data = ocr_response.data or {}
    if not data.get("es_cedula"):
        data["foto_base64"] = None
        data["foto_formato"] = None
        response = GeneralResponse(success=True, message=ocr_response.message, data=data)
        logger.info("extract_cedula_response status=200 payload=%s", _sanitize_for_log(response))
        return response

    face_response = face_service.extraer_rostro(image_bytes)
    if not face_response.success:
        logger.warning("extract_cedula_response status=500 payload=%s", _sanitize_for_log(face_response))
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=face_response.model_dump())

    face_data = face_response.data or {}
    data["foto_base64"] = face_data.get("image_base64")
    data["foto_formato"] = face_data.get("format")
    response = GeneralResponse(success=True, message=ocr_response.message, data=data)
    logger.info("extract_cedula_response status=200 payload=%s", _sanitize_for_log(response))
    return response


@router.post("/placa")
async def extract_placa(file: UploadFile = File(...), service: OcrService = Depends(get_ocr_service)):
    logger.info(
        "extract_placa_request filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    if file.content_type not in {"image/jpeg", "image/png"}:
        response = GeneralResponse(
            success=False,
            message="Solo se permiten imagenes JPG o PNG",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )
        logger.warning("extract_placa_response status=415 payload=%s", _sanitize_for_log(response))
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = await file.read()
    logger.info("extract_placa_image_bytes size=%s", len(image_bytes))
    response = service.extraer_placa(image_bytes)
    if response.success:
        logger.info("extract_placa_response status=200 payload=%s", _sanitize_for_log(response))
        return response
    logger.warning("extract_placa_response status=500 payload=%s", _sanitize_for_log(response))
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump())


@router.post("/foto")
async def extract_foto(file: UploadFile = File(...), service: FaceService = Depends(get_face_service)):
    logger.info(
        "extract_foto_request filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    if file.content_type not in {"image/jpeg", "image/png"}:
        response = GeneralResponse(
            success=False,
            message="Solo se permiten imagenes JPG o PNG",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )
        logger.warning("extract_foto_response status=415 payload=%s", _sanitize_for_log(response))
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = await file.read()
    logger.info("extract_foto_image_bytes size=%s", len(image_bytes))
    response = service.extraer_rostro(image_bytes)
    if response.success:
        logger.info("extract_foto_response status=200 payload=%s", _sanitize_for_log(response))
        return response
    logger.warning("extract_foto_response status=500 payload=%s", _sanitize_for_log(response))
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump())


@router.post("/face-compare")
async def compare_faces(
    payload: FaceCompareRequest,
    service: FaceCompareService = Depends(get_face_compare_service),
):
    logger.info(
        "compare_faces_request cedula_base64_len=%s vivo_base64_len=%s",
        len(payload.foto_cedula_base64 or ""),
        len(payload.foto_rostro_vivo_base64 or ""),
    )

    try:
        image_a = _decode_base64(payload.foto_cedula_base64)
        image_b = _decode_base64(payload.foto_rostro_vivo_base64)
    except ValueError:
        response = GeneralResponse(
            success=False,
            message="Base64 invalido",
            error=ErrorDTO(code="INVALID_BASE64", message="Base64 invalido"),
        )
        logger.warning("compare_faces_response status=400 payload=%s", _sanitize_for_log(response))
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump())

    response = service.comparar(image_a, image_b)
    if response.success:
        logger.info("compare_faces_response status=200 payload=%s", _sanitize_for_log(response))
        return response
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if response.error and response.error.code == "FACE_COMPARE_PROVIDER_ERROR":
        provider_status_code = (response.error.details or {}).get("provider_status_code")
        if isinstance(provider_status_code, int) and 400 <= provider_status_code <= 599:
            status_code = provider_status_code

    logger.warning("compare_faces_response status=%s payload=%s", status_code, _sanitize_for_log(response))
    return JSONResponse(status_code=status_code, content=response.model_dump())


def _decode_base64(value: str) -> bytes:
    raw = value.strip()
    if raw.lower().startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid base64") from exc

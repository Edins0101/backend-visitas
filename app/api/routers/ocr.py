import base64
import binascii

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.application.services.face_compare_service import FaceCompareService
from app.application.services.face_service import FaceService
from app.application.services.ocr_service import OcrService
from app.infrastructure.face_compare_adapter import OpenCvFaceCompareAdapter, HttpFaceCompareAdapter
from app.infrastructure.face_adapter import OpenCvFaceAdapter
from app.infrastructure.ocr_adapter import EasyOcrAdapter
from app.infrastructure.paddle_ocr_adapter import PaddleOcrAdapter

router = APIRouter(prefix="/ocr", tags=["OCR"])
_adapter = PaddleOcrAdapter()
_fallback_adapter = EasyOcrAdapter()
_face_adapter = OpenCvFaceAdapter()
_face_compare_adapter = HttpFaceCompareAdapter()


def get_ocr_service() -> OcrService:
    return OcrService(port=_adapter, fallback_port=_fallback_adapter)


def get_face_service() -> FaceService:
    return FaceService(port=_face_adapter)


def get_face_compare_service() -> FaceCompareService:
    return FaceCompareService(port=_face_compare_adapter)


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
    if file.content_type not in {"image/jpeg", "image/png"}:
        response = GeneralResponse(
            success=False,
            message="Solo se permiten imagenes JPG o PNG",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = await file.read()
    ocr_response = service.extraer_cedula(image_bytes)
    if not ocr_response.success:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=ocr_response.model_dump())

    data = ocr_response.data or {}
    if not data.get("es_cedula"):
        data["foto_base64"] = None
        data["foto_formato"] = None
        return GeneralResponse(success=True, message=ocr_response.message, data=data)

    face_response = face_service.extraer_rostro(image_bytes)
    if not face_response.success:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=face_response.model_dump())

    face_data = face_response.data or {}
    data["foto_base64"] = face_data.get("image_base64")
    data["foto_formato"] = face_data.get("format")
    return GeneralResponse(success=True, message=ocr_response.message, data=data)


@router.post("/placa")
async def extract_placa(file: UploadFile = File(...), service: OcrService = Depends(get_ocr_service)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        response = GeneralResponse(
            success=False,
            message="Solo se permiten imagenes JPG o PNG",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = await file.read()
    response = service.extraer_placa(image_bytes)
    if response.success:
        return response
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump())


@router.post("/foto")
async def extract_foto(file: UploadFile = File(...), service: FaceService = Depends(get_face_service)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        response = GeneralResponse(
            success=False,
            message="Solo se permiten imagenes JPG o PNG",
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content=response.model_dump())

    image_bytes = await file.read()
    response = service.extraer_rostro(image_bytes)
    if response.success:
        return response
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump())


@router.post("/face-compare")
async def compare_faces(
    payload: FaceCompareRequest,
    service: FaceCompareService = Depends(get_face_compare_service),
):
    try:
        image_a = _decode_base64(payload.foto_cedula_base64)
        image_b = _decode_base64(payload.foto_rostro_vivo_base64)
    except ValueError:
        response = GeneralResponse(
            success=False,
            message="Base64 invalido",
            error=ErrorDTO(code="INVALID_BASE64", message="Base64 invalido"),
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump())

    response = service.comparar(image_a, image_b)
    if response.success:
        return response
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump())


def _decode_base64(value: str) -> bytes:
    raw = value.strip()
    if raw.lower().startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid base64") from exc

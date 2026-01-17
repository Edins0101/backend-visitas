from fastapi import APIRouter, Depends, File, UploadFile

from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.application.services.face_compare_service import FaceCompareService
from app.application.services.face_service import FaceService
from app.application.services.ocr_service import OcrService
from app.infrastructure.face_compare_adapter import OpenCvFaceCompareAdapter
from app.infrastructure.face_adapter import OpenCvFaceAdapter
from app.infrastructure.ocr_adapter import EasyOcrAdapter

router = APIRouter(prefix="/ocr", tags=["OCR"])
_adapter = EasyOcrAdapter()
_face_adapter = OpenCvFaceAdapter()
_face_compare_adapter = OpenCvFaceCompareAdapter()


def get_ocr_service() -> OcrService:
    return OcrService(port=_adapter)


def get_face_service() -> FaceService:
    return FaceService(port=_face_adapter)


def get_face_compare_service() -> FaceCompareService:
    return FaceCompareService(port=_face_compare_adapter)


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
async def extract_cedula(file: UploadFile = File(...), service: OcrService = Depends(get_ocr_service)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        return GeneralResponse(
            success=False,
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )

    image_bytes = await file.read()
    return service.extraer_cedula(image_bytes)


@router.post("/foto")
async def extract_foto(file: UploadFile = File(...), service: FaceService = Depends(get_face_service)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        return GeneralResponse(
            success=False,
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )

    image_bytes = await file.read()
    return service.extraer_rostro(image_bytes)


@router.post("/face-compare")
async def compare_faces(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    service: FaceCompareService = Depends(get_face_compare_service),
):
    if file_a.content_type not in {"image/jpeg", "image/png"} or file_b.content_type not in {"image/jpeg", "image/png"}:
        return GeneralResponse(
            success=False,
            error=ErrorDTO(code="UNSUPPORTED_MEDIA", message="Solo se permiten imagenes JPG o PNG"),
        )

    image_a = await file_a.read()
    image_b = await file_b.read()
    return service.comparar(image_a, image_b)

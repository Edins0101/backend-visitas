import base64

from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.face import FacePort


class FaceService:
    def __init__(self, port: FacePort):
        self.port = port

    def extraer_rostro(self, image_bytes: bytes) -> GeneralResponse[dict]:
        if not image_bytes:
            return GeneralResponse(
                success=False,
                message="Imagen vacia",
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            face_bytes = self.port.extract_face(image_bytes)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al detectar rostro",
                error=ErrorDTO(code="FACE_ERROR", message="Fallo al detectar rostro", details={"error": str(exc)}),
            )

        if not face_bytes:
            return GeneralResponse(
                success=False,
                message="No se encontro rostro",
                error=ErrorDTO(code="FACE_NOT_FOUND", message="No se encontro rostro"),
            )

        encoded = base64.b64encode(face_bytes).decode("ascii")
        return GeneralResponse(
            success=True,
            message="Rostro extraido",
            data={"image_base64": encoded, "format": "jpg"},
        )

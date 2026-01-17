from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.face import FaceComparePort


class FaceCompareService:
    def __init__(self, port: FaceComparePort):
        self.port = port

    def comparar(self, image_a: bytes, image_b: bytes) -> GeneralResponse[dict]:
        if not image_a or not image_b:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            result = self.port.compare(image_a, image_b)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="FACE_COMPARE_ERROR", message="Fallo al comparar rostros", details={"error": str(exc)}),
            )

        if not result:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="FACE_NOT_FOUND", message="No se encontro rostro en alguna imagen"),
            )

        return GeneralResponse(
            success=True,
            data={"match": result.match, "distance": result.distance, "threshold": result.threshold},
        )

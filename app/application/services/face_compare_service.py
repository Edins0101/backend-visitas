from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.face import FaceComparePort, FaceCompareProviderError
from app.infrastructure.face_compare_image_storage import LocalFaceCompareImageStorage


class FaceCompareService:
    def __init__(self, port: FaceComparePort, image_storage: LocalFaceCompareImageStorage | None = None):
        self.port = port
        self.image_storage = image_storage or LocalFaceCompareImageStorage()

    def comparar(self, image_a: bytes, image_b: bytes) -> GeneralResponse[dict]:
        if not image_a or not image_b:
            return GeneralResponse(
                success=False,
                message="Imagen vacia",
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            live_image_path = self.image_storage.save_live_image(image_b)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al guardar imagen de validacion",
                error=ErrorDTO(
                    code="FACE_COMPARE_IMAGE_SAVE_ERROR",
                    message="Fallo al guardar imagen de validacion",
                    details={"error": str(exc)},
                ),
            )

        try:
            result = self.port.compare(image_a, image_b)
        except FaceCompareProviderError as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al comparar rostros",
                error=ErrorDTO(
                    code="FACE_COMPARE_PROVIDER_ERROR",
                    message="Fallo al comparar rostros",
                    details={
                        "provider_status_code": exc.status_code,
                        "provider_response_body": exc.response_body,
                    },
                ),
            )
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al comparar rostros",
                error=ErrorDTO(code="FACE_COMPARE_ERROR", message="Fallo al comparar rostros", details={"error": str(exc)}),
            )

        if not result:
            return GeneralResponse(
                success=False,
                message="No se encontro rostro en alguna imagen",
                error=ErrorDTO(code="FACE_NOT_FOUND", message="No se encontro rostro en alguna imagen"),
            )

        if isinstance(result, dict):
            data = dict(result)
            data["fotoRostroVivoPath"] = live_image_path
            return GeneralResponse(
                success=True,
                message="Comparacion realizada",
                data=data,
            )

        return GeneralResponse(
            success=True,
            message="Comparacion realizada",
            data={
                "match": result.match,
                "distance": result.distance,
                "threshold": result.threshold,
                "fotoRostroVivoPath": live_image_path,
            },
        )

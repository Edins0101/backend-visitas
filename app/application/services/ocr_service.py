from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.ecuador_id import extraer_cedula, extraer_nombres
from app.domain.ocr import OcrPort


class OcrService:
    def __init__(self, port: OcrPort):
        self.port = port

    def extraer_texto(self, image_bytes: bytes) -> GeneralResponse[dict]:
        if not image_bytes:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            result = self.port.extract_text(image_bytes)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="OCR_ERROR", message="Fallo al procesar OCR", details={"error": str(exc)}),
            )

        return GeneralResponse(
            success=True,
            data={
                "text": result.text,
                "lines": [
                    {"text": line.text, "confidence": line.confidence, "bbox": line.bbox}
                    for line in result.lines
                ],
            },
        )

    def extraer_cedula(self, image_bytes: bytes) -> GeneralResponse[dict]:
        if not image_bytes:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            result = self.port.extract_text(image_bytes)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(code="OCR_ERROR", message="Fallo al procesar OCR", details={"error": str(exc)}),
            )

        cedula = extraer_cedula(result.text)
        if not cedula:
            for line in result.lines:
                cedula = extraer_cedula(line.text)
                if cedula:
                    break

        if not cedula:
            return GeneralResponse(
                success=False,
                error=ErrorDTO(
                    code="CEDULA_NOT_FOUND",
                    message="No se encontro cedula valida",
                    details={"es_cedula": False},
                ),
            )

        line_texts = [line.text for line in result.lines] or result.text.splitlines()
        nombres = extraer_nombres(line_texts)
        return GeneralResponse(
            success=True,
            data={"cedula": cedula, "es_cedula": True, "nombres": nombres},
        )

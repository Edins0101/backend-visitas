from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.ecuador_id import extraer_cedula, extraer_nombres
from app.domain.placa import extraer_placa, extraer_placa_en_lineas
from app.domain.ocr import OcrPort


class OcrService:
    def __init__(self, port: OcrPort):
        self.port = port

    def extraer_texto(self, image_bytes: bytes) -> GeneralResponse[dict]:
        if not image_bytes:
            return GeneralResponse(
                success=False,
                message="Imagen vacia",
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            result = self.port.extract_text(image_bytes)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al procesar OCR",
                error=ErrorDTO(code="OCR_ERROR", message="Fallo al procesar OCR", details={"error": str(exc)}),
            )

        return GeneralResponse(
            success=True,
            message="OCR procesado",
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
                message="Imagen vacia",
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            result = self.port.extract_text(image_bytes)
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al procesar OCR",
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
                success=True,
                message="No es cedula ecuatoriana",
                data={"cedula": None, "es_cedula": False, "nombres": None},
            )

        line_texts = [line.text for line in result.lines] or result.text.splitlines()
        nombres = extraer_nombres(line_texts)
        return GeneralResponse(
            success=True,
            message="Cedula procesada",
            data={"cedula": cedula, "es_cedula": True, "nombres": nombres},
        )

    def extraer_placa(self, image_bytes: bytes) -> GeneralResponse[dict]:
        if not image_bytes:
            return GeneralResponse(
                success=False,
                message="Imagen vacia",
                error=ErrorDTO(code="EMPTY_IMAGE", message="Imagen vacia"),
            )

        try:
            result = self.port.extract_text(image_bytes, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
        except Exception as exc:
            return GeneralResponse(
                success=False,
                message="Fallo al procesar OCR",
                error=ErrorDTO(code="OCR_ERROR", message="Fallo al procesar OCR", details={"error": str(exc)}),
            )

        placa = None
        best_conf = -1.0
        for line in result.lines:
            candidata = extraer_placa(line.text)
            if candidata and line.confidence > best_conf:
                best_conf = line.confidence
                placa = candidata

        if not placa:
            placa = extraer_placa(result.text)
        if not placa:
            placa = extraer_placa_en_lineas([line.text for line in result.lines])

        if not placa:
            return GeneralResponse(
                success=True,
                message="No se encontro placa",
                data={"placa": None},
            )

        return GeneralResponse(
            success=True,
            message="Placa procesada",
            data={"placa": placa},
        )

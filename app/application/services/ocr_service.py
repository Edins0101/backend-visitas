from app.application.dtos.responses.general_response import GeneralResponse, ErrorDTO
from app.domain.ecuador_id import (
    extraer_cedula,
    extraer_cedula_etiquetada,
    extraer_cedula_patron,
    extraer_nombres,
    validar_cedula,
)
from app.domain.placa import extraer_placa, extraer_placa_en_lineas
from app.domain.ocr import OcrPort


class OcrService:
    def __init__(self, port: OcrPort, fallback_port: OcrPort | None = None):
        self.port = port
        self.fallback_port = fallback_port

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

        result, digits_result, roi_results, ocr_error = self._run_ocr_for_cedula(image_bytes, self.port)
        if ocr_error and self.fallback_port is not None:
            result, digits_result, roi_results, ocr_error = self._run_ocr_for_cedula(image_bytes, self.fallback_port)
        if ocr_error:
            return ocr_error

        cedula, nombres = self._extraer_cedula_y_nombres(result, digits_result, roi_results)
        if not cedula and self.fallback_port is not None:
            fallback_result, fallback_digits, fallback_rois, fallback_error = self._run_ocr_for_cedula(
                image_bytes, self.fallback_port
            )
            if fallback_error:
                return fallback_error
            cedula, nombres = self._extraer_cedula_y_nombres(fallback_result, fallback_digits, fallback_rois)

        if not cedula:
            details = _build_debug_details(result, digits_result, roi_results)
            return GeneralResponse(
                success=True,
                message="No es cedula ecuatoriana",
                data={"cedula": None, "es_cedula": False, "nombres": None, "debug": details},
            )

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

    def _run_ocr_for_cedula(self, image_bytes: bytes, port: OcrPort):
        try:
            result = port.extract_text(image_bytes, preprocess_mode="document")
            digits_result = port.extract_text(
                image_bytes,
                allowlist="0123456789",
                preprocess_mode="document",
            )
            roi_results = []
            for roi in _NUI_ROIS:
                roi_results.append(
                    port.extract_text(
                        image_bytes,
                        allowlist="0123456789",
                        preprocess_mode="document",
                        roi=roi,
                    )
                )
            name_results = []
            for roi in _NAME_ROIS:
                name_results.append(
                    port.extract_text(
                        image_bytes,
                        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ ",
                        preprocess_mode="document",
                        roi=roi,
                        binarize=True,
                    )
                )
            # Fallback: grab a wider middle-left band for names
            name_results.append(
                port.extract_text(
                    image_bytes,
                    allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ ",
                    preprocess_mode="document",
                    roi=_NAME_BAND_ROI,
                    binarize=True,
                )
            )
        except Exception as exc:
            return None, None, None, GeneralResponse(
                success=False,
                message="Fallo al procesar OCR",
                error=ErrorDTO(code="OCR_ERROR", message="Fallo al procesar OCR", details={"error": str(exc)}),
            )
        if _is_empty_result(result) and _is_empty_result(digits_result):
            return None, None, None, GeneralResponse(
                success=False,
                message="OCR sin texto",
                error=ErrorDTO(code="OCR_EMPTY", message="OCR sin texto"),
            )

        merged = digits_result
        for roi_result in roi_results:
            merged = _merge_digits(merged, roi_result)
        for name_result in name_results:
            result = _merge_results(result, name_result)
        return result, merged, roi_results, None

    def _extraer_cedula_y_nombres(self, result, digits_result, roi_results):
        line_texts = [line.text for line in result.lines] or result.text.splitlines()
        cedula = _extraer_cedula_desde_rois(roi_results)
        if not cedula:
            cedula = extraer_cedula_patron(result.text)
        if not cedula:
            cedula = extraer_cedula_etiquetada(line_texts)
        if not cedula:
            cedula = _extraer_cedula_por_ancla(result)
        if not cedula:
            candidates = _collect_valid_candidates(line_texts, result, digits_result)
            if len(candidates) == 1:
                cedula = candidates[0]

        if not cedula:
            return None, None

        nombres = extraer_nombres(line_texts)
        return cedula, nombres


def _extraer_cedula_por_ancla(result) -> str | None:
    anchors = []
    candidates = []
    for line in result.lines:
        text = line.text.upper()
        if "NUI" in text or "DOCUMENTO" in text or "DOC." in text:
            anchors.append(line)
        cand = _extraer_cedulas_validas(text)
        for value in cand:
            candidates.append((value, line))

    if not anchors or not candidates:
        return None

    def _center(bbox):
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    best = None
    best_dist = None
    for anchor in anchors:
        ax, ay = _center(anchor.bbox)
        for value, line in candidates:
            lx, ly = _center(line.bbox)
            # prefer same horizontal band and near to the right
            dy = abs(ly - ay)
            dx = lx - ax
            if dx < -20:
                continue
            score = dy * 1.5 + max(0, dx) * 0.1
            if best_dist is None or score < best_dist:
                best_dist = score
                best = value
    return best


def _extraer_cedulas_validas(texto: str) -> list[str]:
    digits = "".join(ch for ch in texto if ch.isdigit())
    found = []
    if len(digits) < 10:
        return found
    for i in range(len(digits) - 9):
        candidato = digits[i : i + 10]
        if validar_cedula(candidato):
            found.append(candidato)
    return found


def _merge_digits(primary, secondary):
    if not secondary:
        return primary
    if not primary:
        return secondary
    merged_lines = list(primary.lines) + list(secondary.lines)
    merged_text = "\n".join([primary.text, secondary.text]).strip()
    return type(primary)(text=merged_text, lines=merged_lines)


def _merge_results(primary, secondary):
    if not secondary:
        return primary
    if not primary:
        return secondary
    merged_lines = list(primary.lines) + list(secondary.lines)
    merged_text = "\n".join([primary.text, secondary.text]).strip()
    return type(primary)(text=merged_text, lines=merged_lines)


def _extraer_cedula_desde_rois(roi_results) -> str | None:
    if not roi_results:
        return None
    for roi in roi_results:
        if not roi:
            continue
        # Prefer any valid cedula found inside ROI
        candidatos = _extraer_cedulas_validas(roi.text)
        if candidatos:
            return candidatos[0]
        for line in roi.lines:
            candidatos = _extraer_cedulas_validas(line.text)
            if candidatos:
                return candidatos[0]
    return None


def _build_debug_details(result, digits_result, roi_results):
    return {
        "roi_texts": [r.text for r in roi_results if r],
        "digits_text": digits_result.text if digits_result else None,
        "full_text": result.text if result else None,
        "valid_candidates": _collect_valid_candidates(
            [line.text for line in result.lines] if result else [],
            result,
            digits_result,
        ),
    }


def _is_empty_result(result) -> bool:
    if not result:
        return True
    if result.text and result.text.strip():
        return False
    return not result.lines


def _collect_valid_candidates(line_texts, result, digits_result) -> list[str]:
    candidates: list[str] = []
    for line in line_texts:
        for value in _extraer_cedulas_validas(line):
            candidates.append(value)
    for line in digits_result.lines:
        for value in _extraer_cedulas_validas(line.text):
            candidates.append(value)
    for value in _extraer_cedulas_validas(digits_result.text):
        candidates.append(value)
    for value in _extraer_cedulas_validas(result.text):
        candidates.append(value)

    unique = []
    seen = set()
    for value in candidates:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


# ROI for NUI zone on normalized document (x, y, w, h) as ratios
_NUI_ROIS = [
    # New ID: NUI bottom-left
    (0.03, 0.72, 0.45, 0.22),
    # Older ID: number top-right
    (0.58, 0.05, 0.38, 0.16),
    # Older ID: number mid-right
    (0.58, 0.20, 0.38, 0.20),
    # Older ID: number right band (fallback)
    (0.52, 0.00, 0.46, 0.30),
    # Older ID: NUI label top-right tighter
    (0.62, 0.04, 0.30, 0.12),
]

# Name zones (apellidos + nombres)
_NAME_ROIS = [
    # New ID: center-left block
    (0.32, 0.22, 0.34, 0.28),
    # Old ID: center block
    (0.30, 0.26, 0.40, 0.22),
    # Old ID: center-right block
    (0.34, 0.22, 0.36, 0.22),
]

# Wider band where "APELLIDOS Y NOMBRES" typically sits (older IDs)
_NAME_BAND_ROI = (0.22, 0.18, 0.50, 0.34)

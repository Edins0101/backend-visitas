import os
import threading
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

from app.domain.ocr import OcrPort, OcrResult, OcrLine

os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")


class PaddleOcrAdapter(OcrPort):
    def __init__(
        self,
        lang: Optional[str] = None,
        use_gpu: Optional[bool] = None,
        use_angle_cls: Optional[bool] = None,
    ):
        self.lang = lang or os.getenv("PADDLE_OCR_LANG", "es")
        env_gpu = os.getenv("PADDLE_OCR_GPU", "false").lower()
        self.use_gpu = use_gpu if use_gpu is not None else env_gpu in {"1", "true", "yes"}
        env_angle = os.getenv("PADDLE_OCR_ANGLE", "true").lower()
        self.use_angle_cls = use_angle_cls if use_angle_cls is not None else env_angle in {"1", "true", "yes"}
        self._ocr = None
        self._lock = threading.Lock()

    def extract_text(
        self,
        image_bytes: bytes,
        allowlist: str | None = None,
        preprocess_mode: str | None = None,
        roi: tuple[float, float, float, float] | None = None,
        binarize: bool = False,
    ) -> OcrResult:
        image = _load_image_bgr(image_bytes)
        _debug_dump(image, "input")
        if preprocess_mode == "document":
            image = _normalize_document(image)
            _debug_dump(image, "document")
        if roi is not None:
            image = _crop_roi(image, roi)
            _debug_dump(image, "roi")
        image = _upscale_if_needed(image)
        _debug_dump(image, "upscaled")
        if binarize:
            image = _binarize_strong(image)
            _debug_dump(image, "binarized")

        ocr = self._get_ocr()
        try:
            result = ocr.ocr(image, cls=self.use_angle_cls)
        except TypeError:
            # Older versions may not accept cls parameter
            result = ocr.ocr(image)

        lines = []
        texts = []
        for line in result[0] if result else []:
            bbox, (text, conf) = line
            text = _apply_allowlist(text, allowlist)
            if not text:
                continue
            lines.append(OcrLine(text=text, confidence=float(conf), bbox=bbox))
            texts.append(text)

        return OcrResult(text="\n".join(texts).strip(), lines=lines)

    def _get_ocr(self):
        if self._ocr is None:
            with self._lock:
                if self._ocr is None:
                    from inspect import signature
                    from paddleocr import PaddleOCR

                    kwargs = {
                        "use_angle_cls": self.use_angle_cls,
                        "lang": self.lang,
                        "use_gpu": self.use_gpu,
                    }
                    params = signature(PaddleOCR.__init__).parameters
                    filtered = {k: v for k, v in kwargs.items() if k in params}
                    self._ocr = PaddleOCR(**filtered)
        return self._ocr


def _apply_allowlist(text: str, allowlist: Optional[str]) -> str:
    if not allowlist:
        return text
    allowed = set(allowlist)
    return "".join(ch for ch in text if ch in allowed)


def _load_image_bgr(image_bytes: bytes) -> np.ndarray:
    data = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        return image
    return image


def _normalize_document(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            pts = _order_points(approx.reshape(4, 2))
            warped = _four_point_transform(image, pts)
            if _is_reasonable_document(image, warped):
                return warped
            return image
    return image


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    (tl, tr, br, bl) = pts
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = int(max(width_a, width_b))
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = int(max(height_a, height_b))
    if max_w < 1 or max_h < 1:
        return image
    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(pts, dst)
    return cv2.warpPerspective(image, matrix, (max_w, max_h))


def _crop_roi(image: np.ndarray, roi: tuple[float, float, float, float]) -> np.ndarray:
    x, y, w, h = roi
    h_img, w_img = image.shape[0], image.shape[1]
    x1 = int(max(0, min(1, x)) * w_img)
    y1 = int(max(0, min(1, y)) * h_img)
    x2 = int(max(0, min(1, x + w)) * w_img)
    y2 = int(max(0, min(1, y + h)) * h_img)
    if x2 <= x1 or y2 <= y1:
        return image
    crop = image[y1:y2, x1:x2]
    if crop.shape[0] < 40 or crop.shape[1] < 80:
        return image
    return crop


def _is_reasonable_document(original: np.ndarray, warped: np.ndarray) -> bool:
    h, w = warped.shape[0], warped.shape[1]
    if h < 300 or w < 400:
        return False
    ratio = w / max(h, 1)
    if ratio < 1.1 or ratio > 2.5:
        return False
    oh, ow = original.shape[0], original.shape[1]
    if w < ow * 0.4 or h < oh * 0.4:
        return False
    return True


def _upscale_if_needed(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[0], image.shape[1]
    if h >= 900:
        return image
    scale = 2.0
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def _binarize_strong(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    thr = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 6
    )
    return cv2.cvtColor(thr, cv2.COLOR_GRAY2BGR)


def _debug_dump(image: np.ndarray, label: str) -> None:
    if os.getenv("OCR_DEBUG_SAVE", "false").lower() not in {"1", "true", "yes"}:
        return
    out_dir = os.getenv("OCR_DEBUG_DIR", ".ocr_debug")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(out_dir, f"{ts}_{label}.jpg")
    try:
        cv2.imwrite(path, image)
    except Exception:
        pass

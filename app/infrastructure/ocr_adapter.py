import io
import os
import threading
from typing import List, Optional

import easyocr
import numpy as np
import cv2
from PIL import Image

from app.domain.ocr import OcrPort, OcrResult, OcrLine


class EasyOcrAdapter(OcrPort):
    def __init__(self, languages: Optional[List[str]] = None, gpu: Optional[bool] = None):
        env_langs = os.getenv("EASYOCR_LANGS", "es,en")
        self.languages = languages or [lang.strip() for lang in env_langs.split(",") if lang.strip()]
        env_gpu = os.getenv("EASYOCR_GPU", "false").lower()
        self.gpu = gpu if gpu is not None else env_gpu in {"1", "true", "yes"}
        env_pre = os.getenv("EASYOCR_PREPROCESS", "true").lower()
        self.preprocess = env_pre in {"1", "true", "yes"}
        self._reader = None
        self._lock = threading.Lock()

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        image = _load_image(image_bytes)
        reader = self._get_reader()
        results = []
        for img in _iter_ocr_images(image, self.preprocess):
            results.extend(reader.readtext(img, detail=1, paragraph=False))
        results = _dedupe_results(results)

        lines: List[OcrLine] = []
        texts: List[str] = []
        for bbox, text, conf in results:
            norm_bbox = [[float(p[0]), float(p[1])] for p in bbox]
            lines.append(OcrLine(text=text, confidence=float(conf), bbox=norm_bbox))
            texts.append(text)

        full_text = "\n".join(texts).strip()
        return OcrResult(text=full_text, lines=lines)

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            with self._lock:
                if self._reader is None:
                    self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
        return self._reader


def _load_image(image_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        return np.array(image.convert("RGB"))


def _iter_ocr_images(image: np.ndarray, preprocess: bool):
    yield image
    if not preprocess:
        return
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.bilateralFilter(enhanced, 7, 50, 50)
    yield denoised
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 12
    )
    yield thresh


def _dedupe_results(results):
    merged = {}
    for bbox, text, conf in results:
        key = text.strip()
        if not key:
            continue
        current = merged.get(key)
        if current is None or conf > current[2]:
            merged[key] = (bbox, key, conf)
    return list(merged.values())

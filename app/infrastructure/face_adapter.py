import io
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.domain.face import FacePort


class OpenCvFaceAdapter(FacePort):
    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)

    def extract_face(self, image_bytes: bytes) -> Optional[bytes]:
        image = _load_image(image_bytes)
        crop = _detect_and_crop_face(image, self._cascade)
        if crop is None:
            return None
        success, encoded = cv2.imencode(".jpg", crop)
        if not success:
            return None
        return encoded.tobytes()


def _load_image(image_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        return np.array(image.convert("RGB"))


def _detect_and_crop_face(image: np.ndarray, cascade) -> Optional[np.ndarray]:
    primary = _detect_on_image(image, cascade)
    if primary is not None:
        return primary

    best_crop = None
    best_area = 0
    for rotated in _iter_rotations(image):
        if rotated is image:
            continue
        gray = cv2.cvtColor(rotated, cv2.COLOR_RGB2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        for (x, y, w, h) in faces:
            area = w * h
            if area > best_area:
                best_area = area
                best_crop = _crop_with_margin(rotated, x, y, w, h, 0.35)
    return best_crop


def _detect_on_image(image: np.ndarray, cascade) -> Optional[np.ndarray]:
    best_crop = None
    best_area = 0
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    for (x, y, w, h) in faces:
        area = w * h
        if area > best_area:
            best_area = area
            best_crop = _crop_with_margin(image, x, y, w, h, 0.35)
    return best_crop


def _iter_rotations(image: np.ndarray):
    yield image
    yield cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    yield cv2.rotate(image, cv2.ROTATE_180)
    yield cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def _crop_with_margin(image: np.ndarray, x: int, y: int, w: int, h: int, margin: float) -> np.ndarray:
    pad_w = int(w * margin)
    pad_h = int(h * margin)
    x1 = max(x - pad_w, 0)
    y1 = max(y - pad_h, 0)
    x2 = min(x + w + pad_w, image.shape[1])
    y2 = min(y + h + pad_h, image.shape[0])
    return image[y1:y2, x1:x2]

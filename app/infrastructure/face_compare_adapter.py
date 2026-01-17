import os
from typing import Optional

import cv2
import numpy as np

from app.domain.face import FaceComparePort, FaceMatchResult


class OpenCvFaceCompareAdapter(FaceComparePort):
    def __init__(self, threshold: Optional[float] = None):
        env_threshold = os.getenv("FACE_MATCH_THRESHOLD", "0.45")
        self.threshold = threshold if threshold is not None else float(env_threshold)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)

    def compare(self, image_a: bytes, image_b: bytes) -> Optional[FaceMatchResult]:
        face_a = _get_face_crop(image_a, self._cascade)
        face_b = _get_face_crop(image_b, self._cascade)
        if face_a is None or face_b is None:
            return None
        score = _orb_similarity(face_a, face_b)
        if score is None:
            score = _hist_similarity(face_a, face_b)
        distance = float(1.0 - score)
        match = distance <= self.threshold
        return FaceMatchResult(match=match, distance=distance, threshold=self.threshold)


def _get_face_crop(image_bytes: bytes, cascade) -> Optional[np.ndarray]:
    image = _load_image(image_bytes)
    best_crop = None
    best_area = 0
    for rotated in _iter_rotations(image):
        gray = cv2.cvtColor(rotated, cv2.COLOR_RGB2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        for (x, y, w, h) in faces:
            area = w * h
            if area > best_area:
                best_area = area
                best_crop = _crop_with_margin(rotated, x, y, w, h, 0.2)
    return best_crop


def _load_image(image_bytes: bytes) -> np.ndarray:
    data = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


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


def _orb_similarity(face_a: np.ndarray, face_b: np.ndarray) -> Optional[float]:
    gray_a = _prep_gray(face_a)
    gray_b = _prep_gray(face_b)
    orb = cv2.ORB_create(nfeatures=500)
    kp_a, des_a = orb.detectAndCompute(gray_a, None)
    kp_b, des_b = orb.detectAndCompute(gray_b, None)
    if des_a is None or des_b is None:
        return None
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des_a, des_b)
    if not matches:
        return None
    max_kp = max(len(kp_a), len(kp_b), 1)
    score = len(matches) / max_kp
    return max(0.0, min(1.0, score))


def _hist_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    gray_a = _prep_gray(face_a)
    gray_b = _prep_gray(face_b)
    hist_a = cv2.calcHist([gray_a], [0], None, [64], [0, 256])
    hist_b = cv2.calcHist([gray_b], [0], None, [64], [0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)
    corr = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    score = (corr + 1.0) / 2.0
    return max(0.0, min(1.0, score))


def _prep_gray(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return cv2.resize(gray, (160, 160))

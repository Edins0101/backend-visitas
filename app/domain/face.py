from dataclasses import dataclass
from typing import Protocol, Optional


class FacePort(Protocol):
    def extract_face(self, image_bytes: bytes) -> Optional[bytes]:
        ...


@dataclass
class FaceMatchResult:
    match: bool
    distance: float
    threshold: float


class FaceComparePort(Protocol):
    def compare(self, image_a: bytes, image_b: bytes) -> Optional[FaceMatchResult]:
        ...

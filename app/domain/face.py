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


class FaceCompareProviderError(Exception):
    def __init__(self, status_code: int, response_body: str):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"Face compare provider returned HTTP {status_code}: {response_body}")

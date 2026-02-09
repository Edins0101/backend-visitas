from dataclasses import dataclass
from typing import Protocol, List


@dataclass
class OcrLine:
    text: str
    confidence: float
    bbox: List[List[float]]


@dataclass
class OcrResult:
    text: str
    lines: List[OcrLine]


class OcrPort(Protocol):
    def extract_text(
        self,
        image_bytes: bytes,
        allowlist: str | None = None,
        preprocess_mode: str | None = None,
        roi: tuple[float, float, float, float] | None = None,
        binarize: bool = False,
    ) -> OcrResult:
        ...

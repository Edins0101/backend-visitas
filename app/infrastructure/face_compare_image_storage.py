from __future__ import annotations

import io
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps


class LocalFaceCompareImageStorage:
    def __init__(self, base_dir: str | None = None):
        configured = base_dir or os.getenv("FACE_COMPARE_IMAGE_DIR", "storage/face_compare_live")
        self.base_dir = Path(configured)

    def save_live_image(self, image_bytes: bytes) -> str:
        if not image_bytes:
            raise ValueError("empty image")

        day_folder = datetime.now().strftime("%Y%m%d")
        target_dir = self.base_dir / day_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"live_{datetime.now().strftime('%H%M%S_%f')}_{uuid4().hex[:8]}.jpg"
        target_path = target_dir / filename

        normalized = _to_jpeg_bytes(image_bytes)
        target_path.write_bytes(normalized)
        return str(target_path).replace("\\", "/")


def _to_jpeg_bytes(image_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as image:
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        out = io.BytesIO()
        normalized.save(out, format="JPEG", quality=92)
        return out.getvalue()

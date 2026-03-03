from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class LocalManualAccessImageStorage:
    def __init__(self, base_dir: str | None = None):
        configured = base_dir or os.getenv("ACCESO_MANUAL_IMAGE_DIR", "storage/accesos_manual")
        self.base_dir = Path(configured)

    def save(
        self,
        *,
        image_bytes: bytes,
        content_type: str | None,
        original_filename: str | None,
    ) -> str:
        if not image_bytes:
            raise ValueError("empty image")

        extension = _resolve_extension(content_type=content_type, original_filename=original_filename)
        day_folder = datetime.now().strftime("%Y%m%d")
        target_dir = self.base_dir / day_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%H%M%S_%f")
        filename = f"manual_{timestamp}_{uuid4().hex[:8]}{extension}"
        target_path = target_dir / filename
        target_path.write_bytes(image_bytes)

        return str(target_path).replace("\\", "/")


def _resolve_extension(*, content_type: str | None, original_filename: str | None) -> str:
    allowed_by_content_type = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    normalized_type = (content_type or "").strip().lower()
    if normalized_type in allowed_by_content_type:
        return allowed_by_content_type[normalized_type]

    if original_filename and "." in original_filename:
        ext = Path(original_filename).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp"}:
            return ".jpg" if ext == ".jpeg" else ext

    return ".jpg"

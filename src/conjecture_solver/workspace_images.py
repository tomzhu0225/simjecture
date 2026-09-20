"""Bounded, read-only image transport from the scientific workspace."""

from __future__ import annotations

import base64
import hashlib
import io
import warnings
from pathlib import Path
from typing import Any

from PIL import Image

MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MIME_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def read_workspace_image(workspace: Path, relative: str) -> dict[str, Any]:
    root = workspace.resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("image path escapes the campaign workspace")
    with path.open("rb") as stream:
        encoded = stream.read(MAX_IMAGE_BYTES + 1)
    if len(encoded) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds the 4 MiB transport limit")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(encoded)) as image:
            if image.format not in MIME_TYPES:
                raise ValueError("workspace images must be PNG, JPEG, or WebP")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("image exceeds the 16 megapixel limit")
            mime = MIME_TYPES[image.format]
            width, height = image.size
            image.verify()
    return {
        "path": relative,
        "mime_type": mime,
        "width": width,
        "height": height,
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "data": base64.b64encode(encoded).decode("ascii"),
        "note": "Visual inspection only; reading an image does not accept scientific evidence.",
    }

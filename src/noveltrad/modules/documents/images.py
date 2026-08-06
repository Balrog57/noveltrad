"""Image decoding and lossless WebP conversion (SDD 10.5, 10.6)."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from noveltrad.core.atomic_files import write_atomic
from noveltrad.core.exceptions import ImportConversionError

from .limits import MAX_IMAGE_PIXELS

_DATA_URI_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)$")


def decode_data_uri(value: str) -> tuple[str, bytes]:
    """Decode a Markdown data: image URI; None if unsupported (10.5)."""
    match = _DATA_URI_RE.match(value)
    if not match:
        raise ImportConversionError("IMAGE_UNSUPPORTED", "unsupported image data URI")
    import base64

    payload = base64.b64decode(match.group(2))
    return match.group(1), payload


def convert_to_webp(payload: bytes, output_dir: Path) -> str:
    """Convert image bytes to WebP lossless; returns the relative file name
    images/<sha256>.webp (deduplicated by content)."""
    try:
        image = Image.open(io.BytesIO(payload))
        width, height = image.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ImportConversionError(
                "IMAGE_TOO_LARGE",
                f"image exceeds {MAX_IMAGE_PIXELS} pixels",
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        webp_bytes = io.BytesIO()
        image.convert("RGBA").save(webp_bytes, format="WEBP", lossless=True)
        digest = hashlib.sha256(webp_bytes.getvalue()).hexdigest()
        target = output_dir / f"{digest}.webp"
        if not target.exists():
            write_atomic(target, webp_bytes.getvalue())
        return f"images/{digest}.webp"
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImportConversionError("IMAGE_DECODE_FAILED", "image decoding failed") from exc


def convert_markdown_images(markdown: str, output_dir: Path) -> str:
    """Replace embedded data: images in GFM with WebP relative references."""
    result = markdown

    def replace(match: re.Match[str]) -> str:
        alt = match.group(1)
        uri = match.group(2)
        try:
            _, payload = decode_data_uri(uri)
        except ImportConversionError:
            return match.group(0)
        try:
            relative = convert_to_webp(payload, output_dir)
        except ImportConversionError:
            return match.group(0)
        return f"![{alt}]({relative})"

    return re.sub(r"!\[([^\]]*)\]\((data:image/[^)]+)\)", replace, result)


def validate_references(markdown: str, base_dir: Path) -> list[str]:
    """Check that every images/<sha>.webp reference exists; returns errors."""
    errors: list[str] = []
    for match in re.finditer(r"!\[[^\]]*\]\((images/[a-f0-9]+\.webp)\)", markdown):
        target = base_dir / match.group(1)
        if not target.exists():
            errors.append(f"MISSING_IMAGE:{match.group(1)}")
    return errors

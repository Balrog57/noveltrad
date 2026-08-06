"""ZIP archive generation (SDD 15.3-15.6, 15.12).

The only artifact: noveltrad-<project_id>.zip containing exactly
<slug>.md and zero or more entries images/<sha256>.webp. Generation is on
the fly; the archive is removed after download closes or after a 24-hour
expiration. Entries are POSIX relative paths without root, '..', backslash,
control characters or Unicode NFC collisions. ZIP timestamps are fixed to
1980-01-01 00:00:00 and DEFLATE level 6.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from pathlib import Path

from noveltrad.core.contracts import ArtifactId, ProjectId
from noveltrad.core.exceptions import IntegrityError

_ZIP_DATE = (1980, 1, 1, 0, 0, 0)

_SLUG_BAD = re.compile(r"[^a-z0-9]+")


def slugify(name: str, project_id: ProjectId) -> str:
    """Slug per SDD 15.5: NFKD, strip marks, ASCII alphanumeric lowercase,
    collapse remaining sequences to '-', trim edge dashes, truncate to 80.
    Empty result falls back to noveltrad-<project_id>."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_BAD.sub("-", ascii_only).strip("-")[:80]
    if not slug:
        slug = f"noveltrad-{project_id}"
    return slug


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, _ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _validate_entry_name(name: str) -> None:
    if (
        not name
        or name.startswith("/")
        or ".." in name.split("/")
        or "\\" in name
        or any(ord(c) < 32 for c in name)
    ):
        raise IntegrityError(f"unsafe ZIP entry name: {name}")


def build_archive(
    artifact_id: ArtifactId,
    markdown_name: str,
    markdown_bytes: bytes,
    images: list[tuple[str, bytes]],
) -> io.BytesIO:
    """Build the ZIP in memory with deterministic ordering."""
    _validate_entry_name(markdown_name)
    seen: set[str] = set()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_zip_info(markdown_name), markdown_bytes)
        seen.add(markdown_name)
        for name, payload in sorted(images, key=lambda item: item[0]):
            _validate_entry_name(name)
            if name in seen:
                raise IntegrityError(f"duplicate ZIP entry: {name}")
            archive.writestr(_zip_info(name), payload)
            seen.add(name)
    return buffer


def read_images(data_dir: Path, relative_dir: str) -> list[tuple[str, bytes]]:
    """Collect images/<sha256>.webp from the project directory."""
    base = data_dir / relative_dir
    images_dir = base / "images"
    if not images_dir.exists():
        return []
    result: list[tuple[str, bytes]] = []
    for file in sorted(images_dir.glob("*.webp")):
        result.append((f"images/{file.name}", file.read_bytes()))
    return result

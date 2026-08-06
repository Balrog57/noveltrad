"""Import limits (SDD 10.6). All evaluated before allocation and
cumulatively during reading."""

from __future__ import annotations

MAX_BATCH_FILES = 100
MAX_BATCH_BYTES = 512 * 1024 * 1024  # 512 Mio
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000
MAX_MEMBER_BYTES = 256 * 1024 * 1024  # 256 Mio per decompressed member
MAX_TOTAL_DECOMPRESSED = 1024 * 1024 * 1024  # 1 Gio
MAX_RATIO = 100  # uncompressed/compressed per member and total
MAX_XML_BYTES = 64 * 1024 * 1024  # 64 Mio per XML/XHTML document
MAX_XML_DEPTH = 256
MAX_XML_NODES = 1_000_000
MAX_IMAGE_PIXELS = 50_000_000
MIN_FREE_SPACE = 1024 * 1024 * 1024  # 1 Gio floor
MIN_FREE_FACTOR = 2  # x announced decompressed size

SUPPORTED_EXTENSIONS = frozenset({"epub", "docx", "txt", "md", "srt"})

MAX_LINGUA_CHARS = 200_000

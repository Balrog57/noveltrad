"""OCR module (CDC Phase 3 — optional: PaddleOCR or Tesseract).

Implementation choice: Tesseract via pytesseract (simplest to install on
Windows, mature). The module degrades gracefully:

  - If pytesseract is not installed or the tesseract binary is not found,
    is_available() returns False and extract_text() raises OcrUnavailable.
    The UI uses is_available() to enable/disable the OCR button and shows
    install instructions when the user clicks it.

Install (Windows):
  1. Download the UB Mannheim build: https://github.com/UB-Mannheim/tesseract/wiki
  2. Default path C:\\Program Files\\Tesseract-OCR\\tesseract.exe is auto-detected.
  3. Or set the TESSERACT_CMD env var / config.json 'tesseract_cmd'.

CDC quote (Phase 3): 'Intégration OCR pour traduire du texte dans les
images/captures d'écran.'
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Windows default install location for the UB Mannheim Tesseract build.
_WINDOWS_DEFAULTS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


class OcrUnavailable(RuntimeError):
    """Raised when OCR is requested but Tesseract is not installed."""


def find_tesseract() -> str | None:
    """Locate the tesseract binary, or None if not found."""
    # 1. Explicit env var.
    env = os.environ.get("TESSERACT_CMD")
    if env and Path(env).exists():
        return env
    # 2. PATH lookup.
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    # 3. Windows default locations.
    if os.name == "nt":
        for cand in _WINDOWS_DEFAULTS:
            if Path(cand).exists():
                return cand
    return None


def is_available() -> bool:
    """True if both pytesseract (Python lib) and the tesseract binary are usable."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return find_tesseract() is not None


def extract_text(image_path: str | Path, lang: str | None = None) -> str:
    """Run OCR on an image file and return the extracted text.

    lang: a Tesseract language code, e.g. 'eng', 'fra', 'chi_sim', 'eng+fra'.
          Defaults to None (Tesseract default, usually 'eng').
    Raises OcrUnavailable if Tesseract is not installed.
    """
    cmd = find_tesseract()
    if cmd is None:
        raise OcrUnavailable(
            "Tesseract n'est pas installé. Installez-le (UB Mannheim build sur Windows) "
            "ou définissez TESSERACT_CMD. Voir la documentation OCR."
        )
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OcrUnavailable(
            "Dépendances OCR manquantes (Pillow/pytesseract). "
            "Installez-les avec: uv sync --extra ocr"
        ) from exc

    pytesseract.pytesseract.tesseract_cmd = cmd
    img = Image.open(image_path)
    kwargs = {"lang": lang} if lang else {}
    return pytesseract.image_to_string(img, **kwargs).strip()


def install_hint() -> str:
    """User-facing instructions shown when OCR is unavailable."""
    return (
        "OCR non disponible.\n\n"
        "Pour activer la traduction d'images :\n"
        "1. Installez Tesseract OCR (build UB Mannheim sur Windows) :\n"
        "   https://github.com/UB-Mannheim/tesseract/wiki\n"
        "2. Définissez le chemin si besoin : variable TESSERACT_CMD\n"
        "   ou champ 'tesseract_cmd' dans ~/.noveltrad/config.json\n"
        "3. Installez les dépendances Python : uv sync --extra ocr"
    )

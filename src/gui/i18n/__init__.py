"""i18n helpers for the PyQt6 desktop client.

This module is GUI-only and must NOT be imported from
``src/backend/``. The backend is locale-agnostic.

We use Qt Linguist's standard ``.ts``/``.qm`` workflow. English is
the source language (the canonical strings live in code, wrapped in
``self.tr(...)``). French ships as a pre-translated ``noveltrad_fr.ts``
shipped with the repo; additional languages can be added by dropping
a new ``noveltrad_<code>.ts`` next to it and running ``pylrelease6``.

If the corresponding ``.qm`` is missing (e.g. the developer's machine
that hasn't recompiled the catalogue), :func:`load_translator` is a
no-op and the app falls back to English.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

I18N_DIR = Path(__file__).resolve().parent

# Available UI languages. Each entry: (code, english_label, native_label).
# Keep this list aligned with the .qm files actually shipped.
AVAILABLE_LANGUAGES: list[tuple[str, str, str]] = [
    ("en", "English", "English"),
    ("fr", "French", "Français"),
]


def available_languages() -> list[tuple[str, str]]:
    """Return ``[(code, native_label), ...]`` for the Settings combobox."""
    return [(code, native) for code, _english, native in AVAILABLE_LANGUAGES]


def default_language() -> str:
    """Resolve the initial UI language from env or config.

    Falls back to ``"en"`` when nothing is configured. The ConfigManager
    is read defensively (the module is importable before QApplication
    has been created) — on any failure we silently default to English.
    """
    env_lang = os.environ.get("NOVELTRAD_LANGUAGE", "").strip().lower()
    if env_lang:
        return _normalise(env_lang) or "en"
    try:
        from ..app_config import ConfigManager  # local import to avoid cycle

        code = (
            str(
                (ConfigManager().config.get("ui", {}) or {}).get(
                    "language", "en"
                )
            )
            .strip()
            .lower()
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("i18n: config read failed (%s); defaulting to en", exc)
        return "en"
    return _normalise(code) or "en"


def _normalise(code: str) -> str:
    code = (code or "").strip().lower()
    if not code:
        return ""
    for entry in AVAILABLE_LANGUAGES:
        if code == entry[0]:
            return entry[0]
    # Map e.g. "fr-fr" → "fr".
    head = code.split("-", 1)[0].split("_", 1)[0]
    for entry in AVAILABLE_LANGUAGES:
        if head == entry[0]:
            return entry[0]
    return ""


def _qm_path(language: str) -> Optional[Path]:
    code = _normalise(language)
    if not code or code == "en":
        return None
    candidate = I18N_DIR / f"noveltrad_{code}.qm"
    if candidate.exists():
        return candidate
    return None


def load_translator(language: str):
    """Build a :class:`QTranslator` for ``language`` or return ``None``.

    The caller is responsible for installing it on the QApplication.
    The translator is loaded from the .qm compiled by pylrelease6.
    """
    try:
        from PyQt6.QtCore import QTranslator
    except ImportError:  # pragma: no cover - PyQt6 always present in GUI env
        return None
    qm = _qm_path(language)
    if qm is None:
        return None
    tr = QTranslator()
    if tr.load(str(qm)):
        logger.info("i18n: loaded translator %s", qm.name)
        return tr
    logger.warning("i18n: failed to load %s", qm)
    return None


def has_translation(language: str) -> bool:
    """True if a compiled translation is available for ``language``."""
    return _qm_path(language) is not None


__all__ = [
    "AVAILABLE_LANGUAGES",
    "available_languages",
    "default_language",
    "has_translation",
    "load_translator",
]

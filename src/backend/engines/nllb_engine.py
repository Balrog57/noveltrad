"""NLLB translation engine — wrapper around ctranslate2 + sentencepiece.

Loads an NLLB-200 distilled model (e.g. facebook/nllb-200-distilled-600M)
once and serves translation requests in subprocess-friendly form.

This is the *primary* fast translator for the v4 pipeline. The LLM
polisher uses the LiteLLM router instead (much slower but stylistically
better).

Language codes: NLLB uses BCP-47-like "eng_Latn", "fra_Latn", "zho_Hans"
etc. The engine accepts ISO-639-1 ("en", "fr", "zh") and maps them
internally.

Soft dependencies: ctranslate2 and sentencepiece are optional. In
production, missing NLLB is reported as unavailable; callers must
choose an explicit fallback such as LLM draft mode.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ISO-639-1 → NLLB code map. Covers the languages the GUI exposes.
_ISO_TO_NLLB: dict[str, str] = {
    "en": "eng_Latn",
    "fr": "fra_Latn",
    "es": "spa_Latn",
    "de": "deu_Latn",
    "it": "ita_Latn",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "ar": "arb_Arab",
    "hi": "hin_Deva",
    "id": "ind_Latn",
    "vi": "vie_Latn",
    "th": "tha_Thai",
    "tr": "tur_Latn",
    "pl": "pol_Latn",
    "nl": "nld_Latn",
    "uk": "ukr_Cyrl",
    "sv": "swe_Latn",
    "auto": "eng_Latn",
}


def to_nllb_code(lang: str) -> str:
    if not lang:
        return "eng_Latn"
    lang = lang.lower()
    if "_" in lang:
        return lang
    return _ISO_TO_NLLB.get(lang, lang)


def from_nllb_code(code: str) -> str:
    inv = {v: k for k, v in _ISO_TO_NLLB.items()}
    return inv.get(code, code)


class NLLBEngine:
    """Thread-safe NLLB wrapper. Heavy init runs once.

    Configuration via env / options dict:
        NLLB_MODEL  — local path or HF model id (default: facebook/nllb-200-distilled-600M)
        NLLB_QUANT  — int8 / int8_float16 / float16 / float32 (default: int8)
        NLLB_DEVICE — cpu / cuda / auto (default: auto)
    """

    def __init__(
        self,
        model: str | None = None,
        device: str = "auto",
        quant: str = "int8",
    ):
        self.model_name = model or os.environ.get(
            "NLLB_MODEL", "facebook/nllb-200-distilled-600M"
        )
        self.device = device or os.environ.get("NLLB_DEVICE", "auto")
        self.quant = quant or os.environ.get("NLLB_QUANT", "int8")
        self._translator = None
        self._sp = None
        self._sp_target = None
        self._lock = threading.Lock()
        self._load_error: str | None = None
        self._lazy_load()

    @property
    def available(self) -> bool:
        return self._translator is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def _lazy_load(self) -> None:
        try:
            import ctranslate2  # type: ignore
            import sentencepiece  # type: ignore
        except ImportError as exc:
            self._load_error = f"ctranslate2 / sentencepiece not installed: {exc}"
            logger.warning(
                "NLLBEngine unavailable: %s", self._load_error
            )
            return
        try:
            model_path = self._resolve_model_path()
            self._translator = ctranslate2.Translator(
                model_path,
                device=self.device,
                compute_type=self.quant,
            )
            self._sp = sentencepiece.SentencePieceProcessor()
            self._sp_target = sentencepiece.SentencePieceProcessor()
            self._sp.load(str(Path(model_path) / "sentencepiece.bpe.model"))
            self._sp_target.load(str(Path(model_path) / "sentencepiece.bpe.model"))
            logger.info(
                "NLLBEngine loaded: model=%s device=%s quant=%s",
                model_path,
                self.device,
                self.quant,
            )
        except Exception as exc:
            self._load_error = f"NLLB load failed: {exc}"
            logger.warning("NLLBEngine unavailable: %s", exc)
            self._translator = None

    def _resolve_model_path(self) -> str:
        # If the env points at a local dir, use it directly. Otherwise
        # require explicit opt-in for network downloads; a desktop app
        # should not silently pull a multi-GB model at worker startup.
        p = Path(self.model_name)
        if p.is_dir():
            return str(p)
        if os.environ.get("NLLB_ALLOW_DOWNLOAD", "0") not in {"1", "true", "yes"}:
            raise RuntimeError(
                "NLLB_MODEL must point to a local CTranslate2 model directory "
                "or NLLB_ALLOW_DOWNLOAD=1 must be set explicitly"
            )
        try:
            from huggingface_hub import snapshot_download  # type: ignore

            cache_dir = os.environ.get("NLLB_CACHE", str(Path.home() / ".cache" / "nllb"))
            path = snapshot_download(
                repo_id=self.model_name,
                cache_dir=cache_dir,
                allow_patterns=[
                    "*.bin",
                    "sentencepiece.bpe.model",
                    "config.json",
                    "tokenizer.json",
                ],
            )
            return path
        except Exception:
            # Final fallback: assume CTranslate2-compatible path
            return self.model_name

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_decoding_length: int = 256,
    ) -> str:
        if not text.strip():
            return text
        if "\n" in text:
            return self._translate_multiblock(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
                max_decoding_length=max_decoding_length,
            )
        if not self.available:
            if os.environ.get("NOVELTRAD_ALLOW_IDENTITY_TRANSLATION") in {
                "1",
                "true",
                "yes",
            }:
                logger.warning("Using explicit identity translation fallback")
                return f"[{from_nllb_code(to_nllb_code(target_lang))}] {text}"
            raise RuntimeError(self._load_error or "NLLB engine unavailable")
        with self._lock:
            try:
                src_code = to_nllb_code(source_lang)
                tgt_code = to_nllb_code(target_lang)
                tokens = self._sp.encode(text.strip(), out_type=str)  # type: ignore[union-attr]
                source_tokens = [src_code, *tokens, "</s>"]
                results = self._translator.translate_batch(  # type: ignore[union-attr]
                    [source_tokens],
                    batch_type="tokens",
                    target_prefix=[[tgt_code]],
                    beam_size=4,
                    max_decoding_length=max_decoding_length,
                )
                out_tokens = results[0].hypotheses[0]
                # Strip the language token at the start
                if out_tokens and out_tokens[0] == tgt_code:
                    out_tokens = out_tokens[1:]
                return self._sp_target.decode(out_tokens)  # type: ignore[union-attr]
            except Exception as exc:
                logger.exception("NLLB translate failed")
                return text

    def _translate_multiblock(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_decoding_length: int,
    ) -> str:
        """Translate paragraph-like blocks separately while preserving spacing."""
        parts = re.split(r"(\n\s*\n+)", text)
        translated: list[str] = []
        for part in parts:
            if not part:
                continue
            if re.fullmatch(r"\n\s*\n+", part):
                translated.append(part)
                continue
            if not part.strip():
                translated.append(part)
                continue
            leading = part[: len(part) - len(part.lstrip())]
            trailing = part[len(part.rstrip()) :]
            core = part.strip()
            translated.append(
                leading
                + self.translate(
                    core,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    max_decoding_length=max_decoding_length,
                )
                + trailing
            )
        return "".join(translated)

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[str]:
        return [self.translate(t, source_lang, target_lang) for t in texts]


# Module-level singleton — one model per process.
_singleton: NLLBEngine | None = None
_singleton_lock = threading.Lock()


def get_engine() -> NLLBEngine:
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = NLLBEngine()
    return _singleton


def diagnostics() -> dict[str, Any]:
    """Cheap readiness check that does not download or load the model."""
    model_name = os.environ.get("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
    try:
        import ctranslate2  # noqa: F401
        import sentencepiece  # noqa: F401
    except ImportError as exc:
        return {
            "available": False,
            "model": model_name,
            "reason": f"ctranslate2/sentencepiece missing: {exc}",
        }
    p = Path(model_name)
    if not p.is_dir():
        return {
            "available": False,
            "model": model_name,
            "reason": "NLLB_MODEL is not a local CTranslate2 directory",
        }
    spm = p / "sentencepiece.bpe.model"
    return {
        "available": spm.exists(),
        "model": str(p),
        "reason": "" if spm.exists() else "sentencepiece.bpe.model missing",
    }


__all__ = [
    "NLLBEngine",
    "diagnostics",
    "get_engine",
    "to_nllb_code",
    "from_nllb_code",
]

"""Prompt loading (SDD 11.11).

The normative bundle `prompts/v1` contains 01_translate.txt, 02_revise.txt,
03_context.txt and 04_polish.txt. Each file concatenates the common preamble
and exactly one pass instruction. Prompts are resources loaded by stage id
with only allowed named substitutions.
"""

from __future__ import annotations

from pathlib import Path

from noveltrad.core.contracts import PipelineStage
from noveltrad.core.exceptions import ValidationError

_BUNDLE_DIR = Path(__file__).resolve().parent / "prompts"

_STAGE_FILES = {
    PipelineStage.TRANSLATE: "01_translate.txt",
    PipelineStage.REVISE: "02_revise.txt",
    PipelineStage.CONTEXT: "03_context.txt",
    PipelineStage.POLISH: "04_polish.txt",
}


class PromptLoader:
    def __init__(self, bundle_version: str = "v1", base_dir: Path | None = None) -> None:
        if bundle_version != "v1":
            raise ValidationError(f"unknown prompt bundle version: {bundle_version}")
        self._base = base_dir or _BUNDLE_DIR / bundle_version

    def load(self, stage: PipelineStage) -> str:
        filename = _STAGE_FILES.get(stage)
        if filename is None:
            raise ValidationError(f"no prompt for stage {stage}")
        path = self._base / filename
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValidationError(f"prompt resource missing: {filename}") from exc

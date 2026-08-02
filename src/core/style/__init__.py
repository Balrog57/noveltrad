"""
Style extraction and assembly (Phase 3 of the style-extraction plan).

Provides:
- dimensions: the closed list of style dimensions
- lint: conservative abstraction-violation detector for rule instructions
- extractor: parse an LLM response into a validated rule list, and run
  the extraction prompt against a provider
- assembler: turn a rule list into the translation/refinement prose blocks
"""
from src.core.style.assembler import assemble_instructions
from src.core.style.dimensions import ALLOWED_DIMENSIONS, DEFAULT_DIMENSION
from src.core.style.extractor import extract_style, parse_style_response
from src.core.style.lint import lint_instruction

__all__ = [
    "ALLOWED_DIMENSIONS",
    "DEFAULT_DIMENSION",
    "assemble_instructions",
    "extract_style",
    "parse_style_response",
    "lint_instruction",
]

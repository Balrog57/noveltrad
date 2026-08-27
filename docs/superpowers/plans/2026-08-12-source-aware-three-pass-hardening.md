# Source-Aware Three-Pass Refinement Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the provider configuration and make the three-pass refinement pipeline source-aware, history-aware, structurally safe, and resumable.

**Architecture:** Introduce an aligned refinement-segment state at the format adapter boundary. The shared three-pass loop consumes source/current/history and persists a phase-aware checkpoint after each successful segment. Provider clients receive the complete runtime configuration through `create_llm_client`.

**Tech Stack:** Python 3, asyncio, httpx, pytest, existing CheckpointManager, TXT/Markdown, EPUB/DOCX placeholder validators, SRT indexed blocks.

## Global Constraints

- Refinement after translation and refine-only execute exactly three refinement passes.
- The original source is immutable input to every pass.
- Pass 3 must receive the same segment's initial translation and all prior revisions.
- A rate-limit or interruption must resume at the saved phase/segment boundary.
- Do not expose API keys in logs, checkpoints, or prompts beyond existing behavior.
- Preserve the current one-pass internal path when `four_pass_refinement` is false.

---

### Task 1: Provider runtime configuration

**Files:**
- Modify: `src/core/llm_client.py:166-224`
- Modify: `src/core/llm/providers/xai.py:7-16`
- Modify: `src/core/llm/providers/anthropic.py:13-100`
- Modify: `src/api/blueprints/translation_routes.py:51-92`
- Test: `tests/unit/test_provider_runtime_configuration.py`

**Interfaces:**
- `create_llm_client(..., api_endpoint, context_window, log_callback)` passes all three values to every cloud provider.
- OpenAI-compatible provider constructors accept those values without changing existing call sites.
- `_ENDPOINT_CONSUMING_PROVIDERS` includes `anthropic`, `xai`, and `opencode`.

- [x] **Step 1: Write failing tests** for endpoint/context/log propagation and endpoint override recognition.
- [x] **Step 2: Run the focused tests and verify they fail because the values are dropped.
- [x] **Step 3: Pass the values through the wrapper and constructors.
- [x] **Step 4: Run the focused tests and verify they pass.
- [x] **Step 5: Add an Anthropic response test proving `stop_reason=max_tokens` sets `was_truncated=True`.
- [x] **Step 6: Implement configurable output limit and truncation metadata.
- [x] **Step 7: Run provider tests plus existing provider configuration tests.

### Task 2: Explicit refinement segment state and prompt history

**Files:**
- Modify: `src/core/translator.py:1000-1110`
- Modify: `src/prompts/prompts.py:625-820`
- Modify: `src/core/refine/txt_refiner.py:100-190`
- Modify: `src/core/subtitle_translator.py:330-430`
- Modify: `src/core/epub/xhtml_translator.py:1440-1510`
- Test: `tests/unit/test_three_pass_source_and_history.py`

**Interfaces:**
- Refinement loop receives aligned `source_text`, `initial_translation`, and `current_translation`.
- Prompt receives `refinement_history: list[str]` for the same segment.
- Phase 3 is explicitly a minimal final arbitration, not an unconditional rewrite.

- [x] **Step 1: Write failing tests asserting each pass sees the source and same-segment history.
- [x] **Step 2: Run them and verify the current implementation supplies empty source/neighbor text as history.
- [x] **Step 3: Add a small segment-state structure and keep per-segment revision lists.
- [x] **Step 4: Update TXT, EPUB/DOCX, and SRT adapters to populate the aligned source/initial fields.
- [x] **Step 5: Update prompt construction and phase instructions.
- [x] **Step 6: Run the focused history tests and existing refinement tests.

### Task 3: Phase-aware checkpoint and interruption semantics

**Files:**
- Modify: `src/core/adapters/refine_file.py:15-120`
- Modify: `src/core/translator.py:1020-1095`
- Modify: `src/core/refine/txt_refiner.py:70-200`
- Modify: `src/core/epub/xhtml_translator.py:760-920`
- Modify: `src/core/subtitle_translator.py:520-830`
- Test: `tests/unit/test_three_pass_checkpoint_resume.py`

**Interfaces:**
- Checkpoint payload contains `phase`, `next_segment`, `source_hash`, `model`, `prompt_version`, `initial`, `current`, and `history`.
- Resume validates identity fields and continues without re-running completed phases.
- User interruption raises/returns an interruption result; rate limits remain rate-limit results.

- [x] **Step 1: Write failing tests for a pause after pass 2 segment N and for user interruption classification.
- [x] **Step 2: Run them and verify the current checkpoint either lacks phase data or restarts from pass 1.
- [x] **Step 3: Persist the refinement state after each successful segment and load it before the loop.
- [x] **Step 4: Forward checkpoint arguments from `refine_file` to every format refiner.
- [x] **Step 5: Separate interruption handling from `RateLimitError`.
- [x] **Step 6: Run focused resume tests and existing checkpoint tests.

### Task 4: Structural guards and safe output writes

**Files:**
- Modify: `src/core/refine/txt_refiner.py:100-190`
- Modify: `src/core/epub/xhtml_translator.py:1410-1555`
- Modify: `src/core/subtitle_translator.py:370-430`
- Test: `tests/unit/test_refinement_structure_guards.py`

**Interfaces:**
- TXT/Markdown validation rejects changed fenced-code count, link destination count, heading/list marker count, or placeholder set.
- EPUB/DOCX retains prior valid text on placeholder mismatch.
- SRT retains timestamps/indices and falls back per block on malformed output.

- [x] **Step 1: Write failing tests for Markdown structural drift and EPUB chunk-length mismatch.
- [x] **Step 2: Run them and verify invalid refinements are currently accepted or truncated by `zip`.
- [x] **Step 3: Add deterministic signatures and fallback behavior.
- [x] **Step 4: Replace silent `zip` truncation with an explicit mismatch error and safe fallback.
- [x] **Step 5: Run structure tests and format characterization tests.

### Task 5: Regression, documentation, and release validation

**Files:**
- Modify: `docs/PROVIDERS.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Test: all relevant existing tests and the full test suite.

- [x] **Step 1: Add provider and refinement troubleshooting notes, including resume behavior.
- [x] **Step 2: Run `git diff --check`.
- [x] **Step 3: Run focused provider/refinement tests.
- [x] **Step 4: Run `pytest -q` and record the complete result.
- [x] **Step 5: Run `python -m compileall src`.
- [x] **Step 6: Inspect the final diff for accidental secrets, generated files, and unrelated changes.

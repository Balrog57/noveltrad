# Source-Aware Three-Pass Refinement Hardening

> **Obsolete.** NovelTrad refine is a single one-pass Hy-MT2/Chimera Automatic
> Post-Editing call per segment. See `NovelTrad_SDD.md` §2. Do not implement
> this three-pass / four-pass design.

## Goal

Make the three-pass refinement workflow truthful and resumable for TXT/Markdown, EPUB/DOCX, and SRT while making Anthropic, xAI, and OpenCode use the configured provider settings.

## Architecture

The refinement engine will operate on an explicit segment record containing the source text, initial translation, current draft, and all revisions for that same segment. Each pass will read the record and write a new version; neighboring segments remain separate context only. A phase-aware checkpoint stores the segment records and resumes at the exact pass/segment boundary after rate limits or interruption.

Provider construction will use one common configuration path for endpoint, context window, logging, and credentials. OpenAI-compatible providers will inherit the existing retry/key-pool behavior; Anthropic will expose the same operational metadata and mark `max_tokens` responses as truncated.

## Data flow

1. Translation/refine-only adapters build aligned `(source, initial_translation)` segment records.
2. Pass 1 checks source fidelity, omissions, terminology, and structural invariants.
3. Pass 2 checks grammar, local coherence, dialogue, and style without changing facts.
4. Pass 3 arbitrates using the source and every earlier version, applying only justified changes.
5. The adapter validates structure, persists a checkpoint, and writes output atomically.

## Error handling and recovery

- User interruption is distinct from rate-limit failure.
- A checkpoint records `phase`, `next_segment`, source hash, model, prompt version, current text, and revision history.
- Resume rejects stale checkpoints whose source hash/model/prompt version no longer match.
- A failed or structurally invalid refinement keeps the last valid version.
- Provider errors preserve HTTP status/category in logs; truncated responses are not accepted as final without retry/fallback.

## Provider contract

All providers receive `api_endpoint`, `context_window`, and `log_callback`. Refinement calls can provide deterministic generation controls (`temperature`, `top_p`, `max_tokens`) where the provider supports them. Unknown providers still fail explicitly with `ValueError`.

## Structure protection

EPUB/DOCX placeholder validation and SRT index/timestamp isolation remain mandatory. TXT/Markdown gains a lightweight structural signature check for headings, fenced code, links, list markers, and placeholder tokens; invalid output falls back to the previous valid draft.

## Compatibility

The internal one-pass path remains available when `four_pass_refinement` is false. Public refine-only/refine-after paths use exactly three refinement passes, as required by the product decision.

## Verification

Tests must prove source propagation, same-segment revision history, phase-aware resume, interruption classification, provider endpoint propagation, Anthropic truncation, structural fallback, and the existing full suite.

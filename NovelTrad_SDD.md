# TBL fork — NovelTrad scope

This repository remains a direct fork of `hydropix/TranslateBooksWithLLMs`. All
upstream features, UI, branding, attribution, formats, and tests are kept. This
document specifies only the functional deltas of the fork.

## 1. Extra providers

Add the following native providers at the same extension points as existing TBL
providers:

| Id | Vendor | Credential | API |
|---|---|---|---|
| `anthropic` | Anthropic / Claude | `ANTHROPIC_API_KEY` | Anthropic Messages API |
| `xai` | xAI / Grok | `XAI_API_KEY` | OpenAI-compatible |
| `opencode` | OpenCode Zen | `OPENCODE_API_KEY` | OpenAI-compatible Chat Completions |
| `opencodego` | OpenCode Go | `OPENCODE_GO_API_KEY` (fallback `OPENCODE_API_KEY`) | OpenAI-compatible Chat Completions |
| `ollamacloud` | Ollama Cloud | `OLLAMA_CLOUD_API_KEY` (fallback `OLLAMA_API_KEY`) | OpenAI-compatible Chat Completions |
| `chatgpt` | ChatGPT (OAuth) | none (`data/chatgpt_oauth.json`) | Codex Responses API |

Each provider must work from the CLI, the web UI, connection tests, model
loading, glossary/style paths, and resume. Comma-separated multi-keys, 429
rotation, normalized errors, endpoint validation, and non-persistence of
secrets follow the rules already present in TBL.

Default endpoints:

- Anthropic: `https://api.anthropic.com/v1` with `POST /messages` and `GET /models`.
- xAI: `https://api.x.ai/v1` with `POST /chat/completions` and `GET /models`.
- OpenCode Zen: `https://opencode.ai/zen/v1` with `POST /chat/completions` and `GET /models`.
- OpenCode Go: `https://opencode.ai/zen/go/v1` with the same contract. An empty Go
  key falls back to `OPENCODE_API_KEY`.
- Ollama Cloud: `https://ollama.com/v1` with `POST /chat/completions` and `GET /models`.
  Do not inherit the local Ollama endpoint field.
- ChatGPT: device-code OAuth, tokens in `data/chatgpt_oauth.json`, no API key.
  Models are listed from `GET /backend-api/codex/models`. Completions use
  streamed `POST /backend-api/codex/responses`.

OpenCode Zen/Go only route Chat Completions models (DeepSeek, Kimi, GLM,
MiniMax, and similar). GPT (`/responses`), Claude (`/messages`), and Gemini
through Zen/Go are out of scope.

Model lists must be fetched from the provider when the API allows it, with a
short documented fallback list. The web UI selects models from the dropdown;
it does not require typing a model id for these providers.

## 2. Automatic Post-Editing (Refine and Refine+)

Plain translation stays unchanged. Refine and Refine+ are mutually exclusive
product modes; they are never chained. Neither product path sets
`prompt_options.refine`, so EPUB/DOCX/SRT never run an in-pipeline refine and
then a second `refine_file` pass.

Placeholders, tags, timecodes, and format structure must be preserved. If a
structure guard fails after a Refine+ pass, the previous draft is kept.

### 2.1 One-pass Refine (APE)

When the user enables Refine, the pipeline is two steps:

1. **Translation** — existing TBL pass (`translate_file`).
2. **APE** — one source-aware Hy-MT2/Chimera Automatic Post-Editing call per
   segment via `refine_file`, with the original input as `source_filepath`.

`--refine-only` (web Refine-only / CLI `--refine-only`) runs step 2 on an
already translated file. Translate+refine on the web uses `refine_after`; the
CLI `--refine` flag translates, then calls `refine_file`.

Checkpoints store one-pass state (`version: 1`, `phase` remains `1` as a
vestigial field, plus `next_segment` / `current`). An interruption or
rate-limit keeps artefacts already produced and resumes at the current segment
without replaying finished work.

Web progress exposes two phases for Translate + Refine and one phase for
Refine-only.

### 2.2 Refine+ (four LLM passes + automatic QA)

Refine+ is a distinct mode on the same `refine_file` entrypoint, enabled by
`prompt_options.refine_plus`. CLI: `--refine-plus` / `--refine-plus-only`.
Web: `refine_plus_after` / `refine_plus_only`.

Per segment, in order:

1. **Pass 1 (LLM, temperature ~0.2)** — existing Chimera APE prompt plus
   faithfulness constraints (numbers, dates, units, names, placeholders).
   Operates on the already-translated draft, not a second from-scratch
   translation.
2. **Automatic QA (0 LLM)** — numbers/dates/units, placeholders, glossary
   hits, leftover source-script spans, length ratio.
3. **Pass 2 (LLM, temperature ~0.5)** — fluency and literary register.
   Translation-only output.
4. **Pass 3 (LLM, temperature ~0.2)** — glossary enforcement as JSON
   `{translation, changes, conflicts}`. Skipped when the segment has no
   glossary hits.
5. **Pass 4 (LLM, temperature ~0.2)** — grammar/typography as JSON
   `{final, edits}`.

JSON sidecars (`notes`, `changes`, `edits`, `omissions`) are logged only.
They are never written into the published file. `[[AMBIGUITY]]` markers are
stripped if a model emits them.

If automatic QA fails, at most **one** extra LLM call runs: Pass 1 again,
Pass 2, Pass 3, or the omission/addition JSON prompt (Stack Overflow template
Pass 4) with a micro-correction. There is no `max_iters=3` loop and no fifth
systematic pass.

Budget: Refine+-only = 4 LLM calls/segment (3 when glossary is a no-op).
Translate + Refine+ = 5. Worst case with the extra = +1.

Checkpoints use `version: 2` with `pass_index` (next pass 1–4), `extra_used`,
and `segment_current` so a TXT job can resume mid-pass.

### 2.3 Literary quality thresholds (runtime proxies)

Runtime does **not** use BERTScore, embeddings, or LM perplexity. Decisions
match the literary column of the source article via the proxies below.

| Article metric | Literary target | NovelTrad proxy | On failure |
|---|---|---|---|
| Semantic / fidelity | ≥ 0.80 | Numbers, dates, and units 100%; listed glossary names counted in the glossary row | Extra Pass 1, or omission QA when a source segment is present |
| Fluency | ≥ 0.90 | No leftover source-script span in a Latin-script target; structure guard OK | Extra Pass 2 (one iteration) |
| Glossary | ≥ 95% | `glossary_match_rate` on in-segment hits | Force Pass 3 |
| Entity preservation | 100% names/dates/numbers | Numbers/dates/units 100% (names ride with glossary ≥ 95%) | Extra Pass 1 |
| Omissions | 0 ideal; 0–1 non-factual tolerated | Factual: missing numbers = 0. Literary slack: `omission_count` ≤ 1 | Omission QA extra |
| Hallucinations | 0 factual additions | Extra numbers/names = 0 | Extra Pass 1 |
| BLEU / chrF | Offline only | Existing benchmark scripts; not a runtime gate | — |

Calibration (procedure only, not a v1 code deliverable): score 200–500
segments, inspect ~50 failures, adjust thresholds to limit useless extras;
repeat 2–3 cycles.

Out of scope for v1: BERTScore or sentence-transformers at runtime,
N-variants + rerank, `[[AMBIGUITY]]` / chain-of-thought in the published
file, persistent translation memory, human post-edit, a cheap QA model, a
dedicated FastAPI worker, a JSONL example bank, a distinct refine provider,
and rewriting the one-pass APE prompts.

## 3. Acceptance

- The fork is based on upstream TBL 1.5.9 with no other historical rewrite.
- The extra providers are usable from CLI and web UI with a normal
  `LLMResponse`, a model list, and tested errors.
- EPUB, TXT, DOCX, and SRT produce valid output for plain translation, for
  the one-pass APE refine path, and for Refine+.
- Tests prove there is no double refine, Refine and Refine+ are not combined,
  CLI/web parity for `--refine` / refine-after / `--refine-only` and the
  Refine+ flags, placeholder preservation, one-pass and Refine+ resume, and
  no regression on inherited TBL features.

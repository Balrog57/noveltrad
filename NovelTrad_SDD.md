# TBL fork — NovelTrad scope

This repository remains a direct fork of `hydropix/TranslateBooksWithLLMs`. All
upstream features, UI, branding, attribution, formats, and tests are kept. This
document specifies only the two functional deltas of the fork.

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

## 2. One-pass Automatic Post-Editing

Plain translation stays unchanged. When the user enables Refine, the pipeline
is two steps:

1. **Translation** — existing TBL pass (`translate_file`).
2. **APE** — one source-aware Hy-MT2/Chimera Automatic Post-Editing call per
   segment via `refine_file`, with the original input as `source_filepath`.

`--refine-only` (web Refine-only / CLI `--refine-only`) runs step 2 on an
already translated file. Translate+refine on the web uses `refine_after`; the
CLI `--refine` flag translates, then calls `refine_file`. Neither product path
sets `prompt_options.refine`, so EPUB/DOCX/SRT never run an in-pipeline refine
and then a second `refine_file` pass.

Placeholders, tags, timecodes, and format structure must be preserved.
Checkpoints store one-pass state (`phase` remains `1` as a vestigial field,
plus `next_segment` / `current`). An interruption or rate-limit keeps artefacts
already produced and resumes at the current segment without replaying finished
work.

Web progress exposes two phases for Translate + Refine and one phase for
Refine-only.

## 3. Acceptance

- The fork is based on upstream TBL 1.5.9 with no other historical rewrite.
- The extra providers are usable from CLI and web UI with a normal
  `LLMResponse`, a model list, and tested errors.
- EPUB, TXT, DOCX, and SRT produce valid output for plain translation and for
  the one-pass APE refine path.
- Tests prove there is no double refine, CLI/web parity for `--refine` /
  refine-after / `--refine-only`, placeholder preservation, one-pass resume,
  and no regression on inherited TBL features.

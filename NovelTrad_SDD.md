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

## 2. Four-pass refinement

Plain translation stays unchanged. When the user enables Refine, the full
pipeline is:

1. **Translation** — existing TBL pass.
2. **Context** — analyse each block with the previous and next block; output:
   consistency, terminology, and continuity suggestions.
3. **Correction** — spelling, grammar, punctuation, and flow of the draft;
   output: corrected text.
4. **Final** — generate the definitive text from the initial translation, pass 2
   suggestions, and the corrected text from pass 3.

Passes are strictly ordered and use the same provider and model. Placeholders,
tags, timecodes, and format structure must be preserved. `--refine-only` runs
passes 2–4 on an already translated file. Intermediate outputs stay inside
checkpoints and do not change the existing user flow.

Each pass is independently resumable at block level. An interruption or error
keeps artefacts already produced and resumes at the current pass and block
without replaying finished work. After retries are exhausted, the job stays
resumable and reports the failed pass and block.

Web progress exposes four phases for Translate + Refine and three phases for
Refine-only, while keeping the historical fields existing consumers need.

## 3. Acceptance

- The fork is based on upstream TBL 1.5.9 with no other historical rewrite.
- The extra providers are usable from CLI and web UI with a normal
  `LLMResponse`, a model list, and tested errors.
- EPUB, TXT, DOCX, and SRT produce valid output for plain translation and for
  the multi-pass refine path.
- Tests prove order 1→2→3→4, neighboring blocks, per-pass resume,
  `--refine-only`, placeholder preservation, and no regression on inherited TBL
  features.

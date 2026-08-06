# AgentTranslate (NovelTrad) — Architecture Guide

> Companion to `docs/CDC.txt` (the spec) and `AGENTS.md` (team workflow).
> This document describes the Python architecture: a 4-agent LangGraph pipeline
> driven by a PySide6 GUI, faithful to the Cahier des Charges.

---

## Layer model

```
┌─────────────────────────────────────────────────────────────────┐
│  GUI  (PySide6 / Qt 6)                                          │
│  src/gui/                                                       │
│    main_window.py   → double-pane + selector bar (F1.a/d)       │
│    inspector.py     → per-agent panel: CoT + edits + flags (F1.b)│
│    worker.py        → QThread running the LangGraph             │
│    tray.py          → System Tray icon (F3)                     │
│    hotkey.py        → pynput global Ctrl+Alt+T (F1.c)           │
│    overlay.py       → selection capture → translate → paste (F3.c)│
│    settings_dialog.py → provider/model/tone config              │
│  Rule: GUI threads off all LLM work to worker.py (QThread).     │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │  Qt Signals: step_completed / stage_output
                          │             / translation_finished / error
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  CORE PIPELINE  (LangGraph StateGraph)                          │
│  src/core/                                                      │
│    state.py     → TranslationState TypedDict (CDC §2)           │
│    agents.py    → 4 nodes + 4 system prompts (CDC §3, verbatim) │
│    graph.py     → build_translation_graph() (expert)            │
│                   build_fast_graph()        (mode rapide, 1 agent)│
│    validators.py→ Pydantic models (CDC field names)             │
│    llm.py       → get_llm(): Ollama local | OpenAI-compatible   │
│    glossary.py  → load_glossary(): JSON flat-map / list / CSV   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  PERSISTENCE / CONFIG  (src/utils/)                             │
│    config.py   → Config singleton (~/.noveltrad/config.json)    │
│    history.py  → SQLite translation history (F3.a)              │
└─────────────────────────────────────────────────────────────────┘
```

**Dependency rule:** GUI depends on core; core depends on nothing in gui/. Both may use utils/.

---

## The 4-agent pipeline (CDC §3)

```
SOURCE → [1. translate] → [2. proofread] → [3. glossary] → [4. validate] → FINAL
```

| Node | CDC agent | Output (CDC field names) |
|---|---|---|
| `translator` | Draft Translator | raw text (`draft_translation`) |
| `proofreader` | Grammar & Style | `{corrected_text, edits_made[]}` |
| `glossary` | Context & Glossary | `{final_glossary_applied_text, glossary_matches[]}` |
| `validator` | Validator & Arbitrator | `{status, fidelity_score, final_text, flags[]}` |

**Critical design choice:** unlike the previous TS app (which *discarded* the validator's
output — see `docs/CDC_GAP_ANALYSIS.md` P0-1), here the validator's `final_text` **is** the
pipeline result, and its `flags`/`fidelity_score` feed the inspector panel (CDC integration tip).

LLM injection: `agents.set_llm()` (module-level holder). The worker calls it before
`graph.stream()`. Tests do the same with a `FakeChatModel`.

### Mode Rapide vs Mode Expert (CDC §5)
- **Expert** (default): full 4-agent `build_translation_graph()`.
- **Rapide**: `build_fast_graph()` — translator only (sub-3s target). Toggled in the UI.

---

## Conventions

### Prompts
The 4 system prompts in `core/agents.py` (`TRANSLATOR_SYSTEM`, `PROOFREADER_SYSTEM`,
`GLOSSARY_SYSTEM`, `VALIDATOR_SYSTEM`) are **verbatim from the CDC**. JSON example braces
are doubled (`{{ }}`) so `.format()` leaves them literal. Do not rewrap their long lines —
they are excluded from ruff's E501 via `pyproject.toml`.

### Validators
`core/validators.py` Pydantic models use **exactly** the CDC field names
(`corrected_text`, `edits_made`, `glossary_matches`, `fidelity_score`, `final_text`, `flags`).
If the CDC changes a schema, change it here — every node validates against it.

### LLM config (privacy-first)
`core/llm.py` `get_llm()` defaults to local Ollama. Remote (Groq/OpenRouter/DeepSeek/OpenAI)
is opt-in and requires an API key. The CSP-equivalent guarantee: no data leaves the machine
unless the user explicitly picks a remote provider in Settings.

---

## "Where does new code go?" cheat-sheet

| You're adding... | Put it in... |
|---|---|
| A new pipeline agent | a node fn in `core/agents.py` + prompt + edge in `graph.py` |
| A new CDC JSON schema field | the Pydantic model in `core/validators.py` |
| A new AI provider | `core/llm.py` (add to `REMOTE_PRESETS` or a dedicated provider) |
| A new glossary format | `core/glossary.py` |
| A new UI panel | a widget in `src/gui/` |
| A persisted setting | `utils/config.py` DEFAULTS + the settings dialog |
| A new history field | `utils/history.py` schema + `add_entry()` |

---

## Testing

- **Runner:** pytest (`uv run --extra dev pytest`).
- **Scope:** `core/` (state, agents, glossary, graph) is fully unit-tested with a fake LLM.
  GUI is verified by smoke test (instantiation) — `tests/` has no Qt widget tests yet.
- **Baseline:** 30 tests, 0 failures. Keep it green.
- **Lint:** `uv run --extra dev ruff check` (0 errors), `mypy` available.
- **Verify command:** `uv run --extra dev ruff check && uv run --extra dev pytest`

# 🤖 AgentTranslate (NovelTrad)

*Multi-Agent Desktop Translation — pipeline à 4 agents IA, 100% local, pilote par raccourci global.*

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![PySide6](https://img.shields.io/badge/PySide6-6.9+-41CD52?style=flat-square&logo=qt&logoColor=white)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-1C3C3C?style=flat-square)]()
[![Ollama](https://img.shields.io/badge/Ollama-local-blueviolet?style=flat-square)]()
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

> **TL;DR** — Sélectionnez du texte dans n'importe quelle app, pressez **Ctrl+Alt+T**, un
> pipeline de 4 agents IA le traduit et le remplace. Pipeline :
> Translate → Proofread → Glossary → Validate. 100% local (Ollama) par défaut.

Implémentation fidèle du **Cahier des Charges** (`docs/CDC.txt`).

---

## ✨ Fonctionnalités (CDC)

- 🤖 **Pipeline 4 agents** (LangGraph) — Translate, Proofread (grammaire+style), Glossary
  (terminologie), Validator (fidélité). Prompts verbatim du CDC, sorties JSON validées Pydantic.
- 🪟 **UI double-pane** (PySide6) — source à gauche, traduction à droite, inspecteur des agents à droite.
- 🔍 **Panneau d'inspection** — CoT, `edits_made`, `glossary_matches`, `flags` par agent, repliable (vue simplifiée).
- ⌨️ **Raccourci global `Ctrl+Alt+T`** — traduit la sélection courante de n'importe quelle app via un overlay.
- 🔁 **Remplacement auto** — capture (Ctrl+C) → traduit → colle (Ctrl+V).
- 📋 **Copie en un clic**, 📖 **glossaire JSON/CSV**, 🗂 **System Tray**, 📜 **historique SQLite**.
- ⚡ **Mode Rapide** (1 agent, < 3s) / **Mode Expert** (4 agents).
- 🏠 **100% local par défaut** — Ollama. APIs distantes (Groq/OpenRouter/DeepSeek) optionnelles.
- 🖼 **OCR (Phase 3)** — extrait le texte d'une image (Tesseract) puis le traduit.
- 📦 **Packagé en .exe** — build Windows natif via PyInstaller.

## 🛠 Stack

| Domaine | Choix |
|---|---|
| Langage | Python 3.13 |
| GUI | PySide6 (Qt 6) |
| Orchestration | LangGraph (StateGraph) |
| LLM local | Ollama (via `langchain-ollama`) |
| LLM distant | OpenAI-compatible (`langchain-openai`) |
| Validation | Pydantic v2 |
| Raccourcis globaux | pynput |
| Historique | sqlite3 (stdlib) |
| Packaging | uv + (PyInstaller) |
| Tests | pytest |
| Lint | ruff + mypy |

## 🚀 Quick Start

### Prérequis
- **Python 3.13** (LangGraph ne supporte pas 3.14 — Pydantic V1). uv l'installe pour vous.
- **[Ollama](https://ollama.com)** en cours d'exécution (`ollama serve`).
- **[uv](https://docs.astral.sh/uv/)** : `pip install uv`

### Installation

```bash
git clone https://github.com/Balrog57/noveltrad.git
cd noveltrad
uv sync                  # crée le venv Python 3.13 + installe les dépendances
uv run ollama pull qwen2.5:7b   # modèle recommandé
uv run python src/app.py # 🎉 l'app s'ouvre
```

### Utilisation

1. **Mode fenêtre** : collez du texte à gauche → « Traduire » → inspectez les 4 agents → copiez.
2. **Mode sélection** : dans n'importe quelle app, sélectionnez du texte → **Ctrl+Alt+T** → c'est traduit et remplacé.
3. **OCR** : bouton « 🖼 OCR Image… » → sélectionnez une image → le texte est extrait puis traduit (requiert Tesseract, voir ci-dessous).

### 📦 Packaging Windows (.exe)

```bash
uv run --extra dev pyinstaller noveltrad.spec --clean --noconfirm
# → dist/AgentTranslate/AgentTranslate.exe (onedir, ~15 MB exe + Qt6 DLLs)
```

### 🖼 OCR (CDC Phase 3 — optionnel)

L'OCR utilise Tesseract. Pour l'activer :

1. Installez [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (build UB Mannheim sur Windows).
2. Installez les dépendances Python : `uv sync --extra ocr`
3. Si le chemin n'est pas auto-détecté, définissez la variable `TESSERACT_CMD` ou le champ `tesseract_cmd` dans `~/.noveltrad/config.json`.

En l'absence de Tesseract, le bouton OCR est désactivé et affiche les instructions d'installation.

## 📖 Documentation

- **Cahier des Charges** : [`docs/CDC.txt`](docs/CDC.txt) (référence originale)
- **Analyse d'écart** (vs ancienne version TS) : [`docs/CDC_GAP_ANALYSIS.md`](docs/CDC_GAP_ANALYSIS.md)
- **Architecture** : [`ARCHITECTURE.md`](ARCHITECTURE.md)

## 🧪 Tests

```bash
uv run --extra dev pytest         # 30 tests (Vitest-like, LLM mocké)
uv run --extra dev ruff check     # linting (0 erreur)
```

## 🗂 Structure

```
noveltrad/
├── src/
│   ├── app.py               # Point d'entrée QApplication
│   ├── core/                # Pipeline LangGraph + prompts CDC verbatim
│   │   ├── agents.py        # 4 nœuds + 4 prompts système (CDC §3)
│   │   ├── graph.py         # StateGraph translator→proofread→glossary→validate
│   │   ├── state.py         # TranslationState TypedDict (CDC §2)
│   │   ├── validators.py    # Pydantic I/O (noms de champs CDC exacts)
│   │   ├── llm.py           # Ollama local + OpenAI-compatible distant
│   │   └── glossary.py      # Import JSON/CSV (flat-map {"bug":"anomalie"})
│   ├── gui/                 # PySide6 : fenêtre, inspecteur, tray, overlay, hotkey
│   └── utils/               # config JSON, historique SQLite
├── tests/                   # 30 tests pytest
└── docs/                    # CDC + analyse d'écart
```

## 📜 Licence

MIT © Balrog57

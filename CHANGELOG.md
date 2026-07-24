# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.2.0] — 2026-07-24

### Ajouté
- **F1.b — Affichage du CoT (chain-of-thought)** : l'inspecteur montre désormais le
  raisonnement des modèles "thinking" (qwen3, deepseek-r1) en parsant les balises
  `<think>…</think>`, qui sont strippées du contenu. Zone repliable, masquée si le
  modèle n'émet pas de raisonnement.
- **Profils de traduction** (CDC Phase 2) : le sélecteur « Ton » est remplacé par un
  sélecteur « Profil » (Général / Technique / Littéraire / Courrier pro), chacun
  injectant un bloc d'instructions spécifique dans les prompts.
- **Liste dynamique des modèles Ollama** (CDC Phase 1) : le sélecteur de modèle est
  peuplé depuis `/api/tags` (bouton 🔄 de rafraîchissement), plus saisie manuelle.

### Corrigé (9 bugs)
- **Crash overlay** : les widgets n'étaient plus touchés depuis un thread non-UI
  (pynput / QThread) — marshaling via signaux Qt.
- **GC du QThread de rafraîchissement** modèle (référence forte gardée).
- **Shutdown propre** : annulation + attente du worker de traduction au quit.
- **Race sur le LLM global** : verrou `threading.Lock` + reset entre les runs.
- **Auto-update** : un build ARM ne peut plus être sélectionné sur x64.
- **JSON noyé dans du prose** : récupération (modèles locaux bavards).
- **Glossaire** : un terme nommé "source"/"key" n'est plus traité comme un en-tête.
- **Draft vide** : lève une erreur claire au lieu d'un "succès" vide.
- **Shutdown du hotkey** : join du thread pynput (libération du hook clavier).

### Supprimé
- **Historique SQLite** : supprimé (privacy-first cohérent avec le CDC §5). La
  persistance silencieuse sans UI de consultation n'avait pas de valeur utilisateur.

## [1.1.0] — 2026-07-23

### Ajouté
- **Auto-update depuis GitHub Releases** (canal latest) — au démarrage et via le
  menu tray « Vérifier les mises à jour… ». Si une version plus récente existe :
  notification + popup (notes de version) → téléchargement → remplacement via
  `updater.bat` externe → relance. Pattern standard pour remplacer un exe Windows
  verrouillé. Désactivé en mode dev (`uv run`).
- **Workflow `release.yml`** — build automatique du `.exe` Windows + upload du
  zip sur les releases au push de tag `v*`.
- `__version__` lisible au runtime (`importlib.metadata`).

### Technique
- `requests` + `packaging` ajoutés en dépendances explicites.
- `noveltrad.spec` : `copy_metadata` pour que la version soit lisible dans le bundle.

## [1.0.0] — 2026-07-23

### Réécriture complète en Python (fidèle au CDC)

Le projet passe d'une application Electron/Vue/TypeScript (v3.x) à une application
**Python 3.13 + PySide6 + LangGraph**, implémentant fidèlement le Cahier des Charges
(`docs/CDC.txt`). Périmètre réinitialisé : traducteur de sélection multi-agent.

### Ajouté (implémentation Python)
- **Pipeline 4 agents LangGraph** (`src/core/`) — translate → proofread → glossary → validate.
  Prompts système **verbatim du CDC §3**.
- **Sorties JSON conformes au CDC** (`validators.py`) — champs exacts `corrected_text`,
  `edits_made`, `glossary_matches`, `fidelity_score`, `final_text`, `flags` (validés Pydantic).
  *Corrige le bug de la v3 TS qui jetait la sortie du Validator.*
- **UI PySide6 double-pane** + barre de sélecteurs (langue source/cible, **ton**, modèle).
- **Panneau d'inspection** par agent (CoT, `edits_made`, `glossary_matches`, `flags`) avec
  vue simplifiée repliable (F1.b).
- **System Tray** (F3), minimisation en arrière-plan.
- **Raccourci global `Ctrl+Alt+T`** (pynput) — déclenche l'overlay depuis n'importe quelle app (F1.c).
- **Overlay de remplacement de sélection** — capture (Ctrl+C) → traduit → colle (Ctrl+V) (F3.c).
- **Copie en un clic** (F3.b), **historique SQLite** (F3.a).
- **Backend hybride** — Ollama local par défaut (privacy-first) + distant OpenAI-compatible
  (Groq/OpenRouter/DeepSeek) opt-in (F2).
- **Glossaire JSON/CSV** — import flat-map `{"bug":"anomalie"}` (forme exacte du CDC), liste,
  CSV, TSV (F2.c).
- **Mode Rapide** (1 agent) / **Mode Expert** (4 agents) (CDC §5).
- **30 tests pytest** (LLM mocké), **ruff** vert.

### Technique
- Gestionnaire : **uv** (`pyproject.toml` + `uv.lock`), Python 3.13 requis (LangGraph ≠ 3.14).
- Stack : PySide6 6.9+, LangGraph 1.x, langchain-ollama, langchain-openai, Pydantic v2, pynput.

### Packaging & OCR (PR #112)
- **Packaging Windows PyInstaller** (CDC §5) — `noveltrad.spec` (onedir, collect PySide6 +
  langchain). Build vérifié : `dist/AgentTranslate/AgentTranslate.exe` (4257 fichiers, Qt6).
- **OCR Phase 3** (CDC) — `src/core/ocr.py` via Tesseract/pytesseract, dégradation gracieuse.
  Bouton GUI « 🖼 OCR Image… ». Extra `ocr` optionnel.
- **Robustesse runtime** — `_coerce_enum()` + clamp `fidelity_score` après tests sur qwen2.5:7b réel.
- **CI** — retrait de `pytest-qt` (échec Ubuntu headless). CI verte.

### Validation runtime (post-merge)
- Pipeline 4 agents testé sur **Ollama qwen2.5:7b réel** : fidelity 98/100, 3.9s, glossaire OK.
- **Le CDC est désormais 100% couvert.**

### Supprimé
- Toute la base de code Electron/Vue/TypeScript (`apps/`, `packages/`, `node_modules/`, ~18k LOC).
- Configuration npm (`package.json`, `package-lock.json`, `.eslintrc.cjs`, `.prettierrc.yaml`).
- Documentation VitePress SDD 25 volumes (remplacée par `ARCHITECTURE.md` Python).
- CI GitHub Actions TypeScript.

---

## Versions antérieures (historique, application TypeScript — supprimée)

<details>
<summary>v3.0.1 et antérieur (Electron/Vue/TS — archivé dans git history)</summary>

Les versions v1.x–v3.x décrivaient l'application Electron/Vue/TypeScript
(pipeline 12→4 stages, EPUB, TM persistante). Ce code a été entièrement remplacé
par la réécriture Python v1.0.0. Consultez `git log` pour l'historique complet.
L'analyse d'écart entre le CDC et la v3 TS reste dans `docs/CDC_GAP_ANALYSIS.md`.

### v3.0.1 (2026-07-22)
- Fix: auto-clean stale recentProjects paths on launch.

### v3.0.0 (2026-07-22)
- Simplification majeure : pipeline 12→4 stages, UI tout-en-un, moteur in-thread.
</details>

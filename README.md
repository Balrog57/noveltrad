# NovelTrad

Application de traduction assistée par ordinateur pour romans et web novels. Workflow multi-agent : on donne un texte, un orchestrateur enchaîne automatiquement traduction rapide, création de lexique, vérification qualité, correction et polissage, pour sortir un texte traduit de qualité aussi proche que possible de l'original.

Pour la réalisation des agents et de leurs patterns, on s'appuie sur les bonnes pratiques observées dans :

## Pourquoi ce projet

La traduction littéraire (romans, web novels) est un cas dur : un texte long avec des termes récurrents, des noms propres cohérents entre chapitres, un style à préserver, et un risque permanent que le modèle "fabrique" des passages. Aucune API unique ne coche toutes les cases.

**L'approche choisie** : un orchestrateur qui décompose le travail en agents spécialisés, chacun avec un rôle clair et un message protocolaire minimal. L'utilisateur donne un texte ; le système rend un texte traduit de qualité, aussi proche que possible de l'original, et le fait de façon traçable (reprise après crash, cache LLM, glossaire versionné).

## Sommaire

- [Workflow](#workflow)
- [Architecture](#architecture)
- [Les 9 agents](#les-9-agents)
- [L'interface](#linterface)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Premier lancement](#premier-lancement)
- [Utilisation](#utilisation)
- [Construire l'exécutable Windows](#construire-lexécutable-windows)
- [Structure du projet](#structure-du-projet)
- [Stockage et reprise](#stockage-et-reprise)
- [Inspirations et patterns](#inspirations-et-patterns)
- [Limitations connues](#limitations-connues)
- [Validation](#validation)

## Workflow

```
   Drop EPUB/DOCX/TXT/SRT
            │
            ▼
   ┌────────────────┐
   │     Parser     │  segmente en chunks de ~500 chars
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │ FastTranslator │  NLLB-200 local (rapide)
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │ LexiconBuilder │  LLM NER → glossaire
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │GlossaryApplier │  substitution déterministe
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │ConsistencyChk  │  RAG : compare avec voisins du chapitre
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │  QA Validator  │  two-pass anti-fabrication (priorités)
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │ GrammarProofer │  LanguageTool + Grammalecte
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │  LLM Polisher  │  Reflect → Improve
   └────────┬───────┘
            ▼
   ┌────────────────┐
   │   Assembler    │  reconstruit EPUB/DOCX/TXT/SRT
   └────────┬───────┘
            ▼
   Fichier traduit dans <project>/target/
```

L'orchestrateur coordonne l'enchaînement. Chaque étape publie un statut dans le State Store SQLite. L'utilisateur suit la progression en temps réel dans l'activity log.

## Architecture

Deux processus communiquant en HTTP + WebSocket :

```
┌──────────────────────────────────────────────────────────────────┐
│              PyQt6 Client (4 onglets, drop-zone)                 │
│  [Translate] [Settings] [Glossaries] [Files]                     │
│  ┌────────────────────────┐  ┌─────────────────────────────┐    │
│  │  Drop zone + Start     │  │  Activity log (live, WS)     │    │
│  │  Source/Target langs   │  │  ● LLM: ready                │    │
│  └────────────────────────┘  └─────────────────────────────┘    │
└────────────────────┬─────────────────────────────────────────────┘
                 HTTP + WebSocket
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (subprocess)                    │
│  Orchestrator + LiteLLM Router + State Store (SQLite + LanceDB)  │
│  9 agents subprocess : un agent = un sous-processus              │
└──────────────────────────────────────────────────────────────────┘
```

**Le backend et la GUI sont des processus séparés.** `main_qt.py` lance le serveur (`python -m src.backend.server --port 8765`) en arrière-plan et s'y connecte. La GUI ne fait qu'afficher — toute la complexité vit dans le backend.

Conséquences pratiques :
- Si l'UI plante, le pipeline continue ; relancer l'UI montre la progression en cours.
- Si le backend plante, le State Store SQLite survit : relancer le backend et appeler `GET /pipeline/state` récupère l'état.
- On peut piloter le pipeline depuis un autre client (curl, scripts) sans toucher à la GUI.

## Les 9 agents

Chaque agent tourne dans son propre sous-processus. Ils s'échangent des messages `{chunk_id, action}` via des queues `multiprocessing`. L'orchestrateur central est le seul à toucher le State Store (single-writer pour éviter la contention SQLite).

| # | Agent | Rôle | Moteur | Inspiré de |
|---|---|---|---|---|
| 1 | **Parser** | Découpe un fichier EPUB/DOCX/TXT/SRT en chunks de ~500 chars | Python | TBL (chunking) |
| 2 | **FastTranslator** | Traduction brute de chaque chunk | NLLB-200 (ctranslate2) local | TBL (rapide) |
| 3 | **LexiconBuilder** | Extrait les noms propres et termes récurrents | LLM (Ollama) | `deusyu/translate-book` (glossaire v2) |
| 4 | **GlossaryApplier** | Substitue les termes du lexique dans la traduction | Python (regex) | `deusyu/translate-book` |
| 5 | **ConsistencyChecker** | Compare la traduction avec les voisins du même chapitre (RAG) | TF-IDF + LLM | `deusyu/translate-book` (neighbor ±300) |
| 6 | **QAValidator** | Détecte fabrication / omission / structure / terminologie / registre | LLM two-pass | `senshinji/claude-translation-skill` |
| 7 | **GrammarProofer** | Corrections grammaticales et orthographe | LanguageTool + Grammalecte | standard QA |
| 8 | **LLMPolisher** | Boucle *Reflect → Improve* sur la traduction | LLM (Ollama) | `andrewyng/translation-agent` |
| 9 | **Assembler** | Reconstruit le fichier final EPUB/DOCX/TXT/SRT | Python | TBL (output identique au format d'entrée) |

**Statuts de chunk** : `parsed → fast_translated → glossary_applied → consistency_checked → qa_checked → grammar_checked → polished → assembled`, plus `waiting_for_human` et `error`.

**LiteLLM router** (interne au backend) : Ollama local par défaut, fallback OpenAI-compatible. Cache disque SHA-512 (pattern `oomol-lab/epub-translator`). Circuit breaker après 3 échecs. Sémaphore pour Ollama = 1 (leçon de TBL : Ollama ne scale pas en parallèle).

## L'interface

Quatre onglets, une drop zone, un activity log, un badge LLM. Inspiration directe de TBL — surface minimale, le reste vit dans le backend.

| Onglet | Rôle | Endpoint backend |
|---|---|---|
| **Translate** | Drop zone + langues + Start | `POST /projects` + `POST /pipeline/start` |
| **Settings** | Provider, modèle, parallel, paramètres NLLB | `config.json` local |
| **Glossaries** | Table source→target éditable, import/export JSON | `GET/PUT /lexicon/*` |
| **Files** | Liste des chunks, statut, bouton Assembler | `GET /chunks`, `POST /assemble` |

**Activity log** : stream temps réel via WebSocket (`/ws`). Affiche chaque transition d'agent, les erreurs, les requêtes HITL. Filtre texte + clic → ouvre la fenêtre détail du chunk.

**Popup HITL** : non bloquante. Quand un agent (consistency, polisher) émet une demande de confirmation humaine, la popup apparaît. Skipper ou répondre. Timeout 30 min → best-effort, ne bloque jamais.

## Prérequis

- **OS** : Windows 10/11 (cible principale), Linux/macOS possibles (non testés).
- **Python** : 3.10+ (3.11 recommandé).
- **Pour la traduction rapide locale** : 4 GB RAM libres (modèle NLLB-200-distilled-600M). GPU CUDA optionnel.
- **Pour le polisher LLM** : soit [Ollama](https://ollama.com/download) installé avec un modèle (par défaut `gemma3:4b`), soit une clé API OpenAI-compatible (OpenAI, OpenRouter, LM Studio, vLLM…).

## Installation

```powershell
git clone https://github.com/Balrog57/noveltrad.git
cd noveltrad

python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt

# Optionnel : modèle Ollama local pour le polisher
ollama pull gemma3:4b
```

**Dépendances principales** : `PyQt6`, `fastapi`, `uvicorn`, `ctranslate2`, `sentencepiece`, `ebooklib`, `beautifulsoup4`, `python-docx`, `language-tool-python`. Optionnels : `lancedb` (RAG vectoriel), `pygrammalecte` (grammaire FR), `argostranslate`, `huggingface_hub` (téléchargement NLLB à la demande). Les dépendances optionnelles sont chargées en try/except — leur absence dégrade les fonctionnalités au fallback (TF-IDF, passthrough).

## Premier lancement

```powershell
python src/main_qt.py
```

1. Premier démarrage → **FirstRunWizard** (dossier de travail, langue par défaut).
2. Le backend est lancé en sous-processus sur le port 8765. La GUI attend la connexion (quelques centaines de ms) puis affiche le badge LLM.
3. Ouvrir **Settings** pour configurer le provider LLM :
   - Défaut : `Ollama`, base URL `http://127.0.0.1:11434`, modèle `gemma3:4b`.
   - Cloud : clé API OpenAI-compatible, base URL, modèle.
4. Les changements de settings prennent effet au prochain démarrage du backend.

## Utilisation

### Démarrer une traduction

1. Onglet **Translate**.
2. Choisir la langue source et la langue cible.
3. Glisser-déposer un `.epub` / `.docx` / `.txt` / `.srt` dans la drop zone (ou **Browse Files**).
4. Cliquer **▶ Start Translation Batch**.
5. Suivre la progression dans l'**Activity Log**.
6. **Files** liste les chunks avec leur statut. Double-clic → détail (source + traductions intermédiaires + issues).
7. Quand tous les chunks sont `polished`, le **Assembler** reconstruit le fichier dans `<project_dir>/target/`. Bouton **Assemble output…** pour choisir l'emplacement.

### Gérer le glossaire

Onglet **Glossaries** → table éditable, ajouter/supprimer/éditer des termes, **Import JSON** / **Export JSON** pour partager entre projets. Le pipeline auto-alimente le glossaire au fil de l'eau (LexiconBuilder) ; l'utilisateur peut ensuite valider les entrées.

### Répondre à une demande HITL

Quand un agent émet une demande, la popup non bloquante apparaît. Répondre ou Skipper. Le pipeline ne reste jamais bloqué (timeout 30 min).

### Lancer le backend seul (sans GUI)

Utile pour scripter ou utiliser un autre client HTTP :

```powershell
python -m src.backend.server --host 127.0.0.1 --port 8765
```

Endpoints REST :

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Statut du backend |
| `POST` | `/projects` | Créer un projet et démarrer la traduction |
| `GET` / `POST` | `/pipeline/{start,pause,resume,stop,state}` | Contrôle global |
| `GET` | `/chunks[?status=X]` | Liste des chunks |
| `GET` | `/chunks/{id}` | Détail chunk (toutes les traductions intermédiaires) |
| `POST` | `/chunks/{id}/reprocess` | Relancer un chunk |
| `GET` / `POST` / `PUT` / `DELETE` | `/lexicon[/{id}]` | Glossaire |
| `POST` | `/lexicon/import` / `GET /lexicon/export` | I/O glossaire |
| `GET` / `POST` | `/hltl/pending` / `/hltl/respond` | HITL |
| `WS` | `/ws` | Stream temps réel (log, progress, hltl_alert, agent_done) |

## Construire l'exécutable Windows

```powershell
python build_script.py
```

PyInstaller avec `build.spec` → `dist/NovelTrad/NovelTrad.exe`. Le spec inclut les modules `src.backend.*` en `hiddenimports` pour que la GUI puisse spawner le backend comme sous-processus dans l'exe gelé.

Pour un installateur Windows classique : installer [Inno Setup 6](https://jrsoftware.org/isdl.php), puis `ISCC.exe NovelTrad.iss` → `Output/NovelTrad_Setup.exe`.

## Structure du projet

```
src/
├── main_qt.py                # Entrypoint GUI (spawn backend + lance MainWindow)
├── backend/                  # FastAPI + orchestrateur + agents
│   ├── server.py             # App FastAPI + CLI (`python -m src.backend.server`)
│   ├── orchestrator/
│   │   ├── state_store.py    # SQLite + optional LanceDB
│   │   ├── pipeline.py       # Topologie 9 stages
│   │   ├── worker_manager.py # Multiprocessing subprocess lifecycle
│   │   └── orchestrator.py   # Drain loop, HITL, listeners, auto-assemble
│   ├── agents/
│   │   ├── base_worker.py    # Boucle commune
│   │   ├── parser.py
│   │   ├── fast_translator.py
│   │   ├── lexicon_builder.py
│   │   ├── glossary_applier.py
│   │   ├── consistency_checker.py
│   │   ├── qa_validator.py
│   │   ├── grammar_proofer.py
│   │   ├── llm_polisher.py
│   │   └── assembler.py
│   ├── llm_router/
│   │   └── router.py         # Ollama + OpenAI-compat, cache SHA-512, circuit breaker
│   ├── engines/
│   │   └── nllb_engine.py    # Wrapper ctranslate2 (fallback identité)
│   └── formats/
│       └── __init__.py       # EPUB/DOCX/TXT/SRT + chunker déterministe
├── gui/                      # Client PyQt6
│   ├── main_window.py        # Coquille + 4 onglets + badge LLM + activity log
│   ├── backend_client.py     # HTTP + WebSocket natifs (urllib, pas de httpx)
│   ├── tabs/                 # translate / settings / glossaries / files
│   ├── widgets/activity_log.py
│   └── dialogs/              # hitl_popup / chunk_detail_dialog
├── core/                     # Legacy v3 (TM, glossaires, segmenter…)
├── engines/                  # Legacy v3
├── formats/                  # Legacy v3
└── utils/
```

Le code v4 vit sous `src/backend/`. La GUI v4 ne dépend pas du code v3 sous `core/`, `engines/` racine, `formats/` racine.

## Stockage et reprise

- **State Store SQLite** : `<output_dir>/.pipeline_state.db` (tables `chunks`, `lexicon_terms`, `qa_issues`, `grammar_issues`, `consistency_flags`, `pipeline_state`). Créé à la première utilisation.
- **Cache LLM** : `~/.cache/noveltrad_llm/cache.json` (SHA-512 → réponse). Réutilisé entre runs.
- **Vecteurs (optionnel)** : `<output_dir>/.vectors` (LanceDB). Si non installé, fallback TF-IDF automatique.
- **Config utilisateur** : `config.json` à la racine (gitignoré). Contient chemins, clés API, choix de provider.

**Reprise après crash** : tuer le backend, relancer la GUI, le backend redémarre, `GET /pipeline/state` retourne l'état complet. Les chunks qui n'ont pas atteint `polished` sont automatiquement réinjectés.

## Inspirations pour la réalisation

Le tableau ci-dessous résume les patterns techniques repris pour implémenter chaque agent, point par point.

| Projet de référence | Pattern repris | Implémenté dans |
|---|---|---|
| [hydropix/TranslateBooksWithLLMs](https://github.com/hydropix/TranslateBooksWithLLMs) | UI drop-zone, activity log live, badge modèle, parallélisme Ollama=1, formats TXT/EPUB/SRT/DOCX | GUI v4 + LiteLLM router (sémaphore Ollama=1) + format handlers |
| [andrewyng/translation-agent](https://github.com/andrewyng/translation-agent) | Boucle *Translate → Reflect → Improve* | LLMPolisher (deux appels LLM : réflexion puis amélioration) |
| [senshinji/claude-translation-skill](https://github.com/senshinji/claude-translation-skill) | QA two-pass anti-fabrication, priorité *FABRICATION > OMISSION > STRUCTURE > TERMINOLOGY > REGISTER* | QAValidator |
| [oomol-lab/epub-translator](https://github.com/oomol-lab/epub-translator) | Cache LLM à content-hash | LiteLLM router (SHA-512 sur prompt + modèle + version) |
| [deusyu/translate-book](https://github.com/deusyu/translate-book) | Glossaire v2 (aliases, gender, evidence_refs), neighbor context ±300 chars | LexiconBuilder + GlossaryApplier + ConsistencyChecker |

**Différences assumées** vs les projets sources :
- vs TBL : web app Flask → on garde **PyQt6** (contrainte du projet). Multi-agent au lieu d'un agent monolithique.
- vs andrewyng : pas de balises `<TRANSLATE_THIS>` dans le prompt, le contexte est passé en bloc de neighbor chunks.
- vs senshinji : la seconde passe du QA est fusionnée avec la première (auto_fix demandé dans le même appel LLM) pour économiser des requêtes.

## Limitations connues

- **Mémoire** : NLLB-200-distilled-600M tient en CPU (~2.5 GB). Le full 3.3 GB nécessite CUDA.
- **Ollama parallèle = 1** : par design, pour éviter l'OOM GPU. Le routeur sérialise via sémaphore.
- **Grammalecte** : optionnel, FR uniquement. Sans : le GrammarProofer devient un passthrough.
- **HITL non persisté** : les requêtes vivent en RAM dans l'orchestrateur. Si le backend crash, les HITL en attente sont perdues (les chunks restent à `waiting_for_human`).
- **GUI v4 minimale** : 4 onglets, pas de prévisualisation plein texte. La fenêtre **ChunkDetailDialog** (clic sur un chunk) montre les traductions intermédiaires à la demande.
- **Reprise partielle** : les chunks en cours de traitement quand le backend crash sont perdus (idempotence du pipeline = à retraiter depuis `parsed` ou `fast_translated`).

## Validation

```powershell
# Compilation check (ce que la CI exécute)
python -m compileall -q src

# Smoke test manuel
python src/main_qt.py
# → Backend + GUI lancent, badge LLM vert
# → Drop un petit EPUB, clic Start, activity log montre progression
# → Si HITL : popup apparaît, répondre, l'activity log reprend
# → Fichier traduit présent dans l'onglet Files
```

## Licence

Voir le fichier `LICENSE` (à ajouter).

# NovelTrad - Spécification Simplifiée

## Vision
Application de TAO accessible pour traduire des novels automatiquement avec révision humaine minimale.

**Objectif** : "Load & Translate" → révision humaine

## MVP (Phase 1)

### Import/Export
- [x] EPUB
- [x] DOCX
- [x] TXT
- [ ] PDF (v2)

### Traduction Automatique
- [x] NLLB (ctranslate2)
- [x] Argos Translate
- [x] LLM local (LM Studio / Ollama)
- [x] LLM online (OpenAI compatible)

### Interface
- [x] Vue bilingue synchronisée
- [ ] Statut des segments

### Base
- [ ] Export EPUB traduit

## Phase 2 - Productivité

### Glossaire
- [x] Glossaire manuel (CSV)
- [ ] Glossary AI (génération auto)
- [ ] Application auto pendant traduction

### Mémoire de Traduction
- [x] Import/Export TMX
- [ ] Fuzzy matching

### IA Avancée
- [x] Editor AI (raffinage)
- [ ] Batch translation (chapitre entier)
- [ ] Structure AI (détection chapitres)

## Architecture

```
src/
├── core/           # Logique métier
│   ├── database.py # Modèles DB
│   └── project_manager.py
├── engines/        # Moteurs de traduction
│   ├── nllb_engine.py
│   ├── argos_engine.py
│   └── llm_engine.py
├── formats/        # Parsers fichiers
└── gui/            # Interface PyQt6
```

## Technologies
- **GUI**: PyQt6
- **DB**: Peewee (SQLite)
- **NMT**: ctranslate2, Argos Translate
- **LLM**: OpenAI API compatible (LM Studio, Ollama)

## Standards
- TMX 1.4b (compatible OmegaT)
- UTF-8
- Offline-first

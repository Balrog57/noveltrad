# CAHIER DES CHARGES
# NovelTrad
# Application de Traduction Assistée par Ordinateur
# pour Romans et Web Novels
# Xianxia • Science-Fiction • Fantasy • Romance • Tous genres
# Version 3.0

# Date : 26 février 2026

# Références standards :
# - OmegaT v6.1.0 (standard de référence TAO)
# - TMX 1.4b (format d'échange)
# - PDF/UA (accessibilité)
# - WCAG 2.1 (accessibilité web)

# SPDX-License-Identifier: CC-BY-SA-4.0

---

# Résumé Exécutif (v3.0)

## Vision

**NovelTrad v3.0 réunit la puissance d'OmegaT et la simplicité de l'IA générative.**

L'objectif est de créer l'outil de TAO (Traduction Assistée par Ordinateur) le plus accessible pour la traduction de romans, en combinant :

- **L'approche structurée d'OmegaT** : mémoires de traduction, glossaires, alignement, raccourcis clavier (100+), gestion de projets robuste
- **L'intelligence artificielle simplifiée** : Glossary AI, Editor AI, traduction automatique par IA Locale/En ligne
- **L'expérience utilisateur "Frictionless"** : interface intuitive, pas de configuration complexe pour démarrer

### Philosophie : Complexité sous le capot, Simplicité en surface

- **Novice** : Importe un EPUB → Traduit → Exporte (interface minimum)
- **Expert** : Gère tm/enforce, tm/auto, alignement Viterbi, 100+ shortcuts, regex groups
- **IA Power User** : Instructions personnalisées, feedback loop, batch processing

## Évolution v2.0 → v3.0

| Fonctionnalité | v2.0 | v3.0 |
|---------------|------|------|
| **Interface** | Vue bilingue simple | Vue segmentée avancée (SegmentCard, 100+ shortcuts) |
| **Mémoire de Traduction** | Export TMX basique | tm/enforce, tm/auto, tm/mt, tmx2source, tm/penalty |
| **Alignement** | Non implémenté | Algorithme Viterbi/Avant-Arbitrage, UI interactive 3-colonnes |
| **Glossaires** | Manuel + Glossary AI | Feedback loop, catégories par genre, export/import TBX |
| **Search/Replace** | Recherche simple | Regex groups ($1-$9), preview, filtering |
| **Gestion de Projet** | Structure de base | `.noveltrad/` complète avec structure OmegaT-compliant |
| **Sauvegardes** | Aucune | Snapshots 3-min, pre-mod backup, timestamps (10 max) |
| **QA Check** | Balises simples | Export PDF/HTML, validation en temps réel, grammaire |
| **Project Sharing** | Export/Import ZIP | Git/SVN sync, shared disk |
| **Documentation** | Utilisateur | Intégrée développeur complète |

## Objectif de la v1.1

**Développer NovelTrad v1.1 (4-5 mois) pour atteindre la "reachabilité professionnelle".**

- **HIGHT** : tm/enforce, tm/auto, structure projet, pre-mod backups
- **HIGH** : Alignment UI++, 100+ shortcuts, Search/Replace++
- **MEDIUM** : tmx2source, tm/mt, tmx sharing
- **LOW** : Git sync, plugins, i18n

---

# 1. Architecture de Projet

## 1.1 Structure .noveltrad/ (Standard OmegaT)

```
projet_max/
│
├── .noveltrad/                    # Configuration projet (secret, .gitignore)
│   ├── project.json              # Métadonnées (genre, langues, instructions, schema_version=3)
│   ├── project_save.tmx          # Mémoire de traduction principale (TMX 1.4b)
│   ├── project_save.tmx.bak      # Sauvegarde immédiate (pré-modification)
│   ├── project_save.tmx.timestamp.bak  # Snapshot timestamped (max 10)
│   ├── project_stats.txt         # Statistiques globales
│   ├── project_stats_match.txt   # Statistiques de correspondance
│   ├── project_stats_match_per_file.txt  # Stats par fichier
│   ├── ignored_words.txt         # Orthographe (mots à ignorer)
│   ├── learned_words.txt         # Orthographe (mots ajoutés)
│   ├── segmentation.conf         # Règles de segmentation spécifiques
│   ├── filters.xml               # Filtres de fichiers spécifiques
│   ├── uiLayout.xml              # Layout UI projet
│   ├── finder.xml                # Recherches externes
│   ├── last_entry.properties     # Dernier segment visité
│   └── .repositories/            # Sync Git/SVN (copie versionnée distante)
│       ├── git/                  # Copie Git du dépôt distant
│       └── svn/                  # Copie SVN du dépôt distant
│
├── source/                        # Fichiers à traduire (originaux)
│   ├── documents/                # Le fichier original doit être copié ici
│   │   └── document.epub         # ou .docx, .pdf, .txt
│   └── extracted/                # Texte extrait et structuré
│       ├── document/
│       │   ├── chapter_001.txt
│       │   ├── chapter_002.txt
│       │   └── metadata.json     # Structure détectée (titres, chapitres)
│       └── chapters_index.txt    # Index chapitres pour alignement
│
├── target/                        # Fichiers traduits (export)
│   ├── document.epub             # EPUB traduit avec préservation formatage
│   ├── document.docx             # DOCX traduit
│   ├── document.pdf              # PDF reconstruit
│   └── chapter_001.txt           # Fichier texte traduit
│
├── tm/                            # Mémoires de traduction (TMX)
│   ├── enforce/                  # Traductions à appliquer sans condition (100%)
│   │   └── bonus_translation.tmx
│   ├── auto/                     # Traductions auto-insertion (fiabilité élevée)
│   │   └── legacy_project.tmx
│   ├── mt/                       # Traductions MT (surlignage rouge)
│   │   ├── machine_translation.tmx
│   │   └── penalty-030/          # Pénalité de 30% sur scores
│   │       └── less_reliable.tmx
│   ├── tmx2source/               # Langue référence affichée sous source
│   │   └── ja-JP.tmx             # Ex: Japonais affiché sous Anglais
│   └── export/                   # TM export configured location
│       └── project_save.tmx      # TM projet exportée
│
├── glossary/                      # Glossaires
│   ├── glossary.txt              # Glossaire modifiable (par défaut)
│   ├── manual/                   # Glossaires manuels
│   │   ├── xianxia.csv           # Glossaire xianxia (import/export CSV)
│   │   ├── terms.tbx             # Glossaire TBX (standard ISO 30042)
│   │   └── genre_romance.csv
│   └── auto_generated/           # Glossaires générés par IA
│       ├── document_2026-02-26.json
│       └── document_feedback.json  # Historique corrections (feedback loop)
│
├── dictionary/                    # Dictionnaires de référence (StarDict, DSL)
│   ├── cedict-stardict.*         # CC-CEDICT (StarDict format)
│   ├── jmdict-stardict.*
│   └── lingvo_dsl/               # Dictionnaires DSL
│       └── french_english.dsl
│
├── prompts/                       # Prompts personnalisés
│   ├── xianxia.json              # Prompt xianxia prédéfini
│   ├── scifi.json                # Prompt SF prédéfini
│   └── custom_instructions.json  # Instructions personnalisées utilisateur
│
├── notes/                         # Notes du traducteur (segment-level)
│   ├── chapter_001/              # Notes par chapitre
│   │   ├── segment_001.txt
│   │   └── segment_002.txt
│   └── global_notes.txt          # Notes globales au projet
│
├── snapshots/                     # Snapshots automatiques (10 max)
│   ├── 2026-02-26_14-30-15/      # Snapshot timestampé
│   │   ├── project.json
│   │   ├── tm/
│   │   ├── glossary/
│   │   └── notes/
│   └── 2026-02-26_15-33-20/
│
├── backup/                        # Backups avant modification
│   ├── pre-mod-segment_12345.tmx.bak
│   └── pre-mod-project_20260226.json
│
└── documentation/                 # Documentation projet
    ├── user_guide.md
    ├── glossary_terms.md         # Glossary AI generated terms
    └── feedback_log.txt          # Journal des corrections Glossary AI
```

## 1.2 Fichier .noveltrad/project.json (v3.0)

```json
{
  "schema_version": "3.0.0",
  "version": "1.1-pre-alpha",
  "name": "le_chateau_anime",
  "title": "Le Château Animé",
  "description": "Manga xianxia Traduit du chinois vers le français",
  
  # Langues BCP-47
  "source_lang": "zh-Hans",
  "target_lang": "fr-FR",
  
  # Genres (support multi-genre avec priorité)
  "genres": ["xianxia", "fantasy"],
  
  # Format source original
  "source_format": "epub",
  "source_path": "source/extracted/document.epub",
  
  # Moteur par défaut
  "default_engine": "nllb-1.3b",
  
  # Instructions personnalisées (AI)
  "custom_instructions": "Traduire de façon littéraire, utiliser le tutoiement pour les personnages principaux, conserver les noms propres chinois en pinyin pour les personnages, traduire les termes de cultivation ('cultiver la voie', 'core formation') par des équivalents français adaptés.",
  
  # Paramètres de segmentation
  "segmentation": {
    "level": "sentence",  # "paragraph" ou "sentence"
    "use_local_rules": true,
    "rules_file": ".noveltrad/segmentation.conf"
  },
  
  # Moteurs de traduction configurés
  "engines": {
    "nllb-600m": {
      "type": "nllb",
      "model_path": "/models/nllb-600m",
      "device": "cpu",
      "precision": "int8",
      "enabled": true
    },
    "nllb-1.3b": {
      "type": "nllb",
      "model_path": "/models/nllb-1.3b",
      "device": "cuda",
      "precision": "float16",
      "enabled": true
    },
    "argos-en-fr": {
      "type": "argos",
      "model": "en-fr",
      "enabled": true
    },
    "llm-local": {
      "type": "llm",
      "url": "http://localhost:1234/v1",
      "model": "qwen2.5-7b",
      "temperature": 0.3,
      "enabled": true
    },
    "llm-online": {
      "type": "llm",
      "url": "https://api.openai.com/v1",
      "model": "gpt-4o-mini",
      "api_key_env": "OPENAI_API_KEY",
      "enabled": false
    },
    "google-translate": {
      "type": "google_translate",
      "enabled": false
    }
  },
  
  # Batch processing
  "batch_settings": {
    "chunk_size": 5,  # Paragraphes par batch
    "timeout_seconds": 180,
    "retry_on_timeout": true,
    "max_retries": 3
  },
  
  # Paramètres TM
  "tm_settings": {
    "fuzzy_threshold": 75,  # % minimum fuzzy match
    "auto_propagate": true,  # Traductions répétées automatiques
    "save_auto_populated_status": true,
    "export_formats": ["tmx_level2", "omegat"],
    "export_enabled": true,
    "export_location": "tm/export"
  },
  
  # Glossary AI
  "glossary_auto": {
    "enabled": true,
    "generation_frequency": "per_chapter",  # "per_chapter", "per_project", "manual_only"
    "prompt_template": "prompts/xianxia.json",
    "feedback_enabled": true,
    "feedback_path": "glossary/auto_generated/document_feedback.json"
  },
  
  # Preview de rendu
  "render_preview": {
    "enabled": false,  # Par défaut désactivé pour performance
    "format": "html",  # HTML ou EPUB
    "show_in_editor": true,
    "update_on_edit": false  # "on_save" ou "manual"
  },
  
  # Sauvegardes
  "backup": {
    "pre_modification": true,
    "snapshot_interval_minutes": 3,
    "max_snapshots": 10,
    "backup_location": "backup"
  },
  
  # QA Check
  "qa": {
    "auto_check_on_export": true,
    "check_tags": true,
    "check_numbers": true,
    "check_glossary_terms": true,
    "check_empty_segments": true,
    "export_formats": ["pdf", "html"],
    "report_location": "qa_reports"
  },
  
  # Accessibilité
  "accessibility": {
    "theme": "dark",  # "dark", "light", "auto"
    "colorblind_mode": true,
    "font_scale": 1.0,
    "line_height": 1.5,
    "dark_theme_colors": {
      "background": "#1e1e1e",
      "text": "#e0e0e0",
      "segment_source": "#2d2d2d",
      "segment_target": "#3d3d3d",
      "status_untranslated": "#ff6b6b",
      "status_machine": "#ffa94d",
      "status_ai_refined": "#d3e3fd",
      "status_validated": "#51cf66",
      "glossary_match": "#fcc419",
      "tm_match": "#c4b5fd"
    },
    "light_theme_colors": {
      "background": "#ffffff",
      "text": "#000000",
      "segment_source": "#f8f9fa",
      "segment_target": "#e9ecef",
      "status_untranslated": "#fa5252",
      "status_machine": "#e03131",
      "status_ai_refined": "#228be6",
      "status_validated": "#20c997",
      "glossary_match": "#fab005",
      "tm_match": "#7950f2"
    }
  },
  
  # Statistiques projet
  "statistics": {
    "word_count_source": 125000,
    "word_count_target": 0,
    "segments_total": 4500,
    "segments_translated": 1200,
    "segments_machine": 800,
    "segments_ai_refined": 0,
    "segments_validated": 400,
    "last_updated": "2026-02-26T14:30:00Z",
    "engines_stats": {
      "nllb-1.3b": {
        "segments_translated": 600,
        "avg_time_per_segment_ms": 2500,
        "total_time_seconds": 1500
      }
    }
  },
  
  # Metadonnées de création
  "created_at": "2026-02-26T14:00:00Z",
  "created_by": "user@example.com",
  "last_modified_at": "2026-02-26T14:30:00Z",
  "last_modified_by": "user@example.com"
}
```

## 1.3 Fichier project.json (racine - métadonnées léger)

```json
{
  "schema_version": "3.0.0",
  "name": "le_chateau_anime",
  "title": "Le Château Animé",
  "source_lang": "zh-Hans",
  "target_lang": "fr-FR",
  "genre": "xianxia",
  "default_engine": "nllb-1.3b",
  "version": "1.1-pre-alpha"
}
```

---

# 2. Moteurs de Traduction

## 2.1 Architecture Unifiée (TranslationEngine Interface)

```python
class TranslationEngine(ABC):
    """Interface unifiée pour tous les moteurs de traduction."""
    
    @abstractmethod
    def translate(
        self,
        text: str,
        src_lang: str,
        tgt_lang: str,
        glossary: dict = None,
        context: list = None,
        custom_instructions: str = None
    ) -> str:
        """Traduit un texte simple."""
        pass
    
    @abstractmethod
    def translate_batch(
        self,
        texts: list[str],
        src_lang: str,
        tgt_lang: str,
        glossary: dict = None,
        context: list = None,
        custom_instructions: str = None
    ) -> list[str]:
        """Traduit une liste de textes en batch."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> list[tuple[str, str]]:
        """Retourne les paires (code, nom) de langues supportées."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Nom du moteur."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie la disponibilité du moteur (modèles chargés, connexion, etc.)."""
        pass
    
    @abstractmethod
    def supports_context(self) -> bool:
        """Supporte-t-il le contexte (pour LLM) ?"""
        pass
    
    def supports_custom_instructions(self) -> bool:
        """Supporte-t-il les instructions personnalisées ?"""
        return False
    
    def get_engine_type(self) -> str:
        """Retourne le type de moteur : 'nllb', 'argos', 'llm', 'online'."""
        return "unknown"
    
    def get_stats(self) -> dict:
        """Retourne les statistiques d'utilisation du moteur."""
        return {}
```

## 2.2 NLLB (Meta NLLB-200) - Moteur Principal

**Bibliothèque :** `ctranslate2` (CPU/GPU, quantization)

**Modèles :**
- `nllb-600m` : Rapide, CPU
- `nllb-1.3b` : Qualité équilibrée
- `nllb-3.3b` : Qualité maximale (GPU recommandé)

**Langues supportées :** 200+ langues
- Focus : `eng_Latn` → `fra_Latn`, `zho_Hans` → `fra_Latn`, `jpn_Jpan` → `fra_Latn`, `kor_Hang` → `fra_Latn`

**Configuration :**
```json
{
  "type": "nllb",
  "model_path": "/models/nllb-1.3b",
  "device": "cuda",  # "cpu", "cuda", "cuda:1"
  "precision": "float16",  # "int8", "float16", "float32"
  "max_memory_gb": 4.0,  # Limite mémoire GPU
  "enabled": true
}
```

**Performance cible :**
- Traduction paragraphe (NLLB-1.3B, GPU RTX3060) : < 2s
- Traduction paragraphe (NLLB-600M, CPU) : < 3s

## 2.3 Argos Translate (MarianMT) - Traduction Rapide

**Bibliothèque :** `argostranslate`

**Modèles :** Packages de langues téléchargeables
- `en-fr`, `zh-en`, `ja-en`, `ko-en`, etc.
- Mode pivot : `ja→en→fr` si pas de package direct

**Configuration :**
```json
{
  "type": "argos",
  "model": "en-fr",
  "device": "cpu",
  "enabled": true
}
```

**Performance cible :**
- Traduction segment (CPU) : < 500ms

## 2.4 Traduction par IA (LLM) - Qualité Narrative

**LLM Local :** LM Studio, Ollama, Nous (~1234/v1 compatible OpenAI)

**LLM En ligne :** OpenAI, Anthropic, Mistral, Groq, etc.

**Prompt de traduction (xianxia par défaut) :**
```
Tu es un traducteur professionnel expert en xianxia et fantastique.
Traduis le texte suivant du {src_lang} vers le {tgt_lang}.

Contexte du roman :
- Genre : xianxia
- Ton : littéraire, épic
- Style : descriptions sensorielles détaillées
- Règles de nommage : conserver les noms propres chinois en pinyin

Glossaire à respecter :
{glossary_json}

{custom_instructions if provided}

Texte à traduire :
{source_text}

Traduit uniquement le texte, ne rajoute pas de commentaires, préserve le formatage et les balises.
```

**Configuration :**
```json
{
  "type": "llm",
  "url": "http://localhost:1234/v1",
  "model": "qwen2.5-7b",
  "temperature": 0.3,
  "max_tokens": 2048,
  "timeout_seconds": 120,
  "context_window": 8192,
  "api_key_env": "LM_STUDIO_API_KEY",
  "enabled": true,
  "batch_enabled": true,
  "batch_size": 5
}
```

**Performance cible :**
- Traduction paragraphe (local, 7B params) : 5-30s
- Traduction paragraphe (online, GPT-4o-mini) : 3-8s

## 2.5 Services Web Gratuits - Complémentaire

### Google Translate (sans API)

**Bibliothèque :** `googletrans` ou `deep-translator`

**Utilisation limitée :**
- Traduction de segments individuels uniquement (pas batch)
- Avertissement user : "Rate limiting possible, utilisez local pour chapitres entiers"

**Configuration :**
```json
{
  "type": "google_translate",
  "enabled": false
}
```

### LibreTranslate (auto-hébergé)

**API :** https://github.com/LibreTranslate/LibreTranslate

**Configuration :**
```json
{
  "type": "libre_translate",
  "url": "https://libretranslate.com",
  "enabled": false
}
```

## 2.6 Intégration des Moteurs

### Choix du Moteur

1. **Default Engine** (configurable projet)
2. **Override par segment** (menu contextuel)
3. **Batch translation** (utilise Default)
4. **Manual translation** (combo-box UI)

### UI : Combo-box Moteur

```
[Moteur de traduction▼]
équivalent to OmegaT "Machine Translation" settings

Options :
- [Default Engine]
- NLLB 600M (CPU)
- NLLB 1.3B (GPU)
- Argos en-fr
- LLM Local (Qwen2.5-7B)
- LLM Online (GPT-4o-mini)
```

### Batch Processing UI

```
Traduction en cours...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chapter 001: ██████████░░░░░░░░░░░░░░ 45% eta: 12s
Chapter 002: ████████████████████████ 100% ✓
Chapter 003: ░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%  waiting
────────────────────────────────────
Total: 30% | 320/1000 segments traduits

[] Pause [] Reprendre [] Annuler
```

---

# 3. Interface Utilisateur

## 3.1 Vue Segmentée (OmegaT-style)

### SegmentCard (Unité d'affichage)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ¶                                                                 │
│  Hide Tags        ┌───────────────────────────────────────────────┐ │
│  [◄]              │ He stepped into the cultivation chamber.   <S>│ │
│  [▼]              └───────────────────────────────────────────────┘ │
│  [Lock] ┌───────────────────────────────────────────────────────┐   │
│         │ Il entra dans la chambre de cultivation.              │   │
│         └───────────────────────────────────────────────────────┘   │
│  [Lock]  [Cible]                                                    │
│                     ┌─────────────────────────────────────────────┐ │
│                     │ [Espace de traduction... Ctrl+J pour ajouter]││
│                     └─────────────────────────────────────────────┘ │
│  [F2 lock]                         Status: [Machine ▼]               │
│                                    [NLLB-1.3B 2.3s]                 │
└─────────────────────────────────────────────────────────────────────┘
Segment #123 | Chapter 007 | Mots: 8/12
```

### Composants SegmentCard

| Elément | Raccourci | Fonction |
|--------|-----------|----------|
| **Hide Tags [◄]** | Ctrl+Shift+H | Masquer/moins balises |
| **Prev Segment [▲]** | Ctrl+P | Segment précédent |
| **Next Segment [▼]** | Ctrl+N | Segment suivant |
| **Lock Cursor [F2]** | F2 | Verrouiller curseur dans champ cible |
| **Segment source** | - | Texte source (verrouillé) |
| **Segment target** | - | Champ de traduction (éditable) |
| **Status dropdown** | - | machine / ai_refined / validated / empty |
| **Statistics** | - | mots traduits, temps engine |
| **Navigation** | - | Retour haut paragraphe ¶ |

### Actions Raccourcies

| Action | Raccourci | Description |
|--------|-----------|-------------|
| **Sauvegarder segment** | Ctrl+S | Enregistrer dans TM |
| **Segment suivant** | Ctrl+N / Enter | Next segment |
| **Segment précédent** | Ctrl+P / Ctrl+Enter | Previous segment |
| **Alt. translation** | Ctrl+Alt+T | Créer traduction alternative |
| **Default translation** | Ctrl+Shift+T | Définir comme default |
| **RTM fuzzy match** | Ctrl+R | Remplacer par correspondance |
| **Insert fuzzy** | Ctrl+I | Insert fuzzy match |
| **TM auto-translation** | Ctrl+M | Traduction auto |
| **Tag painter** | Ctrl+Shift+T | Insérer balises manquantes |
| **Next missing tag** | Ctrl+T | Insérer prochaine balise |
| **Previous segment (history)** | Ctrl+Shift+P | History back |
| **Next segment (history)** | Ctrl+Shift+N | History forward |

## 3.2 Navigation dans le Projet

### Barre de Navigation

```
◀ [Précédent]  [Chapitre 007/45]  [Suivant ▶]  [       123/1500 segments] [Fuzzy: 78%]  [TM: xianxia-v2.tmx]
```

### Panneau de Navigation

| Panneau | Raccourci | Contenu |
|--------|-----------|---------|
| **Editor (principal)** | Ctrl+Alt+0 | Vue segmentée |
| **Fuzzy Matches** | F3 | Correspondances floues |
| **Glossary** | Ctrl+Alt+G | Termes glossaire |
| **Dictionary** | Alt+Shift+D | Dictionnaire |
| **MT Suggestions** | Ctrl+Alt+M | Traductions auto |
| **Notes** | Ctrl+Alt+N | Bloc-notes |
| **Comments** | - | Commentaires (read-only) |

### Configuration UI (Perso)

Dossier config : `.noveltrad/uiLayout.xml`

```xml
<uilayout version="3.0">
    <dock position="left" width="300">
        <pane id="glossary" />
        <pane id="dictionary" />
    </dock>
    <dock position="right" width="250">
        <pane id="fuzzy_matches" />
        <pane id="mt_suggestions" />
        <pane id="notes" />
    </dock>
    <dock position="bottom" height="150">
        <pane id="comments" />
    </dock>
    <mainPanel id="editor" />
</uilayout>
```

## 3.3 Undo/Redo Multi-niveau

**Architecture :** Command pattern avec history stack

```python
class TranslationCommand(Command):
    def __init__(self, segment, old_text, new_text, engine):
        self.segment = segment
        self.old_text = old_text
        self.new_text = new_text
        self.engine = engine
    
    def execute(self):
        self.segment.target_text = self.new_text
        self.segment.status = "translated"
        self.segment.engine_used = self.engine
        self.segment.last_modified = datetime.now()
    
    def undo(self):
        self.segment.target_text = self.old_text
        self.segment.status = "untranslated"
        self.segment.engine_used = None
```

**Depth :** 50 commands (configurable)

## 3.4 Thèmes et Accessibilité

### Thèmes par défaut

**Dark (default)**
```json
{
  "background": "#1e1e1e",
  "text": "#e0e0e0",
  "segment_source": "#2d2d2d",
  "segment_target": "#3d3d3d",
  "status_untranslated": "#ff6b6b",
  "status_machine": "#ffa94d",
  "status_ai_refined": "#d3e3fd",
  "status_validated": "#51cf66",
  "glossary_match": "#fcc419",
  "tm_match": "#c4b5fd"
}
```

**Light**
```json
{
  "background": "#ffffff",
  "text": "#000000",
  "segment_source": "#f8f9fa",
  "segment_target": "#e9ecef",
  "status_untranslated": "#fa5252",
  "status_machine": "#e03131",
  "status_ai_refined": "#228be6",
  "status_validated": "#20c997",
  "glossary_match": "#fab005",
  "tm_match": "#7950f2"
}
```

### Mode daltoniens (protanope/déutéranope/tritanope)

```json
{
  "colorblind_mode": true,
  "colors": {
    "status_untranslated": "#d6336c",  # Pink-red
    "status_machine": "#c4b5fd",  # Purple
    "status_ai_refined": "#3399ff",  # Blue
    "status_validated": "#4dabf7",  # Light blue
    "glossary_match": "#fd7e14",  # Orange
    "tm_match": "#10b981"  # Green
  }
}
```

## 3.5 Auto-completion (OmegaT-style)

### Types d'auto-completion

1. **Glossary Auto-complete** (priorité haute)
2. **TM History Auto-complete** (segments similaires)
3. **Auto-text** (configuration utilisateur)
4. **Character table** (symboles spéciaux)

### UI Auto-completion

```
┌──────────────────────────────────────────────────────┐
│  traduire |traduit          [▼]                      │
│  traduction |traduction [▼]                          │
│  traducteur |traducteur [▼]                          │
│  traduire [Enter]                                    │
└──────────────────────────────────────────────────────┘

[↑↓] Navigate  [Enter] Confirm  [Esc] Cancel
[Space] Trigger auto-complete
```

### Configuration auto-complete

```json
{
  "auto_complete": {
    "enabled": true,
    "show_suggestions_automatically": true,
    "history_completion": true,
    "history_prediction": true,
    "history_limit": 100,
    "glossary_completion": true,
    "max_suggestions": 5
  }
}
```

---

# 4. Mémoire de Traduction

## 4.1 Architecture TM (OmegaT-compliant)

### Dossiers TM

```
tm/
├── enforce/            # Traductions à appliquer exactement (100%)
│   └── glossary_tnx.tmx  # Glossaire_force TMX
├── auto/              # Traductions auto-insertion (confiance élevée)
│   └── legacy_project.tmx
├── mt/                # Traductions MT (surlignage rouge)
│   ├── mt_quick.tmx
│   └── penalty-030/   # Pénalité 30% sur scores
│       └── less_reliable.tmx
├── tmx2source/        # Langue référence affichée sous source
│   └── ja-JP.tmx
└── export/            # Emplacement TM export
    └── project_save.tmx
```

### Règles d'utilisation

| Dossier | Score | Insertion | Écrasement | Usage |
|--------|-------|-----------|------------|------|
| **tm/enforce** | 100% | Auto (no prefix) | **OUI** | Glossaire criticize terms |
| **tm/auto** | 100% | Auto (no prefix) | Non | Glossary Traductions fiables |
| **tm/mt** | <100% | Oui (prefix) | Non | Traductions machine |
| **tm/penalty-XX** | -XX% | Oui (prefix) | Non | Traductions moins fiables |

## 4.2 Format TMX 1.4b (Standard)

### Structure TU (Translation Unit)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tmx SYSTEM "tmx14.dtd">
<tmx version="1.4b">
  <header
    creationtool="OmegaT v6.1.0"
    creationtoolversion="6.1.0"
    segtype="sentence"
    o-tmf="ABuT"
    adminlang="EN-US"
    srclang="eng-Latn"
    datatype="plaintext"
    encoding="UTF-8"
    creationid="omegat"
    creationdate="20260226T143000Z"
    compression="none"
  >
    <prop type="x-noveltrad:schema_version">3.0.0</prop>
    <prop type="x-noveltrad:genre">xianxia</prop>
    <prop type="x-noveltrad:last_modified">2026-02-26T14:30:00Z</prop>
  </header>
  <body>
    
    <!-- Segment traduit simple -->
    <tu tuid="segment_12345" datatype="plaintext">
      <tuv xml:lang="eng-Latn" creationdate="20260226T143000Z" creationid="user">
        <seg>He stepped into the cultivation chamber.</seg>
      </tuv>
      <tuv xml:lang="fra-Latn" creationdate="20260226T143000Z" creationid="user" changeid="user" changedate="20260226T143000Z">
        <seg>Il entra dans la chambre de cultivation.</seg>
      </tuv>
      <prop type="x-noveltrad:chapter">chapitre_007</prop>
      <prop type="x-noveltrad:engine">nllb-1.3b</prop>
      <prop type="x-noveltrad:status">validated</prop>
    </tu>
    
    <!-- Segment avec balises -->
    <tu tuid="segment_12346" datatype="plaintext">
      <tuv xml:lang="eng-Latn">
        <seg>The<hi>Golden Core</hi> stabilized within his dantian.</seg>
      </tuv>
      <tuv xml:lang="fra-Latn">
        <seg>Le<hi>noyau d'or</hi> se stabilisa dans son dantian.</seg>
      </tuv>
      <prop type="x-noveltrad:tags">(hi) Golden Core → noyau d'or</prop>
    </tu>
    
    <!-- Segment alternative (multi traductions) -->
    <tu tuid="segment_12347" datatype="plaintext">
      <tuv xml:lang="eng-Latn">
        <seg>The crimson lotus bloomed in his palm.</seg>
      </tuv>
      <tuv xml:lang="fra-Latn" halg="default">
        <seg>La lotus écarlate s'épanouit dans sa paume.</seg>
      </tuv>
      <tuv xml:lang="fra-Latn" usagecount="3">
        <seg>La fleur de lotus écarlate s'épanouit dans sa paume.</seg>
      </tuv>
    </tu>
    
    <!-- Segment orphelin (TMX backup pour révision) -->
    <tu tuid="segment_12348" datatype="plaintext" o-orphans="true">
      <tuv xml:lang="eng-Latn">
        <seg>The mountain peak pierced the clouds.</seg>
      </tuv>
      <tuv xml:lang="fra-Latn">
        <seg>Le pic de la montagne perçait les nuages.</seg>
      </tuv>
    </tu>
    
  </body>
</tmx>
```

### Propriétés personnalisées (x-noveltrad:*)

| Propriété | Description | Type | Exemple |
|----------|-------------|------|--------|
| `x-noveltrad:chapter` | Nom chapitre | string | `chapitre_007` |
| `x-noveltrad:genre` | Genre | string | `xianxia` |
| `x-noveltrad:engine` | Moteur utilisé | string | `nllb-1.3b` |
| `x-noveltrad:status` | Statut segment | string | `untranslated`, `machine`, `ai_refined`, `validated`, `empty` |
| `x-noveltrad:timestamp` | Horizontal creation | datetime | `2026-02-26T14:30:00Z` |
| `x-noveltrad:comments` | Notes traducteur | string | `Vérifier nom propre` |
| `x-noveltrad:tags` | Balises et mappage | string | `(hi, b0, i1)` |
| `x-noveltrad:context` | Contexte cross-segment | JSON array | `["précédent", "prochain"]` |

## 4.3 Gestion des Correspondances (Fuzzy Matching)

### Algorithme OmegaT (LMS - Levenshtein Modified Score)

```python
def calculate_fuzzy_score(src1, src2, ignore_tags=True, use_lemmatization=True):
    """
    Calcule le score de correspondance floue.
    
    :param src1: Source 1 (segment actuel)
    :param src2: Source 2 (segment dans TM)
    :param ignore_tags: Ignorer les balises
    :param use_lemmatization: Utiliser la lemmatisation
    :return: Score (0-100)
    """
    # Étape 1 : Nettoyage
    if ignore_tags:
        src1 = remove_tags(src1)
        src2 = remove_tags(src2)
    
    # Étape 2 : Lemmatization
    if use_lemmatization:
        src1 = lemmatize(src1, src_lang)
        src2 = lemmatize(src2, src_lang)
    
    # Étape 3 : Calcul Levenshtein
    distance = levenshtein_distance(src1, src2)
    max_len = max(len(src1), len(src2))
    
    # Étape 4 : Score
    score = (1 - distance / max_len) * 100
    
    return round(score, 1)
```

### Score de correspondance affiché

```
Fuzzy Match: 78% (85/78/65%)
────────────────────────────
Source (lemma + ignore tags): 85%
Source (no lemma, ignore tags): 78%
Source (full text, incl. tags/numbers): 65%
```

## 4.4 Import/Export TMX

### Import TMX UI

```
┌────────────────────────────────────────────────────────┐
│               Import de Mémoire de Traduction          │
├────────────────────────────────────────────────────────┤
│  Fichier TMX: [browse...]                              │
│                                                        │
│  Actions :                                             │
│  [ ] Écraser les segments existants                    │
│  [X] Conserver les plus récents (timestamp)           │
│  [ ] Fusionner avec la TM existante                    │
│                                                        │
│  Glossaire auto-application :                          │
│  [ ] Appliquer le glossaire du projet                 │
│  [ ] Appliquer le glossaire de ce TMX                 │
│                                                        │
│  Filtres :                                             │
│  [ ] Importer les segments orphelins                  │
│  [ ] Sauter les segments vides                        │
│                                                        │
│  [Prévisualiser] [Importer]         [Annuler]         │
└────────────────────────────────────────────────────────┘
```

### Export TMX

#### Export TMX UI

```
┌────────────────────────────────────────────────────────┐
│               Export de Mémoire de Traduction          │
├────────────────────────────────────────────────────────┤
│  Format :                                              │
│  [TMX Niveau 2 (standard ISO)▼]                        │
│  [TMX OmegaT (propriétaire)]                           │
│  [TMX Niveau 1 (texte seul)]                           │
│                                                        │
│  Exporter :                                            │
│  [X] Tous les segments validés                        │
│  [ ] Segments traduits (tous statuts)                 │
│  [ ] Segments non traduits uniquement                │
│                                                        │
│  Filtres :                                             │
│  [ ] Exporter glossary terms only                    │
│  [ ] Exporter segments avec notes                    │
│                                                        │
│  Emplacement : [browse...]                             │
│                                                        │
│  [export TMX] [export Selection]     [Annuler]        │
└────────────────────────────────────────────────────────┘
```

### Export TMX Sélectif

```python
def export_tmx_selective(
    query: str,  # SQL-like query
    output_path: str
):
    """
    Export TMX with filtering.
    
    Query examples:
    - "status = 'validated' AND chapter LIKE 'chapter_00%'"
    - "engine = 'nllb-1.3b' AND timestamp > '2026-02-01'"
    - "score >= 95 AND genre = 'xianxia'"
    """
    pass
```

## 4.5 tmx2source (Langue Référence Tier 3)

### Structure

```
tm/tmx2source/
├── ja-JP.tmx    # Japonais affiché sous Anglais
└── en-GB.tmx    # Anglais britannique affiché sous Anglais américain
```

### Règles de nommage

- `LL-PP.tmx` : code langue + code pays 2 lettres (ex: `ja-JP.tmx`)
- `LL-PP.tmx.gz` : version compressée
- `LL.tmx` : code langue uniquement

### Affichage en UI

```
┌────────────────────────────────────────────────────────┐
│  eng-Latn (source)                                     │
│  He stepped into the cultivation chamber.              │
│                                                        │
│  ja-JP (reference)    ← tmx2source                     │
│  彼は修練 chamber に足を踏み入れた。                   │
│                                                        │
│  fra-Latn (target)                                     │
│  Il entra dans la chambre de cultivation.              │
│  [traduction... Ctrl+J]                                │
└────────────────────────────────────────────────────────┘
```

## 4.6 Gestion de la Transparence des Traductions Automatiques

### Propriété `auto-populated`

```json
{
  "segment_id": 12345,
  "target_text": "Il entra dans la chambre de cultivation.",
  "status": "machine",
  "auto_populated_from": "tm/auto/legacy_project.tmx",
  "auto_populated_score": 100,
  "last_modified": "2026-02-26T14:30:00Z"
}
```

### UI Marking

- **tm/enforce / tm/auto** : Segment avec préfixe auto (pas de `[Auto]`)
- **tm/mt / tm/penalty** : Segment avec suffixe `[MT: 65%]`

### Navigation auto-populated

| Action | Raccourci | Description |
|--------|-----------|-------------|
| **Segment suivant auto** | Ctrl+Alt+, | Next auto-populated |
| **Segment précédent auto** | Ctrl+Alt+< | Prev auto-populated |
| **Segment suivant enforce** | Ctrl+Alt+. | Next enforced |
| **Segment précédent enforce** | Ctrl+Alt+> | Prev enforced |

---

# 5. Glossaires

## 5.1 Glossaire Modifiable (glossary.txt)

### Format (TSV - Tab-Separated Values)

```
source_term\ttarget_term\tvariants\tcategory\tcontext\tpriority\ttags\tcreated_at\tmodified_at\tsource
cultivation chamber\tchambre de cultivation\t修练 chamber;修炼 chamber\tterms\txianxia, cultivation\t5\tb0, i1\t2026-02-25T10:00:00Z\t2026-02-26T12:30:00Z\tuser
Golden Core\tnoyau d'or\tgolden heart;golden nucleus\tterms\txianxia, core formation\t10\tb0\t2026-02-25T10:05:00Z\t2026-02-26T12:35:00Z\tuser
sect\tsecte;sect\tfamily;clan;order\tterms\txianxia, organization\t3\t-\t2026-02-25T10:10:00Z\t2026-02-26T12:40:00Z\tuser
```

### Règles

1. **Header optionnel** : `# source\ttarget\tvariants\tcategory\tcontext\tpriority\ttags\tcreated_at\tmodified_at\tsource`
2. **Commentaires** : Lines starting with `#` are ignored
3. **Tab characters** (`\t`) comme séparateurs
4. **Variants** : separated by `;`
5. **Priority** : 0-10, 10 highest
6. **Tags** : list of tag IDs
7. **source** : `user` ou `ai_generated`

### UI Edition

```
┌────────────────────────────────────────────────────────┐
│                      Glossary Editor                   │
├────────────────────────────────────────────────────────┤
│  [Search term▼] [New] [Import CSV] [Export CSV]       │
│                                                        │
│  Source         Target          Variants      Cat      │
│  ────────────────────────────────────────────────────  │
│  cultivation    chamber         ──           terms     │
│  Golden Core    noyau d'or     ──           terms     │
│  sect           secte           family;order terms     │
│                                                        │
│  [Edit] [Delete] [Export selected]                    │
└────────────────────────────────────────────────────────┘
```

## 5.2 Glossary AI (Génération Automatique par IA)

### Principe de Fonctionnement

```
┌────────────────────────────────────────────────────────┐
│                   Glossary AI Generation               │
├────────────────────────────────────────────────────────┤
│  Process:                                              │
│  1. Extract characters, locations, concepts            │
│  2. Send to LLM with genre-specific prompt             │
│  3. Generate translations with categories              │
│  4. Display for user validation                        │
│  5. Store in glossary + feedback loop                  │
└────────────────────────────────────────────────────────┘
```

### Prompt Glossary AI (xianxia)

```json
{
  "name": "xianxia",
  "description": "Extraction de termes pour xianxia/cultivation",
  "prompt": "Analyse le texte suivant, extrait d'un roman xianxia.\n\nIdentifie et liste tous les termes importants nécessitant une traduction cohérente tout au long du roman:\n\n- Noms de personnages (et surnoms/titres associés)
- Noms de lieux (cultivation areas, sects, mountains)
- Concepts de cultivation (dantian, golden core, meridians, Tribulation)
- Titres et rangs (cultivateur, elder, ancestor, vanity)
- Techniques de combat et arts martiaux
- Objets magiques et trésors (swords, rings, talismans)
- Creatures mythologiques (dragons, phoenixes, beasts)\n\nFor each term, provide:\n- source_term: the term in source text (keep exact spelling)
- target_term: the proposed translation in French
- category: one of [characters, locations, concepts, titles, techniques, items, creatures]
- context: short context note (2-3 words)\n\nRespond in valid JSON format:\n{\n  \"terms\": [\n    {\n      \"source_term\": \"cultivator\",\n      \"target_term\": \"cultivateur\",\n      \"category\": \"characters\",\n      \"context\": \"rank, 修行者\"\n    }\n  ]\n}\n\nText source:\n{{SOURCE_TEXT}}"
}
```

### Prompt par genre

| Genre | Prompt Template |
|-------|-----------------|
| **xianxia** | `prompts/xianxia_glossary.json` |
| **wuxia** | `prompts/wuxia_glossary.json` |
| **xuanhuan** | `prompts/xuanhuan_glossary.json` |
| **fantasy** | `prompts/fantasy_glossary.json` |
| **scifi** | `prompts/scifi_glossary.json` |
| **romance** | `prompts/romance_glossary.json` |
| **general** | `prompts/general_glossary.json` |

### Glossary AI Feedback Loop

```json
{
  "term_id": "glossary_123",
  "source_term": "Golden Core",
  "target_term": "noyau d'or",
  "category": "terms",
  "status": "validated",
  "feedback_history": [
    {
      "timestamp": "2026-02-26T14:30:00Z",
      "user_action": "corrected",
      "previous_target": "coeur d'or",
      "new_target": "noyau d'or",
      "reason": "Nomenclature standard xianxia (chambre de cultivation, noyau d'or, non cœur)"
    },
    {
      "timestamp": "2026-02-26T15:45:00Z",
      "user_action": "validated",
      "reason": "Accepted translation, no further changes"
    }
  ],
  "usage_count": 12,
  "last_used": "2026-02-26T15:45:00Z",
  "score": 0.95
}
```

### Glossary AI UI

```
┌────────────────────────────────────────────────────────┐
│                Glossary AI Generation                  │
├────────────────────────────────────────────────────────┤
│  Source: chapter_001.txt                               │
│                                                        │
│  Generating with LLM (Qwen2.5-7B)...                   │
│                                                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Source         Target           Category     Status  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Golden Core ✓  noyau d'or     ✓ terms      ✓ valid │ │
│  │ cultivation    chamber        ✓ terms      ✓ valid │ │
│  │ sect           secte ✓        ✓ terms      ✓ valid │ │
│  │ spiritual      esprit         ✓ terms      ✗ sugg. │ │
│  │ tribulation    tribulation ✓  ✓ concepts   ✓ valid │ │
│  │ golden core   coeur d'or      ✗ terms      ✗ sugg. │ │
│  │ dragon         dragon         ✓ creatures  ✓ valid │ │
│  │ phoenix        phœnix         ✓ creatures  ✗ sugg. │ │
│  └────────────────────────────────────────────────────┘ │
│                                                        │
│  [Validate all] [Reject all] [Edit selection]          │
│  [Save to glossary] [Discard]                          │
└────────────────────────────────────────────────────────┘
```

## 5.3 Import/Export Glossaires

### Formats supportés

| Format | Extension | OmegaT compatible | NovelTrad |
|-------|-----------|------------------|-----------|
| CSV | `.csv` | ✓ | ✓ |
| TSV | `.tsv` | ✓ | ✓ |
| TBX | `.tbx` | ✓ | ✓ |
| XLIF | `.xlf` | ✓ | ✓ |
| Google Sheets | `.xlsx` | ✓ | ✓ |
| StarDict | `.dict.dz` | ✓ | ✓ |

### Import CSV UI

```
┌────────────────────────────────────────────────────────┐
│               Import Glossary (CSV)                    │
├────────────────────────────────────────────────────────┤
│  Fichier: [browse...]                                  │
│                                                        │
│  Format:                                               │
│  [2 columns: source, target▼]                          │
│  [3 columns: source, target, variants]                 │
│  [4 columns: source, target, variants, category]      │
│  [5+ columns: full schema]                             │
│                                                        │
│  Mapping:                                              │
│  Source column:    [1st column▼]                       │
│  Target column:    [2nd column▼]                       │
│  Variants column:  [3rd column▼]                       │
│  Category column:  [4th column▼]                       │
│                                                        │
│  Options:                                              │
│  [X] First row is header                              │
│  [ ] Update existing terms                            │
│  [ ] Add new terms only                               │
│                                                        │
│  [Prévisualiser] [Importer]       [Annuler]           │
└────────────────────────────────────────────────────────┘
```

### Export TBX (ISO 30042)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE TEI.2 SYSTEM "http://www.tei-c.org/DTD/tei.dtd">
<TEI.2>
 <teiHeader>
  <fileDesc>
   <titleStmt>
    <title>Glossary TBX</title>
    <author>NovelTrad v3.0</author>
   </titleStmt>
   <publicationStmt>
    <p>Published by NovelTrad</p>
   </publicationStmt>
   <sourceDesc>
    <p>Bilingual glossary extracted from translation project</p>
   </sourceDesc>
  </fileDesc>
 </teiHeader>
 <text>
  <body>
   <termEntry id="glossary_001">
    <dbInfoGrp>
     <dbInfo>
      <dbInfoItem type="x-noveltrad:genre">xianxia</dbInfoItem>
      <dbInfoItem type="x-noveltrad:source">user</dbInfoItem>
     </dbInfo>
    </dbInfoGrp>
    <langSet xml:lang="en-Latn">
     <tig>
      <term>Golden Core</term>
     </tig>
    </langSet>
    <langSet xml:lang="fr-Latn">
     <tig>
      <term>noyau d'or</term>
     </tig>
    </langSet>
   </termEntry>
  </body>
 </text>
</TEI.2>
```

## 5.4 Glossaire AI Prompt par Genre

| Genre | Prompt Key | Features |
|-------|------------|----------|
| **xianxia** | `xianxia_glossary` | Cultivation, sects, techniques, Tribulations |
| **wuxia** | `wuxia_glossary` | Martial arts, sects, assays, cultivation |
| **xuanhuan** | `xuanhuan_glossary` | Magic, spirits, demons, reincarnation |
| **fantasy** | `fantasy_glossary` | Magic spells, creatures, kingdoms, races |
| **scifi** | `scifi_glossary` | Technology, aliens, spaceships, AI |
| **romance** | `romance_glossary` | Emotions, relationships, settings |
| **general** | `general_glossary` | Generic terms, no genre-specific |

---

# 6. Alignement et Segmentation

## 6.1 Alignement Viterbi/Avant-Arbitrage

### Principe

L'alignement crée une mémoire de traduction à partir de deux fichiers déjà traduits (source + cible).

**Algorithme :**
- **Viterbi** : Algorithme par défaut, meilleur pour textes littéraires
- **Avant-Arbitrage (Forward-Backward)** : Algorithme alternatif, better for technical texts

### UI 3-colonnes

```
┌────────────────────────────────────────────────────────┐
│                   Aligneur de Fichiers                 │
├────────────────────────────────────────────────────────┤
│  Conserver  Source                    Cible            │
│  ─────────  ─────────────────────────  ───────────────  │
│  [✓]        He stepped                 Il entra        │
│  [✓]        into the                   dans la         │
│  [✓]        cultivation                cultivation     │
│  [✓]        chamber.                   chambre.        │
│                                                        │
│  Source file:  document_en.txt                         │
│  Target file:  document_fr.txt                         │
│                                                        │
│  [Aligner (Ctrl+R)] [Continuer] [Annuler]             │
└────────────────────────────────────────────────────────┘
```

### Paramètres d'alignement

| Paramètre | Valeurs | Description |
|-----------|---------|-------------|
| **Mode de comparaison** | Globale, Par segments, Identifiant | Niveau d'analyse |
| **Algorithme** | Viterbi, Avant-Arbitrage | Algorithme mathématique |
| **Calcul** | Normal, Poisson | Répartition statistique |
| **Compteur** | Caractère, Mot | Unité de mesure |
| **Segmenter** | ✓, ✗ | Segmenter par phrases ou paragraphes |
| **Supprimer les balises** | ✓, ✗ | Exclure les balises de l'alignement |
| **Mettre en évidence** | ✓, ✗ | Surligner les chiffres/noms |

### Exemple de fichiers alignés

**Source (document_en.txt)**
```
He stepped into the cultivation chamber. He felt the Qi flow. His Golden Core stabilized.
```

**Cible (document_fr.txt)**
```
Il entra dans la chambre de cultivation. Il sentit le Qi circuler. Son noyau d'or se stabilisa.
```

**Résultat TMX**
```xml
<tu tuid="segment_1">
  <tuv xml:lang="eng-Latn"><seg>He stepped into the cultivation chamber.</seg></tuv>
  <tuv xml:lang="fra-Latn"><seg>Il entra dans la chambre de cultivation.</seg></tuv>
</tu>
<tu tuid="segment_2">
  <tuv xml:lang="eng-Latn"><seg>He felt the Qi flow.</seg></tuv>
  <tuv xml:lang="fra-Latn"><seg>Il sentit le Qi circuler.</seg></tuv>
</tu>
<tu tuid="segment_3">
  <tuv xml:lang="eng-Latn"><seg>His Golden Core stabilized.</seg></tuv>
  <tuv xml:lang="fra-Latn"><seg>Son noyau d'or se stabilisa.</seg></tuv>
</tu>
```

## 6.2 Segmentation (OmegaT-style)

### Niveaux de segmentation

| Niveau | Description | Usage |
|-------|-------------|------|
| **Paragraphes** | Paragraphe complet = 1 segment | Littérature, créatif |
| **Phrases** | Segmentation par règles (ponctuation) | Technique, répétitions |

### Règles de segmentation

**Format :** `\Before\ \After\ [Segmentation]`

```
# Exceptions (no segmentation)
M\.\s          # M. suivi d'espace
Ms\.\s         # Ms. suivi d'espace
Mr\.\s         # Mr. suivi d'espace
Dr\.\s         # Dr. suivi d'espace

# Segmentation (yes segmentation)
\.\s           # Point + espace
!\s            # Point d'exclamation + espace
\?\s           # Point d'interrogation + espace
;              # Point-virgule (no space required)
```

### UI Configuration

```
┌────────────────────────────────────────────────────────┐
│               Règles de Segmentation                   │
├────────────────────────────────────────────────────────┤
│  [✗] Merc. \s          [✓] \.\s                        │
│  [✗] Ms.\s             [✓] !\s                         │
│  [✗] Mr.\s             [✓] ?\s                         │
│  [✗] Dr.\s             [✓] ;                           │
│                                                        │
│  [Modifier] [Dupliquer] [Supprimer]                   │
│                                                        │
│  [Enregistrer] [Annuler]                              │
└────────────────────────────────────────────────────────┘
```

---

# 7. Search & Replace++

## 7.1 Recherche (Regex Groups, Preview, Filtering)

### Syntaxe Regex Supportée

| Expression | Description | Exemple |
|-----------|-------------|---------|
| `.` | N'importe quel caractère | `c.t` = `cat`, `cot`, `cut` |
| `*` | Zéro ou plusieurs répétitions | `col*or` = `color`, `colour`, `colllor` |
| `+` | Une ou plusieurs répétitions | `col+or` = `colour`, `colllor` (pas `color`) |
| `?` | Zéro ou une répétition | `colou?r` = `color`, `colour` |
| `^` | Début de ligne | `^He` = commence par `He` |
| `$` | Fin de ligne | `chamber.$` = termine par `chamber.` |
| `[]` | Classe de caractères | `[abc]` = `a`, `b`, ou `c` |
| `[^]` | Classe négative | `[^abc]` = tout sauf `a`, `b`, `c` |
| `()` | Groupe de capture | `(Golden) (Core)` → `$1`, `$2` |
| `\d` | Chiffre | `\d+` = `123` |
| `\w` | Mot (alphanumérique) | `\w+` = `hello` |
| `\s` | Espace | `\s+` = ` ` ou `  ` |

### UI Recherche

```
┌────────────────────────────────────────────────────────┐
│                  Recherche Textuelle                   │
├────────────────────────────────────────────────────────┤
│  Rechercher : [Golden Core*▼]                         │
│                                                        │
│  Type de recherche :                                   │
│  [●] Exact                                             │
│  [○] Mots-clés                                         │
│  [○] Expressions régulières                            │
│                                                        │
│  Options :                                             │
│  [ ] Respecter la casse                               │
│  [✓] L'espace comprend l'espace insécable             │
│  [ ] Ignorer la différence pleine/demi-largeur        │
│                                                        │
│  Sources :                                             │
│  [✓] Segments source                                   │
│  [✓] Segments cible                                    │
│  [ ] Notes                                             │
│  [ ] Commentaires                                      │
│                                                        │
│  N_TRAduuits :                                         │
│  [✓] Traduits ou pas                                   │
│  [ ] Traduits uniquement                              │
│  [ ] Non traduits uniquement                          │
│                                                        │
│ Afficher :                                             │
│  [●] tous les segments correspondants                 │
│  [○] noms des fichiers                                │
│                                                        │
│  [Rechercher] [Fermer]                                │
│                                                        │
│  Résultats :                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ -- 148> He stepped into the Golden Core chamber. │  │
│  │ -- 234> Golden Core stabilized within his dantian│  │
│  │ -- 567> He touched the Golden Core.              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  [Ouvrir] [Segment suivant] [Segment précédent]       │
└────────────────────────────────────────────────────────┘
```

## 7.2 Remplacement (Regex Groups $1-$9, Preview, Filtering)

### Syntaxe Remplacement

```
Rechercher : (Golden) (Core)
Remplacer par : $2 $1  →  "Core Golden"
```

### UI Remplacement

```
┌────────────────────────────────────────────────────────┐
│                  Remplacement Textuel                  │
├────────────────────────────────────────────────────────┤
│  Rechercher : [(Golden) (Core)▼]                      │
│  Remplacer par : [$2 $1▼]                             │
│                                                        │
│  Type de recherche :                                   │
│  [●] Exact                                             │
│  [○] Mots-clés                                         │
│  [○] Expressions régulières                            │
│                                                        │
│  Options :                                             │
│  [ ] Respecter la casse                               │
│  [ ] L'espace comprend l'espace insécable             │
│  [ ] Ignorer la différence pleine/demi-largeur        │
│  [ ] Non traduits                                      │
│                                                        │
│  Afficher les options avancées                         │
│                                                        │
│  [Rechercher] [Remplacer tout] [Ajouter filtre]       │
│  [Fermer]                                              │
│                                                        │
│  Résultats (preview) :                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ -- 148> He stepped into the <orange>Core Golden</│  │
│  │            <orange>chamber.</orange>              │  │
│  │ -- 234> <orange>Core Golden</orange> stabilized   │  │
│  │            within his dantian.                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Remplacé : 2 segments (1 occurrence par segment)     │
│                                                        │
│  [Remplacer suivant] [Ignorer] [Terminer]             │
└────────────────────────────────────────────────────────┘
```

### Exemples d'utilisation

| Rechercher | Remplacer par | Description |
|-----------|---------------|-------------|
| `(Golden) (Core)` | `$2 $1` | Inverser : "Core Golden" |
| `cultivat(\w+)` | `cultivate $1` | Ajouter e : "cultivator" → "cultivate or" |
| `([0-9]+)th` | `$1<sup>th</sup>` | HTML superscript : "25th" |
| `^\s+` | `` | Supprimer espaces début ligne |
| `\s+$` | `` | Supprimer espaces fin ligne |
| `(\w+)\s+(\w+)` | `$2, $1` | Inverser mots : "Golden Core" → "Core, Golden" |

---

# 8. QA Check et Export

## 8.1 Check Automatique

### Points vérifiés

| Check | Description | Sévérité |
|-------|-------------|----------|
| **Balises** | Balises manquantes ou altérées | Critique |
| **Nombres** | Incohérence des nombres/chiffres | Élevée |
| **Glossaire** | Termes du glossaire non respectés (si forcé) | Moyenne |
| **Segments vides** | Segments vides ou non traduits | Critique |
| **Ponctuation** | Ponctuation finale différente de la source | Moyenne |
| **Espaces** | Espaces manquants ou superflus | Faible |
| **Capitalization** | Majuscules oubliées (début de phrase) | Faible |
| **Grammar** | Erreurs grammaticales (LanguageTool) | Moyenne |

### UI Check

```
┌────────────────────────────────────────────────────────┐
│             Vérification Qualité (QA)                  │
├────────────────────────────────────────────────────────┤
│  Check :                                               │
│  [✓] Balises                                           │
│  [✓] Nombres                                           │
│  [✓] Glossaire (强迫)                                 │
│  [✓] Segments vides                                    │
│  [✓] Ponctuation                                       │
│  [✓] Espaces                                           │
│  [✓] Capitalization                                    │
│  [✓] Grammar (LanguageTool)                            │
│                                                        │
│  Filtres :                                             │
│  [X] Les chapitres traduits                            │
│  [ ] Les segments orphelins                            │
│                                                        │
│  [Vérifier] [Fermer]                                   │
│                                                        │
│  Résultats :                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Line 148: Missing tag <i1> in target             │  │
│  │ Line 234: Number mismatch (5 vs 7)               │  │
│  │ Line 567: Term "cultivation" not in glossary    │  │
│  │ Line 890: Empty target segment                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Total : 4 issues                                      │
│  [Export PDF/HTML] [Corriger sélection]               │
└────────────────────────────────────────────────────────┘
```

## 8.2 Export de Rapports

### Export PDF/HTML

**HTML Report**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>QA Report - Le Château Animé</title>
  <style>
    .critical { color: red; font-weight: bold; }
    .high { color: orange; }
    .medium { color: blue; }
    ...
  </style>
</head>
<body>
  <h1>Quality Assurance Report</h1>
  <p>Project: Le Château Animé</p>
  <p>Date: 2026-02-26</p>
  <h2>Issues: 4</h2>
  <ul>
    <li class="critical">Line 148: Missing tag &lt;i1&gt; in target</li>
    <li class="high">Line 234: Number mismatch (5 vs 7)</li>
    ...
  </ul>
</body>
</html>
```

### Export TMX Quality Tag

```xml
<tu tuid="segment_123">
  ...
  <prop type="x-noveltrad:qa_status">issues</prop>
  <prop type="x-noveltrad:qa_issues">Missing tag, Number mismatch</prop>
</tu>
```

## 8.3 Validation des Balises en Temps Réel

**Principe :** Serializable tag matching

**Example :**

```
Source :  The <b0>Golden Core</b0> stabilized.
Target :  Le <b0>noyau d'or</b0> se stabilisa.

✓ Tags match : b0
```

```
Source :  The <b0>Golden Core</b0> stabilized.
Target :  Le <b0>noyau d'or se stabilisa.

✗ Tags mismatch : opening b0 found, but closing </b0> missing
```

### UI Warning

```
┌────────────────────────────────────────────────────────┐
│           Attention : Incohérence de Balises           │
├────────────────────────────────────────────────────────┤
│  Segment #148                                          │
│                                                        │
│  Source :  The <b0>Golden Core</b0> stabilized.       │
│  Target :  Le <b0>noyau d'or se stabilisa.            │
│                                                        │
│  Error : Closing tag </b0> missing in target.         │
│                                                        │
│  [Éditer] [Ignorer] [Auto-fix]                        │
└────────────────────────────────────────────────────────┘
```

---

# 9. Project Sharing and Collaboration

## 9.1 Git/SVN Synchronization (.repositories/)

### Structure

```
.noveltrad/.repositories/
├── git/
│   └── le_chateau_anime.git/    # Git bare repository
│       ├── HEAD
│       ├── config
│       └── ...
└── svn/
    └── le_chateau_anime/        # Working copy
        ├── source/
        ├── tm/
        └── glossary/
```

### Workflow

```
1. git Pull
   └── Synchroniser avec dépôt distant (pull)

2. git Add + Commit
   └── Ajouter(Local changes → staging)

3. git Push
   └── Synchroniser avec dépôt distant (push)

4. Auto-backup
   └── create snapshot before push
```

### UI Git Interface

```
┌────────────────────────────────────────────────────────┐
│               Gestion de Version (Git)                │
├────────────────────────────────────────────────────────┤
│  Dépôt distant :                                       │
│  https://github.com/user/noveltrad-project.git        │
│                                                        │
│  branche : [main▼]                                     │
│                                                        │
│  Status :                                              │
│  [✓] Mise à jour complète (2026-02-26 14:30)          │
│  [○] Aucun changement local                            │
│                                                        │
│  Actions :                                             │
│  [Pull] [Add] [Commit] [Push]                         │
│                                                        │
│  Historique :                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 2026-02-26 14:30 user Add chapter 7              │  │
│  │ 2026-02-26 12:15 user Update glossary            │  │
│  │ 2026-02-26 09:00 user Initial import            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  [Ouvrir le dépôt] [Fermer]                           │
└────────────────────────────────────────────────────────┘
```

## 9.2 Partage par Disque Partagé

### Structure

```
\\shared-server\noveltrad-projects\
├── le_chateau_anime\
│   ├── source/
│   ├── tm/
│   ├── glossary/
│   └── ...
└── sunlight_after_rain\
    ├── source/
    ├── tm/
    └── ...
```

### Règles

1. **Locking** : Mettre un fichier `.lock` pendant modifications
2. **Snapshots** : Prendre snapshot avant envoi
3. **TMX Sharing** : Partager `tm/export/` pour TM commune
4. **No Dropbox/OneDrive** : Not recommended for active projects

---

# 10. Sauvegardes et Restauration

## 10.1 Snapshots Automatiques

### Intervalle

- **Par défaut** : 3 minutes
- **Configurable** : 1-60 minutes

### Archi

```
snapshots/
├── 2026-02-26_14-30-15/      # Snapshot 1
│   ├── project.json
│   ├── tm/
│   │   └── project_save.tmx
│   ├── glossary/
│   │   └── glossary.txt
│   └── notes/
│       └── chapter_001/
│           └── segment_001.txt
├── 2026-02-26_15-33-20/      # Snapshot 2
│   └── ...
└── 2026-02-26_16-45-00/      # Snapshot 10 (max)
    └── ...
```

### UI Snapshot

```
┌────────────────────────────────────────────────────────┐
│               Gestion des Snapshots                    │
├────────────────────────────────────────────────────────┤
│  Snapshots disponibles :                               │
│  [✓] 2026-02-26 14:30 (378K)                          │
│  [✓] 2026-02-26 15:33 (392K)                          │
│  [✓] 2026-02-26 16:45 (401K)                          │
│                                                        │
│  Actions :                                             │
│  [Restaurer] [Supprimer] [Exporter ZIP]               │
│                                                        │
│  Configuration :                                       │
│  Intervalle : [3▼] minutes                             │
│  Max snapshots : [10▼]                                │
│                                                        │
│  [Fermer]                                              │
└────────────────────────────────────────────────────────┘
```

## 10.2 Backup Avant Modification

### Principe

```
pre-modification/
├── pre-mod-segment_12345.tmx.bak
│   └── Backup segment avant modification
├── pre-mod-chapter_007.tmx.bak
│   └── Backup chapitre avant batch
└── pre-mod-project_20260226.json
    └── Backup project.json avant changement
```

### UI

```
┌────────────────────────────────────────────────────────┐
│              Backup Avant Modification                 │
├────────────────────────────────────────────────────────┤
│  [X] Activer les backups avant modification           │
│                                                        │
│  Dernier backup :                                      │
│  2026-02-26 14:28: pop mod-segment_12345.tmx.bak      │
│  2026-02-26 14:25: pop mod-project_20260226.json      │
│                                                        │
│  [Restaurer dernier backup]                            │
│                                                        │
│  [Fermer]                                              │
└────────────────────────────────────────────────────────┘
```

---

# 11. Raccourcis Clavier (100+)

## 11.1 Raccourcis Projet

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Nouveau projet | Ctrl+Shift+N | Créer projet vierge |
| Ouvrir projet | Ctrl+O | Ouvrir projet existant |
| Recharger projet | F5 | Recharger,Réeffet changements externes |
| Fermer projet | Ctrl+Shift+W | Fermer projet courant |
| Enregistrer projet | Ctrl+S | Sauvegarde immédiate |
| Créer fichiers traduits | Ctrl+D | Export EPUB/DOCX/PDF |
| Propriétés projet | Ctrl+E | Modifier langue, moteur, etc. |
| Fichiers source | Ctrl+L | Ouvrir fenêtre fichiers |
| Quitter | Ctrl+Q | Quitter l'application |

## 11.2 Raccourcis Édition

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Annuler | Ctrl+Z | Undo last command |
| Rétablir | Ctrl+Y | Redo last command |
| Remplacer par correspondance | Ctrl+R | Replace with fuzzy match |
| Insérer correspondance | Ctrl+I | Insert fuzzy match at cursor |
| Remplacer par source | Ctrl+Shift+R | Overwrite with source text |
| Insérer texte source | Ctrl+Shift+I | Insert source text at cursor |
| Sélectionner texte source | Ctrl+Shift+A | Select source text in target |
| Remplacer par traduction auto | Ctrl+M | Replace with MT suggestion |
| Insérer balises manquantes | Ctrl+Shift+T | Tag painter |
| Insérer prochaine balise manquante | Ctrl+T | Tag next missing |
| Exporter sélection | Ctrl+Shift+C | Export selected segment to file |
| Créer entrée glossaire | Ctrl+Shift+G | Create glossary entry |
| Rechercher | Ctrl+F | Open search window |
| Remplacer | Ctrl+K | Open replace window |
| Basculer casse | Shift+F3 | Cycle case (lower/upper/title/sentence) |

## 11.3 Raccourcis Navigation

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Segment suivant non traduit | Ctrl+U | Next untranslated segment |
| Segment traduit suivant | Ctrl+Shift+U | Next translated segment |
| Segment suivant | Ctrl+N / Enter | Next segment |
| Segment précédent | Ctrl+P / Ctrl+Enter | Previous segment |
| Aller au segment numéro... | Ctrl+J | Jump to segment # (dialog) |
| Note suivante | Ctrl+Alt+N | Next note |
| Note précédente | Ctrl+Alt+P | Previous note |
| Segment unique suivant | Ctrl+Shift+K | Next unique segment |
| Source de correspondance sélectionnée | Ctrl+Shift+M | Go to match source |
| Segment auto suivant (tm/auto) | Ctrl+Alt+, | Next auto-populated (auto) |
| Segment enforce suivant (tm/enforce) | Ctrl+Alt+. | Next enforced |
| Segment précédent (history) | Ctrl+Shift+P | Back in history |
| Segment suivant (history) | Ctrl+Shift+N | Forward in history |
| Aller au bloc-notes | Ctrl+Alt+9 | Jump to notes |
| Aller à l'éditeur | Ctrl+Alt+0 | Jump to editor |

## 11.4 Raccourcis de Navigation dans l'Éditeur

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Ouvrir menu contextuel | CONTEXT_MENU | Right-click menu |
| Segment suivant | TAB | Next segment |
| Segment précédent | Shift+TAB | Previous segment |
| Segment suivant (non tabulé) | ENTER | Next segment (unlock) |
| Segment précédent (non tabulé) | Ctrl+ENTER | Previous segment (unlock) |
| Insérer saut de ligne | Shift+ENTER | Insert line break |
| Tout sélectionner | Ctrl+A | Select all |
| Supprimer précédent token | Ctrl+BACKSPACE | Delete previous word |
| Supprimer suivant token | Ctrl+DELETE | Delete next word |
| Aller au premier segment | Ctrl+PAGE_UP | First segment |
| Aller au dernier segment | Ctrl+PAGE_DOWN | Last segment |
| Passer token suivant | Ctrl+RIGHT | Skip next token |
| Passer token précédent | Ctrl+LEFT | Skip previous token |
| Passer token avec sélection | Ctrl+Shift+RIGHT | Skip with selection |
| Verrouillage du curseur | F2 | Toggle cursor lock |
| Afficher saisie (overwrite) | INSERT / F3 | Toggle overtype mode |

## 11.5 Raccourcis Auto-completion

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Ouvrir auto-completion | Ctrl+SPACE | Trigger auto-complete |
| Afficher prochaines suggestions | Ctrl+SPACE | Next suggestions |
| Afficher suggestions précédentes | Ctrl+Shift+SPACE | Prev suggestions |
| Valider et fermer | ENTER | Confirm and close |
| Valider sans fermer | INSERT | Confirm without closing |
| Fermer | ESC | Cancel |
| Aller en haut de liste | UP | List up |
| Aller en fin de liste | DOWN | List down |
| Remonter d'une page | PAGE_UP | Page up |
| Descendre d'une page | PAGE_DOWN | Page down |

## 11.6 Raccourcis Alignment

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Réinitialiser paramètres | Ctrl+Shift+R | Reset parameters |
| Fermer aligneur | Ctrl+W | Close aligner |
| Glisser vers le haut | U | Move selection up |
| Glisser vers le bas | D | Move selection down |
| Fractionner | S | Split segment |
| Fusionner | M | Merge segments |
| Modifier | E | Edit segment text |
| Marquer accepté | A | Mark accepted |
| Marquer à vérifier | R | Mark to check |
| Effacer la marque | C | Clear mark |
| Réaligner éléments en attente | Ctrl+R | Realign pending |
| Démarrer alignement précis | SPACE | Precise alignment start |

## 11.7 Raccourcis Fuzzy Matches

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Choisir correspondance précédente | Ctrl+UP | Select previous fuzzy |
| Choisir correspondance suivante | Ctrl+DOWN | Select next fuzzy |
| Choisir correspondance #1 | Ctrl+1 | Select fuzzy #1 |
| Choisir correspondance #2 | Ctrl+2 | Select fuzzy #2 |
| Choisir correspondance #3 | Ctrl+3 | Select fuzzy #3 |
| Choisir correspondance #4 | Ctrl+4 | Select fuzzy #4 |
| Choisir correspondance #5 | Ctrl+5 | Select fuzzy #5 |

## 11.8 Raccourcis Recherche/Replace

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Aller au segment suivant (search) | Ctrl+N | Next match |
| Aller au segment précédent (search) | Ctrl+P | Prev match |
| Aller au segment dans l'éditeur | Ctrl+J | Go to editor |
| Synchronisation automatique | ✓ | Auto-sync with editor |
| Retour au segment initial | ✓ | Return to initial segment |

## 11.9 Raccourcis Dictionnaires

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Rechercher dans dictionnaires | Alt+Shift+D | Search dictionaries |
| Hotkey dans l'éditeur | - | Context menu only |

## 11.10 Raccourcis QA Check

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Afficher erreurs | Ctrl+Shift+V | Show errors |
| Afficher erreurs document actuel | - | Current file errors |
| Export rapport QA | - | Export PDF/HTML |

## 11.11 Raccourcis Affichage

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Colorer segments traduits | ✓ | Mark translated |
| Colorer segments non traduits | ✓ | Mark untranslated |
| Afficher délimitations de paragraphes | ✓ | Mark paragraph starts |
| Afficher segments sources | ✓ | Display source segments |
| Colorer segments répétés | ✓ | Mark non-unique segments |
| Surligner segments avec notes | ✓ | Mark noted segments |
| Afficher espaces insécables | ✓ | Mark NBSP |
| Afficher caractères d'espacement | ✓ | Mark whitespace |
| Afficher contrôles Bidi | ✓ | Mark Bidi controls |
| Surligner segments autotraduits | ✓ | Mark auto-populated |
| Souligner correspondances glossaire | ✓ | Mark glossary matches |
| Souligner problèmes vérificateur linguistique | ✓ | Mark grammar issues |
| Réinitialiser fenêtre | ✓ | Restore GUI layout |

## 11.12 Raccourcis Outils

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Afficher erreurs | Ctrl+Shift+V | Show errors |
| Statistiques | - | Show statistics |
| Aligner fichiers | - | Align files |
| Scripts | - | Open scripts window |

## 11.13 Raccourcis Options

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Préférences | - | Preferences dialog |
| Traduction automatique/récupération | ✓ | Auto-fetch MT |
| Glossaires/lemmatisation | ✓ | Use lemmatization |
| Dictionnaires/lemmatisation | ✓ | Use lemmatization |
| Saisie automatique/afficher suggestions | ✓ | Show suggestions |
| Saisie automatique/complétion historique | ✓ | History completion |
| Saisie automatique/prédiction historique | ✓ | History prediction |
| Filtres de fichiers | - | Setup file filters |
| Règles de segmentation | - | Setup segmentation |
| Éditeur | - | Workflow settings |
| Dossier de configuration | - | Access config folder |

## 11.14 Raccourcis Aide

| Action | Raccourci | Description |
|--------|-----------|-------------|
| Manuel d'utilisation | F1 | Help contents |
| À propos | - | About dialog |
| Dernières modifications | - | Last changes |
| Journal | - | Log |
| Rechercher des mises à jour | - | Check updates |

## 11.15 Raccourcis Per Device

### Linux/Windows

| Action | Raccourci | Note |
|--------|-----------|------|
| Ctrl | **Ctrl** | Control key |
| Alt | **Alt** | Alternative key |
| Maj | **Shift** | Shift key |
| Meta | **Ctrl** | Windows key |

### macOS

| Action | Raccourci | Note |
|--------|-----------|------|
| Cmd | **⌘** | Command key |
| Opt | **⌥** | Option key |
| Ctrl | **^** | Control key |
| Maj | **⇧** | Shift key |

---

# 12. Phases de Développement v1.1 (4-5 mois)

## Phase 1 – Fondations (4-6 semaines)

- [ ] Interface de base PyQt6 avec double panneau synchronisé
- [ ] Navigation entre segments (fuzzy pushes, glossary, etc.)
- [ ] Gestion de projets (création, ouverture, sauvegarde)
- [ ] Chargement de fichiers TXT, EPUB, DOCX
- [ ] Intégration NLLB via ctranslate2 (CPU+GPU)
- [ ] Traduction par segment et par lot (batch)
- [ ] Auto-completion glossaire de base
- [ ] Undo/Redo multi-niveau
- [ ] Thèmes clair/sombre

## Phase 2 – Format/Mémoire (4-6 semaines)

- [ ] Support EPUB avec préservation complète du formatage
- [ ] Support DOCX avec préservation complète du formatage
- [ ] Support PDF (import texte + export reconstruit)
- [ ] Intégration Argos Translate (MarianMT)
- [ ] Système de glossaires manuels complet (CRUD, import/export CSV/TSV/TBX)
- [ ] Mémoire de traduction basique (export/import TMX 1.4b)
- [ ] Alignement de base (alignment UI 3-colonnes - Viterbi)

## Phase 3 – IA et Interopérabilité (4-5 semaines)

- [ ] Intégration IA locale (LM Studio / Ollama) comme moteur de traduction
- [ ] Intégration IA en ligne (API OpenAI-compatible)
- [ ] Glossary AI : génération automatique de glossaire par IA avec prompts par genre
- [ ] Editor AI : raffinage des traductions machine par IA
- [ ] Structure AI : détection automatique des chapitres
- [ ] Chat contextuel IA
- [ ] Instructions personnalisées (Custom Instructions)
- [ ] Services web complémentaires (Google Translate, LibreTranslate)

## Phase 4 – Professional TAO (3-4 semaines)

- [ ] Structure `.noveltrad/` complète (OmegaT-compliant)
- [ ] tm/enforce, tm/auto, tm/mt, tm/penalty, tmx2source
- [ ] tmx sharing (partage par disque réseau)
- [ ] Project Sharing Git/SVN sync (.repositories/)
- [ ] 100+ raccourcis clavier (OmegaT-style)
- [ ] Search & Replace++ (Regex groups $1-$9, preview, filtering)
- [ ] Sauvegardes automatiques (snapshots 3-min, max 10)
- [ ] Backup avant modification

## Phase 5 – QA et Accessibilité (2-3 semaines)

- [ ] QA Check (balises, nombres, glossaire, grammaire)
- [ ] Export rapports QA (PDF/HTML)
- [ ] Validation des balises en temps réel
- [ ] Accessibilité (mode daltoniens, thèmes)
- [ ] Accessibilité (taille police, espacement)
- [ ] Aperçu en temps réel du rendu EPUB/DOCX (optionnel)
- [ ] Benchmarks de performance par moteur

## Phase 6 – Finalisation (2-3 semaines)

- [ ] Assistant de premier lancement pour configurer les modèles
- [ ] Gestion des erreurs robuste (timeouts, corruption, messages clairs)
- [ ] Mode "Secours" hors ligne total
- [ ] Export TMX sélectif (par chapitre, par statut, par date)
- [ ] Export glossaire TBX (ISO 30042)
- [ ] Documentation utilisateur complète
- [ ] Documentation développeur + hooks API
- [ ] Packaging en exécutable (PyInstaller)

## Phase 7 –Tests automatisés (continu)

- [ ] Tests unitaires (nllb, argos, tmx, glossary)
- [ ]Tests d'intégration (EPUB/DOCX, batch translation)
- [ ] Tests de compatibilité TMX avec OmegaT
- [ ] Tests de compatibilité TMX avec Trados/memoQ
- [ ] Tests de compatibilité TMX avec Wordfast
- [ ] Jeu de tests sur corpus de référence (xianxia, SF, etc.)
- [ ] Tests de performance (translation time, memory usage)

---

# 13. Stack Technique et API

## 13.1 Stack Principale

### Backend

| Bibliothèque | Version | Usage |
|-------------|---------|-------|
| Python | 3.10+ | Langage principal |
| PyQt6 | 6.5+ | Interface graphique |
| Peewee | 4.0+ | ORM SQLite |
| SQLite | 3.35+ | Base de données locale |
| ctranslate2 | 4.0+ | Traduction NLLB (CPU/GPU) |
| argostranslate | 1.7+ | Traduction MarianMT (Argos) |
| transformers | 4.35+ | LLM (local/online) |
| openai | 1.0+ | API OpenAI-compatible |
| ebooklib | 0.18+ | EPUB handling |
| python-docx | 0.8+ | DOCX handling |
| PyMuPDF | 1.22+ | PDF handling |

### Frontend

| Bibliothèque | Version | Usage |
|-------------|---------|-------|
| PyQt6 | 6.5+ | GUI principal |
| Qt Resources | - | Icons, stylesheets |
| Qt Language Manager | - | i18n (préparation v2) |

### DevOps

| Outil | Version | Usage |
|------|---------|-------|
| Git | 2.30+ | Version control |
| GitHub Actions | - | CI/CD |
| PyInstaller | 5.13+ | Packaging executable |
| Sphinx | 6.2+ | Documentation |

## 13.2 Structure de Code

```
noveltrad/
├── noveltrad.py                              # Entry point
├── main_window.py                            # Main window QMainWindow
├── project_manager.py                        # Project CRUD operations
├── formats/
│   ├── base_handler.py                       # Base handler interface
│   ├── txt_handler.py                        # TXT import/export
│   ├── epub_handler.py                       # EPUB import/export
│   ├── docx_handler.py                       # DOCX import/export
│   └── pdf_handler.py                        # PDF import/export
├── translation/
│   ├── engines/
│   │   ├── base_engine.py                    # TranslationEngine ABC
│   │   ├── nllb_engine.py                    # NLLB (ctranslate2)
│   │   ├── argos_engine.py                   # Argos Translate
│   │   ├── llm_engine.py                     # LLM (local/online)
│   │   └── online_engine.py                  # Online services
│   ├── translation_manager.py                # MT framework
│   └── batch_processor.py                    # Batch translation
├── ui/
│   ├── segment_card.py                       # Segment card widget
│   ├── editor_pane.py                        # Editor panel
│   ├── fuzzy_matches_pane.py                 # Fuzzy matches panel
│   ├── glossary_pane.py                      # Glossary panel
│   ├── dictionary_pane.py                    # Dictionary panel
│   └── mt_suggestions_pane.py                # MT suggestions panel
├── tm/
│   ├── tm_manager.py                         # Translation memory manager
│   ├── tmx_reader.py                         # TMX 1.4b reader
│   ├── tmx_writer.py                         # TMX 1.4b writer
│   └── alignment/                            # Alignment module
│       ├── __init__.py
│       ├── viterbi_aligner.py                # Viterbi algorithm
│       └── forward_backward_aligner.py       # Forward-Backward algorithm
├── glossary/
│   ├── glossary_manager.py                   # Glossary CRUD
│   ├── glossary_ai.py                        # Glossary AI generation
│   └── auto_complete.py                      # Auto-completion
├── search_replace/
│   ├── search_manager.py                     # Search framework
│   ├── replace_manager.py                    # Replace framework
│   └── regex_engine.py                       # Regex groups $1-$9
├── qa/
│   ├── qa_check.py                           # QA checks
│   ├── qa_report.py                          # Export PDF/HTML
│   └── tag_validator.py                      # Tag validation
├── backup/
│   ├── backup_manager.py                     # Backup framework
│   ├── snapshot_manager.py                   # Snapshot manager
│   └── pre_mod_backup.py                     # Pre-modification backup
├── sharing/
│   ├── git_manager.py                        # Git sync
│   └── network_sync.py                       # Shared disk sync
├── ai/
│   ├── editor_ai.py                          # Editor AI
│   ├── custom_instructions.py                # Custom instructions
│   └── chat_context.py                       # Chat context
├── utils/
│   ├── stats.py                              # Project statistics
│   ├── config.py                             # Project configuration
│   └── logger.py                             # Logging
├── resources/
│   ├── icons/
│   │   ├── segment_source.png
│   │   ├── segment_target.png
│   │   └── ...
│   ├── stylesheets/
│   │   ├── dark.qss
│   │   └── light.qss
│   └── templates/
│       ├── project_template.json
│       └── prompts/
│           ├── xianxia.json
│           └── ...
├── translations/
│   ├── noveltrad_fr.ts
│   └── noveltrad_en.ts (v2+)
├── tests/
│   ├── unit/
│   │   ├── test_nllb_engine.py
│   │   ├── test_tmx_write.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_epub_import.py
│   │   ├── test_batch_translation.py
│   │   └── ...
│   └── fixtures/
│       └── sample_texts/
├── docs/
│   ├── user_guide.md
│   ├── developer_guide.md
│   └── api_reference/
│       └── ...
└── setup.py                                   # PyInstaller packaging
```

## 13.3 API de Moteur de Traduction (TranslationEngine)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class TranslationEngine(ABC):
    """Interface unifiée pour tous les moteurs de traduction."""
    
    @abstractmethod
    def translate(
        self,
        text: str,
        src_lang: str,
        tgt_lang: str,
        glossary: Optional[Dict] = None,
        context: Optional[List[str]] = None,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Traduit un texte simple."""
        pass
    
    @abstractmethod
    def translate_batch(
        self,
        texts: List[str],
        src_lang: str,
        tgt_lang: str,
        glossary: Optional[Dict] = None,
        context: Optional[List[str]] = None,
        custom_instructions: Optional[str] = None
    ) -> List[str]:
        """Traduit une liste de textes en batch."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[tuple]:
        """Retourne les paires (code, nom) de langues supportées."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Nom du moteur."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie la disponibilité du moteur."""
        pass
    
    @abstractmethod
    def supports_context(self) -> bool:
        """Supporte-t-il le contexte (pour LLM) ?"""
        pass
    
    def supports_custom_instructions(self) -> bool:
        """Supporte-t-il les instructions personnalisées ?"""
        return False
    
    def get_engine_type(self) -> str:
        """Retourne le type de moteur."""
        return "unknown"
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation."""
        return {}
```

## 13.4 Hook API pour Plugins (v2+)

```python
class Plugin(ABC):
    """Interface pour les plugins."""
    
    @abstractmethod
    def get_name(self) -> str:
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        pass
    
    @abstractmethod
    def initialize(self, app):
        pass
    
    @abstractmethod
    def cleanup(self):
        pass

class TranslationEnginePlugin(Plugin):
    """Plugin pour moteur de traduction."""
    
    @abstractmethod
    def get_engine(self) -> TranslationEngine:
        pass

class FormatHandlerPlugin(Plugin):
    """Plugin pour gestion de formats."""
    
    @abstractmethod
    def supports_extension(self, ext: str) -> bool:
        pass
    
    @abstractmethod
    def load(self, path: str) -> List[Segment]:
        pass
    
    @abstractmethod
    def save(self, path: str, segments: List[Segment]):
        pass
```

---

# 14. Annexes

## 14.1 Exemples de Prompts Glossary AI

### xianxia

```json
{
  "name": "xianxia",
  "description": "Extraction de termes pour xianxia/cultivation",
  "prompt": "..."
}
```

### wuxia

```json
{
  "name": "wuxia",
  "description": "Extraction de termes pour wuxia/martial arts",
  "prompt": "..."
}
```

## 14.2 Exemple de Prompt Editor AI

```json
{
  "name": "editor_ai_refinement",
  "description": "Raffinage de la traduction pour fluidité et cohérence",
  "prompt": "Relis et améliore la traduction suivante pour fluidité et cohérence stylistique.\\n\\nGlossaire à respecter :\\n{glossary_json}\\n\\nTexte à raffiner :\\n{translated_text}\\n\\nRenvoie uniquement la traduction améliorée, sans commentaires."
}
```

## 14.3 RessourcesExternes

- **NLLB-200** : https://github.com/facebookresearch/fairseq/tree/nllb
- **ctranslate2** : https://github.com/OpenNMT/CTranslate2
- **Argos Translate** : https://github.com/argosopentech/argos-translate
- **CC-CEDICT** : https://www.mdbg.net/chinese/dictionary?page=cedict
- **JMdict** : https://www.edrdg.org/jmdict/j_jmdict.html
- **OmegaT** : https://omegat.org
- **TMX 1.4b** : https://www.gala-global.org/tmx-14b
- **TBX** : https://www.iso.org/standard/44600.html
- **PyQt6** : https://www.riverbankcomputing.com/software/pyqt/
- **ebooklib** : https://github.com/aerkalov/ebooklib
- **python-docx** : https://python-docx.readthedocs.io
- **PyMuPDF** : https://pymupdf.readthedocs.io

---

# Version Phone

**NovelTrad v3.0 - Cahier des charges**

- **Date** : 26 février 2026
- **Version** : 1.1-pre-alpha
- **Status** : En développement
- **Source** : https://github.com/user/noveltrad

**Contact** : marc@example.com

**Licence** : CC-BY-SA-4.0

---

*Document généré automatiquement à partir du cahier des charges v3.0*
*Format Markdown - Optimisé pour GitHub/GitLab*

# Planification et Suivi - Version 3.0 ( Toward OmegaT Compliance v1.1)

## Avancement

**Complétés pour v1.1 :**
- ✅ `ProjectStructure.create()` - COMPLET (13 sous-dossiers créés)
- ✅ `project_schema.py` - COMPLET (Pydantic v2.0+ BaseModel)
- ✅ `tm/enforce`, `tm/auto`, `tm/mt`, `tmx2source`, `tm/penalty-XX` - STRUCTURE CRééE
- ✅ `requirements.txt` - MISE À JOUR (pydantic>=2.0.0, watchdog>=3.0.0)
- ✅ `tests/` - 12/12 PASS

---

## Objectifs de la Session

- [x] Section 1: Structure de Projet - Dossier `.noveltrad/` complet
- [ ] Section 2: tm/enforce, tm/auto, tm/mt - Règles d'utilisation TM
- [ ] Section 3: Architecture projet `.noveltrad/` - Fichiers de configuration
- [ ] Section 4: Alignement UI++ - OpenFileDialog segmenté 3-colonnes
- [ ] Section 5: 100+ raccourcis - Navigation, translation, edit, project
- [ ] Section 6: Search/Replace++ - UI avancée avec groups, preview, filter
- [ ] Section 7: Project Sharing - Git/SVN sync, shared disk TMX
- [ ] Section 8: Documentation développeur - API, architecture, guide
- [ ] Section 9: Tests automatisés - Suite complète 100% key features

---

## Implémentation

### Semaine 1-2: Structure de Projet

#### Livrables conceptuels

- **Spécification ensemble** : `docs/architecture_project_structure.md` (300+ lignes)
- **Definition schema** : `docs/project_schema_v3.json` (validé JSON Schema)
- **Encryption strategy** : `docs/encryption_strategy.md` (sensible data protection)

#### Livrables techniques

- [x] **Créer dossier `.noveltrad/`** (avec `.gitignore` complet)
  ```powershell
  New-Item -ItemType Directory -Path ".noveltrad" -Force
  ```
- [x] **Implementer `project.json` (schema_version=3)**
  - Corriger (`creationtool` → `translationtool`)
  - Ajouter (`schema_version`: "3.0.0")
  - Champs obligatoires : `name`, `title`, `source_lang`, `target_lang`, `genres`, `source_format`, `default_engine`, `tm_settings`, `backup`, `accessibility`, `statistics`
  - Validation Pydantic v2 (`BaseModel`)
- [x] **Créer document `project_save.tmx` (TM principale)**
  - Header TMX 1.4 avec propriétés custom :
    ```xml
    <prop type="x-noveltrad:schema_version">3.0.0</prop>
    <prop type="x-noveltrad:genre">xianxia,fantasy</prop>
    <prop type="x-noveltrad:project_path">C:\Users\...\project</prop>
    ```
  - Insertion automatique des segments traduits
- [x] **Ajouter scripts de backup (auto every 3min)**
  - Script Python : `src/core/backup_manager.py` ( refactoring)
    - `BackupManager.create_snapshot(label="auto")`
    - `BackupManager.cleanup(max_snapshots=10)`
    - `BackupManager.get_latest_backup_path()`
  - Service Windows : `noveltrad-backup-service.ps1`
  - Détection changements : `watchdog` library integration

#### Livrables d'interface

- [x] **UI : Project Settings Dialog v3**
  - Onglet "Métadonnées" (`project.json`)
  - Onglet "Mémoire de traduction" (tm folders layout)
  - Onglet "Sauvegardes" (interval, max snapshots)
  - Onglet "Accessibilité" (thèmes, colorblind, font scale)
  -validation bouton [Enregistrer] qui write `.noveltrad/project.json`

---

### Semaine 3-4: tm/enforce, tm/auto, tm/mt

#### Architecture TM (OmegaT-compliant)

- **Établir structure de dossiers** :
  ```
  tm/
  ├── ENFORCE/             # Traductions exactes (100%), écrasement OUI
  │   └── bonus_translation.tmx
  ├── AUTO/               # Auto-insertion (fiabilité élevée), écrasement NON
  │   └── legacy_project.tmx
  ├── MT/                 # MT (surlignage rouge), écrasement NON
  │   ├── mt_quick.tmx
  │   └── penalty-030/    # Pénalité 30% sur scores
  │       └── less_reliable.tmx
  ├── TMX2SOURCE/         # Langue référence tierce
  │   └── ja-JP.tmx
  └── export/             # Emplacement TM export configuration
      └── project_save.tmx
  ```

#### Livrables techniques

- [ ] **Implementer `tm/auto` (exact match, auto-insert)**
  - Classe : `src/core/auto_tm_manager.py`
    ```python
    class AutoTMManager:
        def load_tmx_files(self, directory="tm/auto/")
        def search_exact_match(self, source_text) -> Optional[str]
        def insert_auto(self, segment) -> bool
        ```
  - Logique : `source_text == tm_source` → `target_text` auto-insert sans confirmation
  - UI : Marqueur gris clair (+ badge "Auto")

- [ ] **Implementer `tm/enforce` (écrase traductions)**
  - Classe : `src/core/enforce_tm_manager.py`
    ```python
    class EnforceTMManager:
        def load_tmx_files(self, directory="tm/enforce/")
        def enforce_translation(self, source_text) -> str
        def force_replace(self, segment, target_text) -> None
        ```
  - Logique : `100% score` → écrase le champ cible même si traduit
  - UI : Menu contextuel [Forcer translation] (rouge vif, validation explicite)

- [ ] **Implementer `tm/mt` (highlight rouge)**
  - Classe : `src/core/mt_manager.py`
    ```python
    class MTManager:
        def load_tmx_files(self, directory="tm/mt/")
        def get_mt_suggestions(self, source_text, threshold=50) -> List[dict]
        def mark_as_mt(self, segment, mt_data) -> None
        ```
  - Logique : `score < 100%` → surlignage rouge (#ff6b6b) + suffixe `[MT: 65%]`
  - UI : Status dropdown [Machine ▼] avec venteau scores

- [ ] **Implementer `tm/penalty-XX` (score fuzzy pénalisé)**
  - Classe : `src/core/fuzzy_scoring.py`
    ```python
    class FuzzyScorer:
        def calculate_score(self, s1, s2, penalty_percent=30) -> int
        def get_fuzzy_matches(self, source_text, threshold=75) -> List[dict]
        ```
  - Logique : `score_calculated - penalty_percent` → affichage score pénalisé
  - UI : Score affiché `[Fuzzy: 58% (78-20%)]`

#### Livrables d'interface

- [ ] **TM Explorer Panel**
  - TreeView : `tm/enforce | tm/auto | tm/mt | tmx2source`
  - Preview panneau : sélection L → source, sélection R → target
  - Actions : [Open], [Import], [Refresh], [Export Selected]

- [ ] **TM Status UI in SegmentCard**
  - Badge `Auto` (gris clair)
  - Badge `Enforce` (rouge vif)
  - Badge `MT: 65%` (jaune/orange)
  - Badge `Fuzzy: 58%` (violette)

---

### Semaine 5-6: Architecture projet `.noveltrad/`

#### Standard OmegaT-compliant

- **Catalogue complet des fichiers** :
  ```
  .noveltrad/
  ├── project.json              # Métadonnées (schema_version=3)
  ├── project_save.tmx          # TM principale
  ├── project_save.tmx.bak      # Pré-modification backup
  ├── project_save.tmx.timestamp.bak  # Snapshot timestamped (max 10)
  ├── project_stats.txt         # Statistiques globales (word count, % translated)
  ├── project_stats_match.txt   # Statistics par type de correspondance
  ├── project_stats_match_per_file.txt  # Stats par fichier
  ├── ignored_words.txt         # Spellcheck ignored words
  ├── learned_words.txt         # Spellcheck learned words
  ├── segmentation.conf         # Règles de segmentation spécifiques
  ├── filters.xml               # Filtres de fichiers spécifiques
  ├── uiLayout.xml              # Layout UI projet (panneaux dockés)
  ├── finder.xml                # Recherches externes
  ├── last_entry.properties     # Dernier segment visited (x-noveltrad:last_segment_id)
  └── .repositories/            # Sync Git/SVN (copie versionnée distante)
      ├── git/
      └── svn/
  ```

#### Livrables techniques

- [ ] **Implementer TMX export/import**
  - Classe : `src/core/tmx_handler.py` (refactoring v3)
    ```python
    class TMXHandler:
        def export_tmx_v3(segments, source_lang, target_lang, output_path, include_status=True, include_metadata=True)
        def import_tmx_v3(file_path, project, strategy="update_if_empty")
        ```
  - Support TMX 1.4b avec propriétés custom :
    ```xml
    <prop type="x-noveltrad:status">machine</prop>
    <prop type="x-noveltrad:engine">nllb-1.3b</prop>
    <prop type="x-noveltrad:timestamp">2026-02-26T14:30:00Z</prop>
    <prop type="x-noveltrad:chapter">chapter_007</prop>
    ```

- [ ] **Implementer `tmx2source` (3ème langue)**
  - Logique : Afficher TMX `ja-JP.tmx` sous source (anglais) pour référence
  - Classe : `src/core/tmx2source_manager.py`
    ```python
    class Tmx2SourceManager:
        def load_reference_tmx(self, tmx_path)
        def get_reference_text(self, source_text) -> Optional[str]
        def display_mode(self, mode="normal"|"reference_below")
        ```
  - UI : Toggle [▼ Reference below] dans HeaderPanel

- [ ] **Implementer `.repositories/` Git/SVN**
  - Classe : `src/core/vcs_manager.py`
    ```python
    class VCSManager:
        def init_git(self, path, remote_url)
        def sync_git(self, action="pull"|"push")
        def init_svn(self, path, repo_url)
        def sync_svn(self, action="update"|"commit")
        ```
  - Subprocess Python : `git.exe` / `svn.exe` path configurable
  - UI : Project Settings / Sync tab (remote URL, [Sync Now], [Log])

- [ ] **Créer document `last_entry.properties`**
  - Format Java Properties (OmegaT standard)
  - Contenu :
    ```
    # Last visited segment for each chapter
    chapter_007.last_segment=123
    last_project=C:\\Users\\...\project.ntrad
    last_session=2026-02-26T14:30:00Z
    ```
  - Réécriture automatique à chaque changement de segment
  - Acknowledgment on project load : "Session restored: segment #123 of chapter_007"

#### Livrables d'interface

- [ ] **Project Properties Dialog v3**
  - Onglet "Métadonnées" (title, description, languages, genres)
  - Onglet "Segmentation" (sentence/paragraph rules, local rules file)
  - Onglet "TM" (tm folders, fuzzy threshold, auto-propagate)
  - Onglet "Glossary" (auto-generation, prompt template, feedback loop)
  - Onglet "Sauvegardes" (interval, max snapshots, backup location)
  - Onglet "Sync" (Git/SVN remote URL, [Sync Now])

---

### Semaine 7-8: Alignement UI++

#### Standard OmegaT-aligner

- **Architecture alignement** :
  ```
  AlignmentDialog++
  ├── Left pane (Segment source)
  ├── Center pane (Segment target)
  ├── Right pane (Reference/aled)
  ├── Toolbar (Nav buttons, Split/Merge)
  └── Footer (Status, Word count, Confidence score)
  ```

#### Livrables techniques

- [ ] **Créer OpenFileDialog `AlignmentDialog++`**
  -fenêtre modale (non-blocking parent)
  - Coast-to-coast layout (QSplitter)
  - Style sombre/light adjustable

- [ ] **Implementar 3-colonnes view (Conserver, Source, Cible)**
  - Container : `QHBoxLayout` → `QWidget` (3 QStackedWidgets)
  - Conserver : segment original (read-only)
  - Source : segment source à traduire (highlight)
  - Cible : champ de traduction (input)
  - Sync scroll : `QScrollBar` binding

- [ ] **Implementar keyboard navigation (Ctrl+N, Ctrl+P)**
  - Classe : `src/gui/alignment_navigation.py`
    ```python
    class AlignmentNavigation:
        def next_segment(self) -> None
        def prev_segment(self) -> None
        def jump_to_segment(self, index) -> None
        def navigate_by_tag(self, direction="forward"|"backward") -> None
        ```
  - Raccourcis :
    - `Ctrl+N` : Next segment
    - `Ctrl+P` : Previous segment
    - `Ctrl+G` : Next missing tag
    - `Ctrl+T` : Previous tag

- [ ] **Implementar Split/Merge segments**
  - Split : Button [+] à côté de la source (détermine cursor position)
  - Merge : Button [−] à côté du segment suivant
  - Confirmation dialog : "Split into 2 segments?" / "Merge 2 segments?"

#### Livrables d'interface

- [ ] **Aligner UI Design**
  - Header : [Browse Source], [Browse Target], [Start Alignment]
  - Toolbar : [◄] [►] [＋] [−] [_LOCK_] (F2 lock)
  - Left : Source segment (read-only)
  - Center : Target segment (editable)
  - Right : Reference or aligned version
  - Footer : [Segment #], [Words: 12/15], [Confidence: 78%]

- [ ] **Alignment Actions Menu**
  - [Split segment at cursor]
  - [Merge with next segment]
  - [Mark segment as pair]
  - [Unmark segments]
  - [Export aligned TMX]

---

### Semaine 9-10: 100+ raccourcis

#### Catalogue complet raccourcis (OmegaT-style)

- **Navigation** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Segment suivant | `Ctrl+N` / `Enter` | Next segment |
  | Segment précédent | `Ctrl+P` / `Ctrl+Enter` | Previous segment |
  | Tooltip source | `F1` | Show tooltip source |
  | Tooltip target | `Shift+F1` | Show tooltip target |
  | Commentaire | `Ctrl+Alt+C` | Toggle comments panel |

- **Translation** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Traduction auto | `Ctrl+M` | Auto-translation (default engine) |
  | Insert fuzzy | `Ctrl+I` | Insert fuzzy match |
  | Remplacer par correspondance | `Ctrl+R` | Replace with match |
  | Traduction alternative | `Ctrl+Alt+T` | Create alternative translation |
  | Définir comme default | `Ctrl+Shift+T` | Set as default translation |

- **Edit** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Undo | `Ctrl+Z` | Undo last action |
  | Redo | `Ctrl+Y` / `Ctrl+Shift+Z` | Redo last action |
  | Copier | `Ctrl+C` | Copy selected text |
  | Couper | `Ctrl+X` | Cut selected text |
  | Coller | `Ctrl+V` | Paste text |

- **Search** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Recherche | `Ctrl+F` | Open search dialog |
  | Recherche suivante | `F3` | Next search match |
  | Recherche précédente | `Shift+F3` | Previous search match |
  | Replace | `Ctrl+H` | Open replace dialog |

- **Project** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Sauvegarder | `Ctrl+S` | Save current segment |
  | Enregistrer tout | `Ctrl+Shift+S` | Save all segments |
  | Exporter | `Ctrl+E` | Export project |
  | Nouveau projet | `Ctrl+N` | New project (conflict with next segment → rebind to `Ctrl+Shift+N`) |
  | Ouvrir projet | `Ctrl+O` | Open project |

- **Glossary** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Ouvrir glossaire | `Ctrl+Alt+G` | Open glossary panel |
  | Ajouter au glossaire | `Ctrl+G` | Add selected text to glossary |
  | Rechercher glossaire | `Ctrl+Alt+F` | Search glossary |

- **Dictionary** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Ouvrir dictionnaire | `Alt+Shift+D` | Open dictionary panel |
  | Rechercher mot | `Ctrl+D` | Search dictionary |

- **MT** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Ouvrir MT suggestions | `Ctrl+Alt+M` | Open MT panel |
  | Traduction MT | `Ctrl+Alt+T` | Translate with MT |

- **Notes** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Ouvrir notes | `Ctrl+Alt+N` | Open notes panel |
  | Ajouter note | `Ctrl+Alt+A` | Add note |

- **Alignment** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Ouvrir aligner | `Ctrl+Alt+A` | Open alignment dialog (conflict → rebind to `Ctrl+Shift+A`) |
  | Split segment | `Ctrl+Alt+S` | Split segment at cursor |

- **Alignment Navigation** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Next auto-populated | `Ctrl+Alt+,.` | Next auto-populated segment |
  | Prev auto-populated | `Ctrl+Alt+<` | Previous auto-populated |
  | Next enforced | `Ctrl+Alt+.` | Next enforced |
  | Prev enforced | `Ctrl+Alt+>` | Previous enforced |

- **Shortcuts only in tag mode** :
  | Action | Raccourci | Description |
  |--------|-----------|-------------|
  | Tag painter | `Ctrl+Shift+T` | Insert missing tags |
  | Next missing tag | `Ctrl+T` | Insert next missing tag |
  | Previous segment (history) | `Ctrl+Shift+P` | History back |
  | Next segment (history) | `Ctrl+Shift+N` | History forward |
  | Lock cursor | `F2` | Lock cursor in target field |

#### Livrables techniques

- [ ] **Modifier `src/core/shortcut_manager.py`**
  - Classe refactoring :
    ```python
    class ShortcutManager:
        def __init__(self, main_window)
        def init_shortcuts(self)
        def register_shortcut(self, action_name, keyseq, callback)
        def get_all_shortcuts(self) -> dict
        def save_shortcuts_to_file(self, path)
        def load_shortcuts_from_file(self, path)
        ```
  - Storage : `shortcuts.toml` (human-readable)
    ```toml
    [navigation]
    next_segment = "Ctrl+N"
    prev_segment = "Ctrl+P"
    
    [translation]
    auto_translate = "Ctrl+M"
    insert_fuzzy = "Ctrl+I"
    ```

- [ ] **Créer `ShortcutConfigDialog`**
  - UI : Table view (Action, Key Sequence, Edit button)
  - Actions : [Reset default], [Export], [Import], [Save]
  - Conflict detection : precedent check avant apply

#### Livrables d'interface

- [ ] **Keyboard Shortcuts UI**
  - Menu : `Options > Keyboard Shortcuts`
  - Search bar : filter shortcuts by action name
  - Export / Import button
  - Preview : Current key sequence display

- [ ] **Shortcuts Help Dialog**
  - Modal : `F1` dans main window
  - Categories tree : Navigation, Translation, Edit, Project, Glossary, Dictionary, MT, Notes, Alignment, Shortcuts only in tag mode
  - Copy to clipboard button

---

### Semaine 11-12: Search/Replace++

#### Architecture Search/Replace (OmegaT-style)

```
SearchReplaceDialog++
├── Search Pane 1 (Search text, options)
├── Search Pane 2 (Replace text, options)
├── Results Pane (Match list, preview)
└── Preview Pane (Source/Target/Notes)
```

#### Livrables techniques

- [ ] **Search UI++ (4 panes, Regex)**
  - Container : `QTabWidget` (4 tabs : Search, Replace, Results, Preview)
  - Search pane :
    - Text input : [____________________]
    - Options : `Case sensitive`, `Whole words`, `Regex`, `Match tags`
    - Scope : `Source`, `Target`, `Notes`, `All`
  - Replace pane :
    - Replace with : [____________________]
    - Group selection : `$1-$9` dropdown
    - Preview button : [Preview]
  - Results pane : `QTableView` (Match list, checkbox)
  - Preview pane : `QTextBrowser` (HTML preview)

- [ ] **Replace UI++ (preview, groups $1-$9)**
  - Regex groups connection :
    ```python
    def replace_with_groups(self, text, pattern, replacement) -> str:
        # support $1-$9 groups
        for i in range(9, 0, -1):
            replacement = replacement.replace(f"${i}", f"\\{i}")
        return re.sub(pattern, replacement, text)
    ```
  - Live preview : `QTimer` (500ms debounce)
  - Replace all / Replace selected buttons

- [ ] **Filtering options (source/target/notes)**
  - Scope selection : `QComboBox`
    - `Source text`
    - `Target text`
    - `Notes`
    - `Source + Target`
    - `All fields`
  - Filter button : [Filter results]
  - Export results button : [Export to CSV]

- [ ] **Synchronization Editor ↔ Search panel**
  - Sync scroll : When double-click result → jump to segment in editor
  - Sync selection : When select segment in editor → highlight in search results
  - Sync mode : Toggle [Sync with editor] checkbox

#### Livrables d'interface

- [ ] **Search/Replace UI Design**
  - Mode tabs : `[Search]`, `[Replace]`, `[Results]`, `[Preview]`
  - Search/Replace line edit with dropdown ( recent terms)
  - Regex-toggle button (bright indicator when enabled)
  - Match list : QListView with checkboxes
  - Preview : Syntax-highlighted HTML preview

- [ ] **Search Results Export**
  - Export as : `CSV`, `TXT`, `TMX`, `JSON`
  - Export options :
    - Include source
    - Include target
    - Include notes
    - Include context (±2 segments)

---

### Semaine 13-14: Project Sharing

#### Architecture Project Sharing (OmegaT Team Project)

- **Dossiers partagés** :
  ```
  shared_project/
  ├── .noveltrad/                # Local configuration (ignored by Git)
  │   ├── project.json          # Local overrides (user-specific)
  │   └── .repositories/
  │       ├── git/              # Git working copy
  │       └── svn/              # SVN working copy
  ├── source/                    # Shared source files
  ├── target/                    # Shared translations
  ├── tm/                        # Shared translation memory
  │   ├── enforce/              # Shared enforce TM
  │   ├── auto/                 # Shared auto TM
  │   └── mt/                   # Shared MT TM
  └── glossary/                  # Shared glossary
  ```

#### Livrables techniques

- [ ] **Shared disk TMX sharing**
  - Classe : `src/core/shared_disk_manager.py`
    ```python
    class SharedDiskManager:
        def sync_tmx(self, tmx_path, remote_path, strategy="merge"|"overwrite")
        def get_remote_tmx_status(self, remote_path) -> dict
        def merge_tmx(self, local_tmx, remote_tmx) -> dict
        ```
  - Conflict resolution : Last-write-wins / Timestamp priority
  - UI : Project Settings / Sync tab

- [ ] **Git sync integration**
  - Classe : `src/core/vcs_manager.py` (extension Git)
    ```python
    class GitManager:
        def init_repo(self, path, remote_url)
        def pull(self) -> bool
        def push(self) -> bool
        def get_status(self) -> dict
        def commit(self, message) -> bool
        def get_log(self, limit=10) -> List[dict]
        ```
  - Subprocess Python : `git.exe` (Windows) or `git` (Linux/Mac)
  - Auto-configure : `.gitignore` write à la création projet

- [ ] **SVN sync integration**
  - Classe : `src/core/vcs_manager.py` (extension SVN)
    ```python
    class SVNManager:
        def checkout(self, url, path)
        def update(self, path) -> bool
        def commit(self, path, message) -> bool
        def get_status(self, path) -> dict
        ```
  - Subprocess Python : `svn.exe`

- [ ] **External TMX loading**
  - Classe : `src/core/external_tm_manager.py`
    ```python
    class ExternalTMManager:
        def load_external_tmx(self, path, strategy="append"|"merge"|"replace")
        def get_external_tmx_paths(self) -> List[str]
        def remove_external_tmx(self, path)
        ```
  - UI : Project Settings / TM tab / External TMs section

#### Livrables d'interface

- [ ] **Project Sharing UI**
  - Tabs : `Local`, `Git`, `SVN`, `External TMX`
  - Git tab :
    - Remote URL : [____________________]
    - [Initialize Repo] [Connect to Repo]
    - [Pull] [Push] [Status]
    - Log viewer : QTableView (commit, author, date, message)
  - SVN tab :
    - Repository URL : [____________________]
    - [Checkout] [Update] [Commit]
    - Status : [Up to date] / [X commits ahead]
  - External TMX tab :
    - List : QListView (TMX files)
    - [Add] [Remove] [Reload]
    - Strategy dropdown : [Append] [Merge] [Replace]

- [ ] **Sync Status Indicator**
  - HeaderPanel : Icon + tooltip
    - ✓ : Synced
    - ⚠️ : X commits ahead
    - ✗ : Conflict detected
  - Info tooltip on hover : "Last sync: 2026-02-26 14:30 | Local changes: 2"

---

### Semaine 15-16: Documentation & Tests

#### Documentation développeur (v3.0)

- [ ] **Documentation API**
  - Docstrings Google style in all public methods
  - Auto-generate docs avec `sphinx` :
    ```bash
    pip install sphinx sphinx-rtd-theme
    sphinx-apidoc -o docs/api src
    make html
    ```

- [ ] **Architecture Guide**
  - `docs/architecture.md` (500+ lignes)
  - Sections :
    - Project structure
    - Core modules
    - GUI modules
    - Translation engines
    - TM system
    - Glossary system
    - Alignment system
    - Shortcuts system
    - Search/Replace system
    - Project sharing system

- [ ] **Developer Quick Start Guide**
  - `docs/developer_quick_start.md`
  - Sections :
    - Prerequisites (Python 3.10+)
    - Clone and setup
    - Run in dev mode
    - Run tests
    - Build executable
    - Contribute

#### Tests automatisés (100% coverage key features)

- [ ] **Unit tests (pytest)**
  - Structure :
    ```
    tests/
    ├── test_project_manager.py
    ├── test_translation_memory.py
    ├── test_glossary_manager.py
    ├── test_shortcut_manager.py
    ├── test_search_replace.py
    ├── test_alignment.py
    ├── test_tmx_handler.py
    ├── test_backup_manager.py
    └── test_vcs_manager.py
    ```

- [ ] **Integration tests**
  - End-to-end scenarios :
    - Create project → Import file → Translate segments → Export
    - Create project → Import TM → Auto-translate → Validate
    - Create project → Configure Git → Sync → Resolve conflict

- [ ] **Test suite execution**
  - Script : `run_tests.bat`
    ```batch
    @echo off
    python -m pytest tests/ -v --tb=short --cov=src --cov-report=html
    ```
  - Coverage report : `htmlcov/index.html`

- [ ] **EPUB/DOCX validation**
  - Test files :
    - `tests/fixtures/epub/sample.epub`
    - `tests/fixtures/docx/sample.docx`
  - Validation script : `tests/validate_formats.py`
    - Parse EPUB → Extract → Recreate → Compare
    - Parse DOCX → Extract → Recreate → Compare

- [ ] **Benchmark performance**
  - Script : `tests/benchmark.py`
    - Import time (100, 1000, 10000 segments)
    - Translation time (NLLB, Argos, LLM)
    - TM search time (1000, 10000 entries)
    - Export time (EPUB, DOCX, PDF, TXT)
  - Report : `docs/performance_benchmark.md`

#### Livrables techniques

- [ ] **Update `.agents/rules/rules.md`** (si nécessaire)
  - Ajouter section "Version 3.0 checklist" (coche-liste vérification)

- [ ] **Changelog v3.0**
  - `CHANGELOG.md` avec format Keep a Changelog
    ```markdown
    # Changelog

    ## [3.0.0] - 2026-02-26
    ### Added
    - OmegaT-compliant `.noveltrad/` structure (COMPLET)
    - TM enforcement (tm/enforce) with overwrite capability (STRUCTURE CRééE)
    - Auto TM insertion (tm/auto) with grey marker (STRUCTURE CRééE)
    - MT suggestions (tm/mt) with red highlight (STRUCTURE CRééE)
    - Fuzzy scoring with penalty system (tm/penalty-XX) (STRUCTURE CRééE)
    - tmx2source (third language reference) (STRUCTURE CRééE)
    - Alignment dialog++ (3-columns view, split/merge)
    - 100+ keyboard shortcuts
    - Advanced Search/Replace (preview, groups, filter)
    - Git/SVN project sharing
    ```

- [ ] **Version tagging**
  - Commande Git :
    ```powershell
    git tag -a v3.0.0 -m "Version 3.0: OmegaT Compliance"
    git push origin v3.0.0
    ```

#### Livrables d'interface

- [ ] **About Dialog v3**
  - Tabs : `Overview`, `Changelog`, `License`, `Third-party licenses`
  - Build info : `v3.0.0 | 2026-02-26 | Git commit: abc123`
  - Links : [Website], [Documentation], [Report bug]

- [ ] **Welcome Wizard v3**
  - Scrollable list of new features
  - Interactive tutorial (optional)
  - Skip button

---

## Révision

### Checklist finale (exigé par `.agents/rules/rules.md`)

- [ ] **Test suite pass** : `pytest tests/` (12/12 key features tests PASS)
- [ ] **Logs propres** : Aucun `WARNING` ou `ERROR` à l'exécution
- [ ] **Code élégant** : Follow PEP 8, type hints, docstrings
- [ ] **OmegaT-compliant** : Standard TMX 1.4b, `.noveltrad/` structure
- [ ] **Documentation complète** : API docs, architecture guide, quick start
- [ ] **Performance validated** : Benchmark report < 5s for 1000 segments
- [ ] **Formats validés** : EPUB/DOCX round-trip test pass
- [ ] **Changelog updated** : `CHANGELOG.md` with v3.0.0 changes
- [ ] **Version tagged** : Git tag `v3.0.0`

### pledged a perpetual gratitude to the users who report bugs

> " Every bug reported is a gift that helps us build a better tool. Thank you for making NovelTrad better for everyone. "


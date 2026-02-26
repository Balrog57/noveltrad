# Leçons Apprises (Memory)

## Modèles d'Erreurs Récents
- **Erreur** : `AttributeError: 'DictionaryManager' object has no attribute 'has_language'`
  - **Cause** : La méthode manquait dans `DictionaryManager` pour vérifier la présence d'une langue au sein d'une DB locale, déclenchant un crash de l'UI sur appel de `load_languages_into_footer`.
  - **Solution** : Ajouter `@staticmethod def has_language(...) -> bool` permettant une requête peewee `.exists()` sur `GlobalDictionaryTerm`.
- **Erreur** : `deep-translator library not found`
  - **Cause** : Dépendance manquante dans l'environnement.
  - **Solution** : Exécuter `pip install deep-translator` pour activer les fonctions de fallback Google.
- **Concept** : Les dialogues UI (Custom Instructions, Concordancer, Search/Replace) étaient préparés mais leurs "slots" Qt et leurs accès via `MainWindow` n'existaient pas. Il faut systématiquement vérifier si l'Action Menu est associée à son handler Python.
- **Règle UI** : Éviter la redondance stricte. Si une action est présente avec une icône visuelle évidente (Undo, Redo, Save) dans le header, elle doit être retirée des menus textuels pour garder une interface "Propre" et éviter la confusion de "double action".
- **PyQt Naming** : Faire attention aux noms de méthodes intégrées. Utiliser toujours `statusBar()` (méthode) au lieu de tenter d'instancier un membre `status_bar` par erreur de nommage, ce qui mène à des `AttributeError`.

## Nouveaux Concepts et Patterns (Refactorisation)
- **Modularisation GUI** : L'extraction de la logique dans des contrôleurs nécessite une vigilance sur les branchements de signaux. Pour les widgets enfants (Header/Footer/Tools), l'attachement direct des widgets critiques à l'instance `MainWindow` (ex: `self.main_window.dict_input = ...`) simplifie l'accès depuis les contrôleurs sans introduire de couplage excessif ou de proxys complexes.
- **Gestion des Dépendances Facultatives** : Les modules comme `PyQt6-WebEngine` ne sont pas toujours inclus par défaut dans les bundles PyQt de base. Il est crucial de vérifier leur présence au démarrage ou de les lister explicitement dans `requirements.txt` pour éviter des `ImportError: QtWebEngine` au premier lancement.
- **Routage des Menus** : Lors d'une migration vers des contrôleurs, le fichier `mainwindow.py` perd ses méthodes locales. Chaque action de `create_menu_bar` doit être explicitement redirigée vers `self.controller.method` pour éviter des `AttributeError` silencieuses jusqu'à l'activation du menu.

## Concepts et Patterns

#### Concept : tm/enforce vs tm/auto vs tm/mt (OmegaT-style)
**Description** : Trois niveaux de confiance pour les mémoires de traduction :
- `tm/enforce/` : Exact match 100%, écrase traductions existantes SANS confirmation
- `tm/auto/` : Exact match 100%, insert AUTO sans préfixe, BUT pas d'écrasement
- `tm/mt/penalty-XX/` : Score fuzzy réduit de XX%, surlignage rouge

**Impact** : Permet de gérer des TM de différentes fiabilités dans un même projet.

---

#### Concept : tmx2source (langue référence tierce)
**Description** : Affiche une 3ème langue juste sous le segment source pour référence.
- Fichier : `tm/tmx2source/JA-JP.tmx` (pour japonais)
- Condition : Exact match ONLY
- Usage : Progression anglais→français via japonais (ex: web novels)

**Usage** : Structure = `LL-PP.tmx` où LL=langue de référence, PP=code arbitraire.

---

#### Pattern : Project Structure .noveltrad/ (OmegaT-compliant)
**Description** : Structure de projet séparant données utilisateur du code :

```
project.noveltrad/
├── .noveltrad/          # Configuration système (.gitignore, secrets)
├── source/             # Fichiers à traduire
├── target/             # Fichiers exportés
├── tm/                 # Mémoires de traduction (enforce/auto/mt/penalty/tmx2source)
├── glossary/           # Glossaires (modifiable + référence)
├── dictionary/         # Dictionnaires (StarDict, Lingvo DSL)
└── .repositories/      # Sync Git/SVN (copie versionnée distante)
```

**Avantage** : Portabilité, backup facile, collaboration.

---

#### Pattern : Pre-modification Backup (OmegaT)
**Description** : Sauvegarde avant chaque modification de segment.

**Logique** :
1. User clique "Edit" → Save Before Save
2. BackupManager.create_snapshot(label="pre_modification")
3. Post-modification → Save to project_save.tmx
4. Cleanup : max 10 timestamped backups

**Avantage** : Refonte complète en cas d'erreur.

---

#### Pattern : 100+ Raccourcis (OmegaT)
**Description** : Navigation/translation/edit/project shortcuts.

**Catégories** :
- Navigation : Ctrl+U (next untranslated), Ctrl+J (jump to search), F2 (lock cursor)
- Translation : Ctrl+M (auto-translation), Ctrl+I (insert fuzzy), Ctrl+R (replace)
- Edit : Ctrl+G (create glossary), Ctrl+F (search), Ctrl+K (replace)
- Project : Ctrl+S (save), Ctrl+D (export), Ctrl+E (properties)

**Implémentation** : ShortcutManager.py + QShortcut + keymap.json

---

#### Pattern : tm/penalty-XX/ (Score fuzzy reduction)
**Description** : Réduction de score fuzzy pour TM de moindre fiabilité.

**Exemple** : TMs dans `tm/mt/penalty-030/` → score -30%
- Exact match 100% → devient 70%
- Fuzzy match 85% → devient 55%

**Usage** : Fondu progressif de fiabilité TM.

---

#### Pattern : tmx2source (3rd language reference)
**Description** : Affiche langue tierce sous segment source.

**Format** : `LL-PP.tmx` (ex: `JA-JP.tmx` pour japonais)

**Usage** : Passage anglais→français via japonais pour web novels.

---

#### Pattern : SegmentCard (UI moderne)
**Description** : Vue segmentée en "cartes" avec badge statut, color coding.

**Éléments** :
- Header : ID segment, badge status
- Content : Source (read-only), Target (editable)
- Footer : Word count, help text
- Color coding : Untranslated (gris), Machine (orange), AI (blue), Validated (green)

**Avantage** : UX intuitive, feedback visuel clair.

---

#### Pattern : Architecture Controllers (séparation view/business)
**Description** : Architecture PyQt6 avec contrôleurs extraits de MainWindow.

**Structure** :
- `src/gui/controllers/project_controller.py`
- `src/gui/controllers/ai_controller.py`
- `src/gui/controllers/tm_controller.py`
- `src/gui/controllers/editor_controller.py`
- `src/gui/controllers/tools_controller.py`

**Avantage** : Testabilité, maintenance, réutilisabilité.

---

#### Pattern : Git/SVN Sync (.repositories/)
**Description** : Synchronisation Git/SVN en arrière-plan.

**Structure** :
```
.repositories/
├── git/     # Clone local du dépôt distant
└── svn/     # Checkout local du dépôt SVN
```

**Usage** : Projet équipe, sync asynchrone, conflict resolution.

---

#### Pattern : Backup Manager (snapshots)
**Description** : Snapshots automatiques avec rotation.

**Features** :
- Auto every 3 minutes
- Max 10 snapshots (rotation automatique)
- Restore from any snapshot
- Label custom (auto, pre_major_change, user_request)

**Avantage** : Sauvegarde robuste pour traduction longue.

---

#### Pattern : Gestion TM par niveau de fiabilité
**Description** : Organisation des TM par niveau de fiabilité avec étiquettes distinctes.

**Étiquettes** :
- tm/enforce/ : Exact match 100%, écrase traductions existantes
- tm/auto/ : Exact match 100%, insert AUTO sans confirmation
- tm/mt/ : Surlignage rouge, pas d'écrasement
- tm/penalty-XX/ : Score fuzzy −XX%
- tmx2source/ : Langue tierce exact match ONLY

**Usage** : Gestion TM de différentes fiabilités dans un même projet.

---

#### Pattern : Fuzzy Scoring avec Pénalité
**Description** : Algorithme OmegaT (LMS - Levenshtein Modified Score) avec pénalités configurables.

**Logique** :
1. Nettoyage (suppression balises)
2. Lemmatization (optionnel)
3. Calcul Levenshtein
4. Score final avec pénalité appliquée

**Implémentation** : fuzzy_scoring.py + penalty configuration via dossier `tm/mt/penalty-XX/`.

---

#### Pattern : Glossary AI avec Feedback Loop
**Description** : Génération automatique de glossaire par IA avec correction utilisateur et amélioration itérative.

**Flux** :
1. Extraction termes importants (personnages, lieux, concepts)
2. Génération traductions par LLM avec prompt genre-specific
3. Validation utilisateur (UI table with status: validated/suggested/rejected)
4. Stockage dans glossary.txt + historique de feedback

**Avantage** : Terminologie cohérente, apprentissage continu, adaptation genre.

---

#### Pattern : OpenFileDialog Alignement 3-colonnes
**Description** : Interface d'alignement visuelle avec source, cible et référence.

**Architecture** :
- Left pane (Segment source)
- Center pane (Segment target)
- Right pane (Reference/aled)
- Toolbar (Nav buttons, Split/Merge)
- Footer (Status, Word count, Confidence score)

**Usage** : Alignement de textes parallèles pour création TM, correction manuelle, validation.

---

#### Pattern : Search/Replace++ avec Regex Groups
**Description** : Interface avancée de recherche/remplacement avec support regex groups ($1-$9) et preview en temps réel.

**Fonctionnalités** :
- 4 panneaux : Search, Replace, Results, Preview
- Detection de conflits raccourcis
- Sync editor ↔ search panel
- Export résultats (CSV, TXT, TMX, JSON)
- Preview HTML syntax-highlighté

**Avantage** : Recherche puissante, correction batch, feedback visuel immédiat.

---

#### Pattern : 100+ Keyboard Shortcuts Catalogue
**Description** : Catalogue complet de raccourcis clavier organisés par catégories.

**Catégories** :
- Navigation : Ctrl+N/P (prev/next segment), F2 (lock cursor)
- Translation : Ctrl+M (auto-translation), Ctrl+I (insert fuzzy), Ctrl+R (replace)
- Edit : Ctrl+Z/Y (undo/redo), Ctrl+F (search), Ctrl+G (glossary)
- Project : Ctrl+S (save), Ctrl+E (export), Ctrl+O (open)
- Alignment : Ctrl+Alt+A (open alignment), Ctrl+Alt+S (split)
- Tag mode : Ctrl+Shift+T (tag painter), Ctrl+T (next missing tag)

**Implémentation** : ShortcutManager.py avec load/save to shortcuts.toml.

---

## Références Techniques

- [OmegaT v6.1.0] : Standard de référence pour les mémoires de traduction TMX 1.4b - https://omegat.org/
- [TMX 1.4b Specification] : standard d'échange pour mémoires de traduction - https://www.kde.org/fileupload/8311/tmx14b.pdf
- [PyQt6 Documentation] : Framework GUI pour interface desktop - https://www.riverbankcomputing.com/static/Docs/PyQt6/
- [ctranslate2] : Moteur inference rapide pour modèles NLLB - https://github.com/OpenNMT/CTranslate2
- [argos-translate] : Bibliothèque traduction rapide MarianMT - https://github.com/argosopentech/argos-translate
- [Viterbi Algorithm] : Algorithme alignement séquences (segmentation) - https://en.wikipedia.org/wiki/Viterbi_algorithm
- [Levenshtein Distance] : Algorithme calcul correspondance floue - https://en.wikipedia.org/wiki/Levenshtein_distance
- [Git Documentation] : Gestion version distributed - https://git-scm.com/doc
- [SVN Documentation] : Gestion version centralisée - https://subversion.apache.org/docs/
- [Python Pathlib] : Manipulation chemins cross-platform - https://docs.python.org/3/library/pathlib.html
- [Pydantic v2] : Validation données Python - https://docs.pydantic.dev/latest/
- [Sphinx] : Génération documentation API - https://www.sphinx-doc.org/en/master/
- [pytest] : Framework tests Python - https://docs.pytest.org/en/stable/
- [coverage.py] : Mesure couverture tests - https://coverage.readthedocs.io/en/stable/

---

## Préférences de l'Utilisateur

- **Architecture** : Separator view/business via contrôleurs (architecture PyQt6 clean)
- **Interface** : Segmented view (SegmentCard), dark/light themes, colorblind mode support
- **TM System** : OmegaT-compliant tm/enforce, tm/auto, tm/mt, tm/penalty-XX, tmx2source
- **Backup Strategy** : Snapshots auto every 3 min, max 10 snapshots, pre-modification backup
- **Glossary** : AI generation + manual editing + feedback loop, CSV/TSV/TBX export
- **Shortcuts** : 100+ raccourcis organisés par catégories (navigation, translation, edit, project)
- **Alignment** : UI 3-colonnes interactive avec split/merge segments, keyboard navigation
- **Search/Replace** : Regex groups ($1-$9), preview interface, sync with editor
- **Project Sharing** : Git/SVN sync via .repositories/, shared disk TMX
- **Documentation** : API docs (Sphinx), architecture guide, developer quick start
- **Testing** : 100% coverage key features, pytest + coverage.py + benchmark suite
- **Format Support** : EPUB/DOCX/PDF output, round-trip validation, TMX 1.4b standard

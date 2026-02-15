# Plan d'Implémentation NovelTrad

# But du Projet
Créer une application de bureau (Windows) pour la traduction de romans et web novels (TAO - Traduction Assistée par Ordinateur).
L'application doit permettre :
- L'import de fichiers (TXT, EPUB, DOCX, PDF).
- La traduction phrase par phrase ou paragraphe par paragraphe.
- L'utilisation de moteurs de traduction automatique (NLLB via ctranslate2, Argos) et d'IA (LLM via OpenAI API local/online).
- **Le support multi-langues (Source/Cible) pour tous les projets et dictionnaires.**
- La gestion de glossaires (par projet et globaux/dictionnaires).
- L'export au format d'origine en conservant la mise en forme (EPUB/DOCX).

## User Review Required
> [!IMPORTANT]
> **Support Multi-langues** : L'interface de création de projet inclura désormais la sélection des langues source et cible (ex: Chinois -> Français, Anglais -> Allemand, etc.).
> **Dictionnaires** : Ajout d'une gestion de dictionnaires globaux indépendants des projets pour supporter le multi-langue.

## Structure du Projet (MVC)
- **Model** : Base de données SQLite (Peewee ORM) pour stocker les projets, segments, et glossaires.
- **View** : Interface PyQt6 (MainWindow, Editor, Settings).
- **Controller** : Logique métier (ProjectManager, TranslationEngines, FormatHandlers).

## Phases de Développement

### Phase 1 : Initialisation et GUI de base
- [x] Structure du projet et environnement virtuel.
- [x] Fenêtre principale (MainWindow) avec menus.
- [x] Widget d'édition bilingue (EditorWidget).
- [x] **Dialogue de création de projet (Intégré dans ProjectManager/Settings).**

### Phase 2 : Gestion des Formats
- [x] Classe abstraite `FormatHandler`.
- [x] Implémentation `TxtHandler`.
- [ ] **Implémentation `EpubHandler` (Avancé : Préservation formatage/images/CSS via ebooklib).**
- [x] Implémentation `DocxHandler` (Basique).
- [ ] **Implémentation `DocxHandler` (Avancé : Préservation styles via python-docx).**
- [ ] **Implémentation `PdfHandler` (Extraction texte + Export simple).**

### Phase 3 : Moteurs de Traduction
- [x] Interface `TranslationEngine`.
- [x] Intégration `ctranslate2` (NLLB) - *Fonctionnel*.
- [x] Intégration `LLMEngine` (OpenAI/Ollama) - *Fonctionnel*.
- [ ] **Intégration `Argos Translate` (Mode offline léger).**
- [x] UI de configuration des moteurs.

### Phase 4 : Données, Glossaires et Dictionnaires
- [x] Modèles de données (Project, Segment, Glossary, Dictionary).
- [ ] **[CRITYQUE] Implémentation du modèle `Chapter` et refonte ProjectManager.**
- [x] **Gestionnaire de Dictionnaire Global (Multi-langues).**
- [x] **Gestionnaire de Glossaire Projet.**
- [ ] **Import de dictionnaires tiers (CC-CEDICT, JMdict).**
- [ ] **Glossary AI (Génération automatique des termes via LLM).**
- [ ] **Mémoire de Traduction (TM) - Recherche et Fuzzy Matching.**

### Phase 5 : Fonctionnalités Avancées (IA & Tools)
- [ ] **Editor AI (Raffinage de traduction).**
- [ ] **Structure AI (Découpage de chapitres).**
- [ ] **Traduction en lot (Batch Processing).**
- [ ] **Statistiques et estimations de coûts.**

### Phase 6 : Verification et Packaging
- [ ] Tests unitaires et d'intégration complets.
- [ ] Packaging avec PyInstaller.
- [ ] Documentation utilisateur.

## Verification Plan
### Automated Tests
- `pytest tests/` pour valider la logique des handlers et des moteurs.
- Tests d'intégration pour le flux complet (Création projet -> Import -> Traduction -> Export).
- **Validation manuelle des formats exportés (EPUB/DOCX) pour la préservation du style (Images, CSS, Table des matières) - Réf: SPECS.md Section 6.**

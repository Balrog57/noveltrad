# GEMINI.md - Cerveau Persistant de NovelTrad

Ce document sert de guide de contexte et de mémoire technique pour l'agent Gemini CLI. Il doit être maintenu à jour après chaque changement structurel ou résolution de bug critique.

## 🚀 Contexte Projet
**Nom du projet** : NovelTrad
**Description** : Une application de bureau CAT (Computer Assisted Translation) haute performance spécialisée pour la traduction de romans (Web Novels, EPUB, etc.). Elle combine des outils TAO traditionnels (TMX, glossaires, concordancier) avec des moteurs d'IA modernes (OpenAI, TranslateGemma, Argos, NLLB).
**Version courante** : v0.4  
**Objectif prochain** : v1.1 (OmegaT-compliant) en 4-5 mois  
**Cahier des charges** : `specifications document v3.md` (TM/enforce, tm/auto, tm/mt, tmx2source, 100+ shortcuts, 16 semaines)

### 🛠 Stack Technique
- **Langage** : Python 3.10+
- **Interface** : PyQt6 (Native Desktop)
- **Base de données** : SQLite via Peewee ORM
- **Formats supportés** : EPUB (EbookLib), DOCX (python-docx), PDF (PyMuPDF), TXT, TMX (XML), XLIFF.
- **Moteurs IA/Traduction** : 
  - Offline : Argos Translate, NLLB (ctranslate2), TranslateGemma (via LM Studio/API).
  - Online : OpenAI API, DeepL.
- **Segmentation** : NLTK (punkt) et Grammalecte.

### 🏗 Architecture
Le projet suit une structure modulaire :
- `src/gui/` : Interface utilisateur (MainWindow, composants, styles, dialogues).
    - `src/gui/panels/` : Composants UI modulaires (Header, Footer, Tools).
- `src/gui/controllers/` : Logique métier extraite de la vue :
    - `ProjectController` : Cycle de vie du projet.
    - `AIController` : Services d'intelligence artificielle.
    - `TMController` : Mémoire de traduction globale.
    - `EditorController` : Gestion des chapitres et segments (Éditeur).
    - `ToolsController` : Dictionnaire, Concordancier, QA.
- `src/core/` : Logique métier (gestionnaire de projet, segmentation, mémoires de traduction, base de données, backup, tm managers, glossary, concordancer).
- `src/engines/` : Moteurs de traduction (NLLB, Argos, LLM, GlossaryAI).
- `src/formats/` : Parseurs de fichiers (EPUB, DOCX, PDF, TXT, TMX).

**Structure projetOmegaT-compliant** : `.noveltrad/`
- `project_save.tmx` : TM principale
- `tm/enforce/`, `tm/auto/`, `tm/mt/`, `tm/penalty-XX/`
- `tmx2source/` : 3ème langue référence
- `.repositories/` : Sync Git/SVN

---

## 📜 Registre des Erreurs Documentées (Erreurs & Solutions)

#### ERREUR : `ImportError: QtWebEngine` ou `QtWebEngineWidgets`
- **CAUSE** : Le module `PyQt6-WebEngine` est séparé du package `PyQt6` principal et manquait dans l'environnement.
- **SOLUTION** : Installation via `pip install PyQt6-WebEngine` et ajout au `requirements.txt`.

#### ERREUR : `AttributeError: 'MainWindow' object has no attribute 'X'` après refactorisation
- **CAUSE** : Les actions du menu ou les raccourcis pointaient vers des méthodes locales de `MainWindow` qui ont été déplacées dans les contrôleurs.
- **SOLUTION** : Router les appels via l'instance de contrôleur appropriée (ex: `self.project_ctrl.method`) dans `MainWindow.py`.

#### ERREUR : `AttributeError: undo_action` dans `HeaderPanel`
- **CAUSE** : Le panneau tentait d'accéder à des objets `QAction` supprimés de `MainWindow` au profit de méthodes de contrôleur.
- **SOLUTION** : Connecter directement les signaux `clicked` des boutons du header aux méthodes `self.main_window.editor_ctrl.undo`.

#### ERREUR : `AttributeError: 'ToolsPanel' object has no attribute 'right_stack'`
- **CAUSE** : `AIController` tentait d'accéder à un membre `right_stack` inexistant lors de l'ouverture du chat.
- **SOLUTION** : Renommer l'accès en `self.main_window.tools_panel.stack` et intégrer le `ChatWidget` dans le `QStackedWidget` du `ToolsPanel`.

#### ERREUR : Déploiement version 3.0 -respect rules.md
- **CAUSE** : Respect strict des règles de `.agents/rules/rules.md` pour maintien de l'état du projet.
- **SOLUTION** : Création systématique/après chaque session:
  - `specifications document v3.md` (cahier des charges OmegaT-compliant v3.0)
  - `tasks/todo.md` (plan d'action 16 semaines vers OmegaT v1.1)
  - `tasks/lessons.md` (micro-apprentissages & patterns)

#### ERREUR : `pydantic_core._pydantic_core.ValidationError` sur `ProjectSchema`
- **CAUSE** : Le champ `name` du validateur Pydantic n'acceptait que le pattern `^[a-zA-Z0-9_-]+$` (nom interne restrictif), alors que la fonction `create_project` y injectait le nom saisi par l'utilisateur contenant potentiellement des espaces ou caractères spéciaux.
- **SOLUTION** : Nettoyage et transformation du `name` via `re.sub(r'[^a-zA-Z0-9_-]', '_', name)` avant injection dans `ProjectSchema`, tout en conservant le nom saisi par l'utilisateur pour le champ `title`.

---

## 📝 Usage du Répertoire
- `/src` : Code source principal.
- `/tasks` : Suivi des tâches (`todo.md`) et leçons (`lessons.md`).
- `/resources` : Icônes et thèmes CSS.
- `/tests` : Suite de tests unitaires et d'intégration.

# GEMINI.md - Cerveau Persistant de NovelTrad

Ce document sert de guide de contexte et de mémoire technique pour l'agent Gemini CLI. Il doit être maintenu à jour après chaque changement structurel ou résolution de bug critique.

## 🚀 Contexte Projet
**Nom du projet** : NovelTrad
**Description** : Une application de bureau CAT (Computer Assisted Translation) haute performance spécialisée pour la traduction de romans (Web Novels, EPUB, etc.). Elle combine des outils TAO traditionnels (TMX, glossaires, concordancier) avec des moteurs d'IA modernes (OpenAI, TranslateGemma, Argos, NLLB).

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
- `src/core/` : Logique métier (gestionnaire de projet, segmentation, mémoires de traduction, base de données).
... (rest of architecture remains) ...

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

---

## 📝 Usage du Répertoire
- `/src` : Code source principal.
- `/tasks` : Suivi des tâches (`todo.md`) et leçons (`lessons.md`).
- `/resources` : Icônes et thèmes CSS.
- `/tests` : Suite de tests unitaires et d'intégration.

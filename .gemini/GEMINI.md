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
    - `src/gui/controllers/` : Logique métier extraite de la vue (Project, AI, TM).
- `src/core/` : Logique métier (gestionnaire de projet, segmentation, mémoires de traduction, base de données).
- `src/engines/` : Adaptateurs pour les différents moteurs de traduction.
- `src/formats/` : Gestionnaires d'import/export pour les différents formats de fichiers.
- `src/utils/` : Utilitaires transversaux (logging, tags, connectivité).

---

## ⚙️ Building and Running

### Commandes Clés
- **Installation** : `pip install -r requirements.txt`
- **Lancement (Dev)** : `python src/main_qt.py`
- **Tests** : `pytest tests/`
- **Build Exécutable** : `.\Build-NovelTrad-Qt.bat` (Génère `dist/NovelTrad/NovelTrad.exe`)
- **Création Installateur** : Compiler `NovelTrad.iss` avec Inno Setup.
- **Formatage** : `black .` et `isort .`
- **Linting** : `flake8 .`

---

## 📐 Conventions de Développement
1. **Encodage** : TOUJOURS utiliser `encoding='utf-8'` pour toute manipulation de fichier.
2. **Thread Safety** : Ne jamais bloquer le thread principal (UI). Utiliser `QThread` ou `asyncio` avec signaux Qt pour les opérations longues (API, chargement gros TMX).
3. **Typage** : Utiliser les type hints Python pour toute nouvelle fonction.
4. **Balises Internes** : Ne jamais modifier les balises XML internes (`<bpt>`, etc.) lors du traitement des segments.
5. **Gestion de la RAM** : Utiliser des parsers itératifs (`iterparse`) pour les fichiers TMX volumineux.
6. **Entités HTML** : Ne pas échapper les entités HTML deux fois (utiliser `html.unescape()` une seule fois).
7. **Accès Fichiers** : Tout accès fichier doit être enveloppé dans un `try/finally` avec fermeture explicite.

---

## 📜 Registre des Erreurs Documentées (Erreurs & Solutions)

#### ERREUR : `AttributeError: 'DictionaryManager' object has no attribute 'has_language'`
- **CAUSE** : Méthode manquante dans le manager pour vérifier l'existence d'une langue en DB avant chargement de l'UI.
- **SOLUTION** : Ajout de `@staticmethod def has_language(lang_code: str) -> bool` dans `src/core/dictionary_manager.py` avec une requête `.exists()`.

#### ERREUR : Crash au chargement de gros fichiers TMX
- **CAUSE** : Chargement complet de l'arbre DOM XML en mémoire.
- **SOLUTION** : Utilisation systématique de `xml.etree.ElementTree.iterparse` pour un traitement itératif.

#### ERREUR : `deep-translator library not found`
- **CAUSE** : Dépendance manquante pour les fallbacks de traduction.
- **SOLUTION** : Ajout à `requirements.txt` et installation via `pip install deep-translator`.

#### ERREUR : Orphelinat des Actions UI
- **CAUSE** : Les `QAction` du menu Qt n'étaient pas connectées à leurs méthodes respectives dans `mainwindow.py`.
- **SOLUTION** : S'assurer que chaque action créée dans `setup_menus` est liée via `action.triggered.connect(self.handler_method)`.

#### ERREUR : `AttributeError: 'MainWindow' object has no attribute 'status_bar'`
- **CAUSE** : Utilisation incorrecte de `self.status_bar` au lieu de `self.statusBar()` (méthode native PyQt).
- **SOLUTION** : Remplacer toutes les occurrences de `self.status_bar` par `self.statusBar()`.

---

## 📝 Usage du Répertoire
- `/src` : Code source principal.
- `/tasks` : Suivi des tâches (`todo.md`) et leçons (`lessons.md`).
- `/resources` : Icônes et thèmes CSS.
- `/tests` : Suite de tests unitaires et d'intégration.

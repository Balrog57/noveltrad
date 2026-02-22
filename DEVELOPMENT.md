# Directives de Développement - NovelTrad

## 🛠 Environnement & Commandes

- **Interpréteur** : Python 3.10+
- **Gestionnaire** : pip (venv)
- **Lancer l'app** : `python src/main_qt.py` ou `python -m src.main_qt`
- **Installation** : `pip install -r requirements.txt`
- **Formatage** : `black .` et `isort .`
- **Linting** : `flake8 .`

## 🏗 Architecture & Bibliothèques

- **Interface** : PyQt6
- **Fichiers TMX/XLIFF** : `xml.etree.ElementTree` (stdlib) - see `src/formats/`
- **Encodage** : TOUJOURS `encoding='utf-8'` lors de l'ouverture des fichiers
- **Segmentation** : `pygrammalecte` (intégré) pour grammaire, `nltk` pour sentences
- **Base de données** : `peewee` (SQLite)

### Structure du projet

```
src/
├── core/           # Logique métier (segmentation, fuzzy matching)
├── engines/        # Moteurs de traduction (DeepL, Google, OpenAI, ArgTranslate)
├── formats/        # Parsers TMX, XLIFF, EPUB, DOCX
├── gui/            # Interface PyQt6
└── utils/         # Helpers (logging, config)
```

## 🎨 Règles de Style (Pythonic)

- **Typage** : Utiliser les type hints (`def segment(text: str) -> list[str]:`)
- **Docstrings** : Format Google pour chaque fonction complexe
- **Async** : Utiliser `asyncio` pour les appels API (DeepL/OpenAI) afin de ne pas bloquer l'UI
- **GUI** : Toutes les opérations longues doivent être dans des threads séparés avec signaux Qt

## 🛑 Erreurs Critiques à Éviter (Mémoire de Correction)

### Règle #1 : Balises Internes
Ne JAMAIS modifier les balises internes des segments XML (ex: `<bpt>`, `<ept>`, `<it>`, `<ph>`). Ces balises sont des marqueurs de formatage et ne doivent jamais être altérées.

### Règle #2 : Entités HTML
Ne pas échapper les entités HTML deux fois. Utiliser `html.unescape()` une seule fois avant le traitement.

### Règle #3 : TMX Volumineux
Lors du chargement d'une mémoire de traduction (TMX) volumineuse, utiliser un parser itératif ( voir `xml.etree.ElementTree.iterparse`) pour éviter de saturer la RAM.

### Règle #4 : Encodage Fichiers
TOUJOURS spécifier `encoding='utf-8'` lors de l'ouverture de fichiers texte. Ne jamais relyer sur l'encodage par défaut du système.

### Règle #5 : GUI Thread Safety
Ne JAMAIS bloquer le thread principal avec des opérations réseau. Utiliser `QThread` ou `asyncio` avec signaux Qt.

## 🔧 Modules Clés

### `src/formats/tmx_handler.py`
- Charger/sauver fichiers TMX
- Utiliser `iterparse` pour gros fichiers

### `src/formats/xliff_handler.py`
- Support XLIFF 1.2 et 2.0
- Préserver les balises `<trans-unit>`

### `src/engines/`
- `deepl_engine.py` : API DeepL (async)
- `openai_engine.py` : GPT-based translation
- `argos_engine.py` : Modèles offline ArgTranslate

### `src/core/segmenter.py`
- Segmentation sentences avec NLTK punkt
- Conservation des balises inline

## 📋 Workflow

1. Avant de modifier le moteur de traduction, vérifie la règle de segmentation dans `core/segmenter.py`
2. Après chaque ajout de fonctionnalité, lance les tests dans `tests/`
3. Pour les grosses opérations (TMX > 10MB), utilise toujours le parser itératif
4. Tout accès fichier doit être enveloppé dans un `try/finally` avec close explicite

## ⚡ Commandes Utiles

```bash
# Lancer l'app
python src/main_qt.py

# Installer les dépendances
pip install -r requirements.txt

# Lancer les tests
pytest tests/

# Formatage
black src/ tests/
isort src/ tests/
```

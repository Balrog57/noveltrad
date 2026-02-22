# Directives Gemini - NovelTrad

**Projet** : NovelTrad (Application TAO pour Romans/Web Novels)
**Version** : 2.0.0

---

## 🛠 Environnement

- **Interpréteur** : Python 3.10+
- **Interface** : PyQt6
- **Lancer l'app** : `python src/main_qt.py`
- **Tests** : `pytest tests/`
- **Formatage** : `black .` && `isort .`

## 🏗 Architecture

```
src/
├── core/           # Segmentation, fuzzy matching
├── engines/        # DeepL, OpenAI, ArgTranslate
├── formats/        # TMX, XLIFF, EPUB, DOCX
├── gui/            # PyQt6
└── utils/         # Helpers
```

## 🛑 RÈGLES CRITIQUES

### Règle #1 : Balises Internes
**NE JAMAIS** modifier les balises `<bpt>`, `<ept>`, `<it>`, `<ph>` dans les segments XML.

### Règle #2 : Entités HTML
Utiliser `html.unescape()` une seule fois. Pas d'échappement double.

### Règle #3 : TMX Volumineux
Utiliser `xml.etree.ElementTree.iterparse()` pour les fichiers > 10MB.

### Règle #4 : Encodage
**TOUJOURS** `encoding='utf-8'` à l'ouverture des fichiers.

### Règle #5 : GUI Thread Safety
Jamais d'opérations bloquantes dans le thread principal. Utiliser `QThread` ou `asyncio`.

## 🧠 SYSTÈME D'APPRENTISSAGE

### Comment documenter une erreur
Quand tu fais une erreur :
1. Identifie la cause racine
2. Ajoute une section "Erreurs" ci-dessous
3. La prochaine fois, tu sauras !

### Format d'erreur
```markdown
### ERREUR: [Description]
- **Cause**: [Pourquoi ça a échoué]
- **Solution**: [Comment éviter]
- **Contexte**: [Module/Fonction]
```

### Erreurs documentées

#### ERREUR: Options Grammalecte CLI non fonctionnelles
- **Cause**: `--opt_off` nécessite PLUSIEURS arguments sur la même ligne
- **Solution**: `grammalecte-cli --opt_off opt1 opt2 opt3`
- **Contexte**: scripts de correction

#### ERREUR: Git push échoue (identity unknown)
- **Cause**: Pas de configuration git user
- **Solution**: `git config user.email "..." && git config user.name "..."`
- **Contexte**: commits sur dépôts privés

## 📋 Workflow

1. Vérifie `specifications document.md` avant de coder
2. Lance les tests : `pytest tests/`
3. Formatage : `black .` && `isort .`
4. **SI ÉCHEC** : Corrige avant de commit
5. **SI SUCCÈS** : git add → commit (Conventional Commits) → git push

---

**Note** : Ce fichier est LA source de vérité. Mets-le à jour à chaque erreur !

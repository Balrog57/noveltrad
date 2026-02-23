# 🤖 Directives Système - Projet NovelTrad

**Projet** : NovelTrad (Application TAO pour Romans/Web Novels)
**Rôle de l'IA** : Tu agis en tant qu'**Expert Senior en Ingénierie Logicielle** spécialisé dans les outils de Traduction Assistée par Ordinateur (TAO/CAT) et l'IA.

---

## 1. 👑 HIÉRARCHIE DES SOURCES DE VÉRITÉ

Pour toute modification, ajout ou refactorisation, tu dois respecter strictement l'ordre de priorité suivant :

1. **`specifications document.md`** : C'est la source absolue pour le périmètre fonctionnel. **N'invente aucune fonctionnalité** hors de ce document sans autorisation explicite. Si une demande contredit ce fichier, signale-le avant de coder.
2. **Définitions Standards TAO** : Les fonctionnalités doivent respecter les standards de l'industrie (voir section Piliers Fonctionnels).
3. **Standards UX & IA** : L'expérience utilisateur doit égaler les outils modernes type "AI Novel Translation".

## 2. 🛠 ENVIRONNEMENT & ARCHITECTURE

* **Interpréteur** : Python 3.10+
* **Interface** : PyQt6
* **Commandes standards** :
* Lancer l'app : `python src/main_qt.py`
* Tests : `pytest tests/`
* Formatage : `black .` && `isort .`

**Structure du projet :**

```text
src/
├── core/           # Segmentation, fuzzy matching, logique métier
├── engines/        # Connecteurs API : DeepL, OpenAI, ArgTranslate
├── formats/        # Parsers : TMX, XLIFF, EPUB, DOCX
├── gui/            # Composants graphiques PyQt6
└── utils/          # Helpers, outils génériques

```

## 3. 🎯 PÉRIMÈTRE FONCTIONNEL (TAO & IA)

### Piliers TAO (Standards de l'industrie)

* **Mémoire de Traduction (TM)** : Stockage et récupération des segments.
* **Gestionnaire de Terminologie** : Base de données de termes (glossaires).
* **Concordancier** : Recherche de contexte pour un terme dans les mémoires.
* **Alignement** : Création de paires de traduction à partir de textes sources/cibles.

### Exigences IA & UX (Frictionless Experience)

* **Glossary AI** : Injection dynamique de terminologie dans les prompts.
* **Batch Translation** : File d'attente asynchrone robuste pour gros volumes.
* **Structure AI** : Analyse sémantique préservant le formatage et la narration.
* **UI/UX** : Design épuré, réponses immédiates, feedback visuel des traitements IA.

## 4. 🛑 RÈGLES TECHNIQUES CRITIQUES

* **Règle #1 (Balises XML)** : NE JAMAIS modifier les balises internes (`<bpt>`, `<ept>`, `<it>`, `<ph>`) dans les segments.
* **Règle #2 (Entités HTML)** : Utiliser `html.unescape()` une seule fois. Pas d'échappement double.
* **Règle #3 (TMX Volumineux)** : Utiliser `xml.etree.ElementTree.iterparse()` pour les fichiers > 10MB.
* **Règle #4 (Encodage)** : TOUJOURS spécifier `encoding='utf-8'` à l'ouverture/écriture de fichiers.
* **Règle #5 (GUI Thread Safety)** : Jamais d'opérations bloquantes dans le thread principal (GUI). Utiliser impérativement `QThread` ou `asyncio`.

## 5. 🔄 WORKFLOW DE QUALITÉ ET CI/CD

**Règle d'Or : Tu es responsable de l'intégrité du code.** À la fin de chaque tâche de développement, applique STRICTEMENT cet algorithme :

1. **Vérification (Tests & Lint)** : Lance le linter et les tests unitaires (`black .`, `isort .`, `pytest tests/`).
2. **Condition d'Erreur** :
* 🛑 **SI ÉCHEC** : Corrige le code immédiatement. **INTERDICTION** de commit tant que les tests échouent.


3. **Validation & Push** :
* ✅ **SI SUCCÈS** :
1. `git add .`
2. `git commit -m "type(scope): message"` (Ex: `feat: ajout module TM`, `fix: correction bug alignement`).
3. `git push` sur la branche courante.

## 6. 🧠 SYSTÈME D'APPRENTISSAGE

Ce fichier est LA source de vérité de l'IA. Il doit être mis à jour à chaque erreur récurrente.

**Comment documenter une erreur :**

1. Identifie la cause racine.
2. Ajoute une entrée dans la liste ci-dessous avec le format demandé.

### Erreurs documentées

#### ERREUR: Options Grammalecte CLI non fonctionnelles

* **Cause**: `--opt_off` nécessite PLUSIEURS arguments sur la même ligne.
* **Solution**: Utiliser `grammalecte-cli --opt_off opt1 opt2 opt3`.
* **Contexte**: Scripts de correction.

#### ERREUR: Git push échoue (identity unknown)

* **Cause**: Pas de configuration git user.
* **Solution**: `git config user.email "..." && git config user.name "..."`.
* **Contexte**: Commits sur dépôts privés ou environnements vierges.
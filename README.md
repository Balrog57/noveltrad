# NovelTrad Desktop

Application de bureau pour la traduction assistée par ordinateur de romans et web novels, avec moteurs de traduction multiples, glossaires, mémoires de traduction et outils de QA.

## Fonctionnalités

- Application de bureau native en PyQt6.
- Support des formats EPUB, DOCX et TXT.
- Intégration de moteurs OpenAI-compatible, LM Studio, Argos et NLLB.
- Gestion de glossaires projet et de mémoires de traduction TMX.
- Outils d'alignement, concordancier et vérification qualité.
- Fonctionnement principal hors ligne, avec options IA locales ou cloud.

Pour des instructions d'utilisation détaillées, consultez le [Guide Utilisateur](docs/user_guide.md).

## Dépôt public et références locales

- Le dépôt GitHub public contient le code source, la documentation du projet et les ressources de l'application.
- `OmegaT_Doc/` sert de référence locale pour l'étude d'OmegaT, la rédaction du cahier des charges et le développement de NovelTrad.
- `OmegaT_Doc/` est volontairement ignoré par Git et ne doit pas être publié sur GitHub.
- `config.json`, les environnements virtuels, les caches et les autres fichiers générés restent locaux à la machine.
- La validation automatique du dépôt public repose actuellement sur une vérification de compilation de `src/` dans la CI.

## Installation (Développement)

1. Cloner le dépôt.
2. Créer un environnement virtuel :

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

3. Installer les dépendances :

```powershell
pip install -r requirements.txt
```

4. Lancer l'application :

```powershell
python src/main_qt.py
```

## Créer l'exécutable

Pour créer un fichier `.exe` autonome :

```powershell
.\Build-NovelTrad-Qt.bat
```

Cela génère `dist/NovelTrad/NovelTrad.exe`.

## Créer l'installateur

1. Installer [Inno Setup](https://jrsoftware.org/isdl.php).
2. Compiler `NovelTrad.iss`.

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" NovelTrad.iss
```

Cela crée `Output/NovelTrad_Setup.exe`.

## Structure du projet

- `src/gui/` : interface principale.
- `src/core/` : logique métier, projet, QA, TM et sauvegardes.
- `src/engines/` : moteurs de traduction.
- `src/formats/` : import/export des formats de documents.
- `resources/` : icônes et ressources UI.
- `docs/` : documentation utilisateur.

## Fonctionnalités TAO

- Mémoire de traduction (TM) avec import/export TMX.
- Glossaires projet et terminologie cohérente.
- Concordancier pour la recherche contextuelle.
- Alignement pour créer de la TM à partir de bitextes.
- QA Check pour la validation avant export.

## Licence

Voir le fichier `LICENSE` pour les détails.

# NovelTrad Desktop

Application de bureau haute performance pour la traduction de romans, avec suggestions alimentées par l'IA et gestion complète des glossaires. Répliquant la philosophie de design "Stitch" pour une expérience utilisateur premium.

## Fonctionnalités

- **Application de bureau native**: Développée avec PyQt6 pour la vitesse et l'intégration système.
- **Interface inspirée de Stitch**: Thème sombre moderne, navigation latérale, et éditeur de segments par cartes.
- **Support des formats**: EPUB, DOCX, TXT.
- **Intégration IA**: Support d'OpenAI, TranslateGemma (via LM Studio), Argos, et NLLB.
- **Optimisation TranslateGemme**: Moteur spécialisé pour `translategemma-12b-it` utilisant l'API Completion pour éviter les erreurs de template Jinja2 de LM Studio. Optimisé pour les GPU NVIDIA RTX (ex: RTX 5070 Ti) avec une fenêtre de contexte recommandée de 8192.
- **Gestion des glossaires**: Créer et gérer des glossaires spécifiques au projet.
- **Hors ligne**: Les fonctionnalités principales fonctionnent hors ligne ; les fonctionnalités IA nécessitent internet si utilisation d'API cloud ou peuvent fonctionner localement avec LM Studio.
- **Support TMX**: Import et export de mémoires de traduction au standard industriel.
- **Assurance qualité**: Vérifications automatiques et outil d'alignement.

Pour des instructions d'utilisation détaillées, consultez le [Guide Utilisateur](docs/user_guide.md).

## Installation (Développement)

1. **Cloner le dépôt**
2. **Créer un environnement virtuel**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```
3. **Installer les dépendances**:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Lancer l'application**:
   ```powershell
   python src/main_qt.py
   ```
5. **Lancer les tests**:
   ```powershell
   python -m pytest tests/
   ```

## Créer l'exécutable

Pour créer un fichier `.exe` autonome:

1. Exécuter le script de build:
   ```powershell
   .\Build-NovelTrad-Qt.bat
   ```
   Cela générera `dist/NovelTrad/NovelTrad.exe`.

## Créer l'installateur

Pour créer un fichier d'installation:

1. Installer [Inno Setup](https://jrsoftware.org/isdl.php).
2. Faire un clic droit sur `NovelTrad.iss` et choisir "Compile".
   OU exécuter:
   ```powershell
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" NovelTrad.iss
   ```
   Cela créera `Output/NovelTrad_Setup.exe`.

## Structure du projet

- `src/gui/`: Logique principale de l'interface (`mainwindow.py`, `components.py`, `styles.py`).
- `src/core/`: Modèles de base de données (`database.py`) et logique du projet (`project_manager.py`).
- `src/engines/`: Interfaces des moteurs de traduction (`llm_engine.py`, etc.).
- `src/formats/`: Parseurs de fichiers.

## Fonctionnalités TAO

NovelTrad est un outil TAO (Traduction Assistée par Ordinateur) complet:

- **Mémoire de traduction (TM)**: Réutilisation de traductions existantes
- **Glossaires**: Gestion de la terminologie cohérente
- **Concordancier**: Recherche contextuelle dans les TM
- **Alignement**: Création de TM à partir de bitextes
- **QA Check**: Validation automatique avant export

## License

Voir le fichier LICENSE pour les détails.

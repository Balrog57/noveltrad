# NovelTrad

**Application de Traduction Assistée par Ordinateur (TAO) pour Romans et Web Novels.**

NovelTrad est une application de bureau conçue pour aider les traducteurs de romans (Xianxia, Fantasy, Sci-Fi, etc.) à travailler efficacement grâce à une interface bilingue et l'intégration de moteurs de traduction IA (NLLB, LLM, OpenAI).

## Fonctionnalités Principales

*   **Interface Bilingue** : Édition côte à côte (Source / Cible) avec synchronisation du défilement.
*   **Multi-Moteurs** : Support de NLLB (Offline via CTranslate2) et LLM (Local via Ollama/LM Studio ou Online via OpenAI).
*   **Gestion de Projets** : Organisation par roman et chapitres.
*   **Glossaires & Dictionnaires** :
    *   Gestion de glossaires par projet.
    *   Dictionnaire global multi-langues.
*   **Formats Supportés** :
    *   Import : TXT, EPUB (Basique), DOCX.
    *   Export : TXT.
*   **Confidentialité** : Fonctionne entièrement en local (sauf si utilisation d'API en ligne).

## Installation

### Prérequis

*   Python 3.10+
*   Git

### Installation Développement

1.  Cloner le dépôt :
    ```bash
    git clone https://github.com/VotreUsername/noveltrad.git
    cd noveltrad
    ```

2.  Créer un environnement virtuel :
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  Installer les dépendances :
    ```bash
    pip install -r requirements.txt
    ```

## Utilisation

1.  Lancer l'application :
    ```bash
    python src/main.py
    ```
2.  Créer un nouveau projet (Fichier -> Nouveau Projet).
3.  Importer un fichier (TXT ou EPUB).
4.  Configurer les moteurs de traduction (Outils -> Paramètres).
5.  Commencer à traduire !

## Architecture

Le projet suit une architecture MVC modulaire :
*   `src/core` : Logique métier et modèles de données.
*   `src/ui` : Interface utilisateur (PyQt6).
*   `src/engines` : Moteurs de traduction (Abstract, NLLB, LLM).
*   `src/formats` : Gestionnaires de formats de fichiers.

## Licence

[Votre Licence Ici]

# NovelTrad

NovelTrad est une application locale de **traduction littéraire assistée par intelligence artificielle**. Elle importe une œuvre, la normalise en Markdown GFM et WebP lossless, la traduit avec le fournisseur IA de votre choix, applique automatiquement une révision complète en quatre passes, puis exporte un résultat propre dans une archive ZIP éphémère contenant un Markdown unique et ses images WebP.

Conçue pour la confidentialité et la fiabilité, elle fonctionne avec Docker, stocke les données localement (SQLite + fichiers), et supporte **Ollama**, **LM Studio** et toute **API OpenAI-compatible**.

## Fonctionnalités

- **Import** : EPUB, DOCX, TXT, Markdown (`.md`) et SRT.
- **Normalisation immédiate et irréversible** : les textes sont convertis en GitHub Flavored Markdown, les images embarquées en WebP lossless ; aucun original n'est conservé.
- **Pipeline IA obligatoire en quatre passes** : traduction fidèle → révision linguistique → vérification contextuelle → finalisation, toujours au même modèle.
- **File d'attente FIFO persistante** : un seul appel par segment à la fois, pause/reprise propres, reprise sans perte après redémarrage (checkpoints atomiques).
- **Édition humaine** après finalisation : éditeur Markdown par chapitre logique, autosauvegarde, recherche et remplacement global sur le projet.
- **Export** : archive ZIP éphémère `noveltrad-<project_id>.zip` contenant le Markdown traduit assemblé et exactement ses images WebP référencées ; suppression automatique après téléchargement ou expiration (24 h).
- **Interface Streamlit FR/EN** : thèmes clair/sombre/sépia, responsive PC/tablette/smartphone, journaux filtrables, notification locale de fin de traduction (désactivable).
- **Local-first** : les fichiers restent sur votre machine, sauf appels volontaires à une API distante.

## Fournisseurs IA

| Fournisseur | URL par défaut |
|---|---|
| Ollama | `http://host.docker.internal:11434` |
| LM Studio | `http://host.docker.internal:1234/v1` |
| API OpenAI-compatible | `https://api.openai.com/v1` |

Les modèles Ollama et LM Studio installés sont détectés automatiquement. Les clés API sont chiffrées au repos (AES-256-GCM, clé dérivée d'`APP_PASSWORD` via Argon2id) et ne sont jamais journalisées ni exportées.

## Prérequis

- Docker avec Docker Compose
- 2 vCPU, 4 Gio de RAM et au moins 2 Gio d'espace libre avant import
- Un fournisseur IA (local ou distant)

## Démarrage rapide

Créez un fichier `.env` à côté de `compose.yaml` :

```dotenv
APP_PASSWORD=votre_mot_de_passe_tres_long_et_secure
# Facultatif : adresse d'écoute hôte (défaut 127.0.0.1) et port (défaut 8501)
# NOVELTRAD_BIND_ADDRESS=127.0.0.1
# NOVELTRAD_PORT=8501
```

Puis lancez l'application :

```bash
docker compose up -d
```

Ouvrez `http://127.0.0.1:8501`, saisissez `APP_PASSWORD`, choisissez la langue et le thème, puis configurez le fournisseur IA dans les Paramètres.

> **Sécurité d'exposition** : l'écoute est limitée à `127.0.0.1` par défaut. L'activation `0.0.0.0` est réservée à un usage derrière un VPN ou une terminaison TLS externe ; l'exposition HTTP directe sur LAN ou Internet est interdite.

### Options d'environnement

| Variable | Valeurs | Défaut |
|---|---|---|
| `APP_PASSWORD` | 16 à 256 points de code Unicode (obligatoire) | — |
| `NOVELTRAD_BIND_ADDRESS` | `127.0.0.1` ou `0.0.0.0` | `127.0.0.1` |
| `NOVELTRAD_PORT` | entier 1–65535 | `8501` |
| `NOVELTRAD_DATA_DIR` | chemin du volume de données | `/data` |
| `NOVELTRAD_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |

## Sauvegarde et restauration

Après arrêt de l'application, la sauvegarde complète requiert **deux opérations séparées** :

1. Copier le dossier de données (`database.sqlite`, `key.salt`, projets, etc.) ;
2. Sauvegarder `.env` séparément dans un emplacement chiffré (il contient `APP_PASSWORD`).

La restauration consiste à restaurer le dossier de données puis à restaurer ou recréer `.env` avant le redémarrage.

## Architecture

- **Monolithe modulaire** dans un **conteneur unique** : Streamlit (interface), Worker logique unique (file FIFO), SQLite (métadonnées) et système de fichiers (`source.md` immuable, `translated.md`, WebP, checkpoints internes).
- **Principes clés** : un projet = une œuvre ; `source.md` est immuable ; le pipeline complet est obligatoire ; une seule traduction active ; les exports sont temporaires ; toute écriture de `translated.md` est atomique ; les corrections humaines ne sont jamais écrasées.
- **Sécurité** : mot de passe unique via `APP_PASSWORD` (comparaison en temps constant, temporisation après échecs répétés), clés API chiffrées, journaux expurgés, analyses XML sans DTD/entités/réseau, archives traitées comme non fiables (limites de décompression, chemins confinés).

## Documentation

La référence technique complète et normative du projet est le [NovelTrad_SDD.md](NovelTrad_SDD.md) (Spécification détaillée : exigences EF-001 à EF-016, règles métier RM-001 à RM-012, architecture, modèle SQLite, pipeline, tests et traçabilité).

## Licence

**GNU Affero General Public License v3.0 uniquement (`AGPL-3.0-only`).** Le code source correspondant à toute version utilisée par interaction réseau reste accessible conformément à l'AGPL-3.0. Le lien « Licence et code source » de l'interface donne accès à ce dépôt.

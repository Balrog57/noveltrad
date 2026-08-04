# NovelTrad — Software Design Document

**Document maître unique — Version consolidée**

Ce document constitue la référence fonctionnelle et technique du projet NovelTrad. Toute évolution doit être intégrée ici avant son implémentation.

## Chapitre 1 — Vision, objectifs et périmètre

### 1.1 Vision

NovelTrad est une application locale de traduction littéraire assistée par intelligence artificielle. Elle permet de créer un projet, d’y importer une œuvre, de convertir automatiquement son contenu, de lancer un pipeline complet de traduction et de révision, puis d’exporter le résultat final.

### 1.2 Objectifs

- Simplicité d’installation, d’utilisation et de dépannage.
- Traduction fidèle nécessitant le moins possible de corrections humaines.
- Révision automatique obligatoire et intégrée au produit.
- Conservation locale des fichiers, sauf utilisation volontaire d’une API distante.
- Robustesse face aux interruptions et redémarrages.
- Architecture monolithique modulaire, sans complexité inutile.

### 1.3 Périmètre

- Création d’un projet représentant une œuvre.
- Import EPUB, DOCX, TXT, Markdown et SRT.
- Conversion automatique vers GitHub Flavored Markdown.
- Conversion des images vers WebP lossless.
- Réorganisation manuelle des chapitres.
- Traduction et révision automatiques.
- Édition du texte traduit après le pipeline.
- Export EPUB, DOCX, Markdown, TXT ou SRT.

### 1.4 Hors périmètre

- Multi-utilisateur et collaboration.
- Microservices, Redis, reverse proxy obligatoire.
- Exécution distribuée, multi-machine ou multi-GPU.
- Historique complet des versions.
- Conservation des fichiers originaux après conversion.
- Import ou export complet d’un projet NovelTrad.

### 1.5 Principes fondateurs

1. Un projet représente une seule œuvre.
2. `source.md` est immuable.
3. `translated.md` est le seul contenu éditable.
4. Le pipeline complet est obligatoire.
5. Une seule traduction est active à la fois.
6. Les exports sont temporaires.
7. Toute écriture de `translated.md` est atomique.
8. Les corrections humaines ne sont jamais écrasées automatiquement.

## Chapitre 2 — Principes d’architecture

NovelTrad est un monolithe modulaire composé des couches suivantes :

```text
Streamlit → Services métier → Repositories → SQLite / fichiers
                          ↘ Worker → Fournisseur IA
```

### Responsabilités

- Streamlit : affichage, navigation et collecte des actions.
- Services : application de toutes les règles métier.
- Repositories : accès exclusif à SQLite.
- Worker : exécution des traitements longs.
- Fournisseur IA : traduction et révision derrière une interface commune.

### Dépendances interdites

- Aucun SQL dans Streamlit ou les services.
- Aucun appel IA direct depuis Streamlit.
- Aucune logique métier dans les repositories.
- Aucun accès direct aux fichiers depuis l’interface.

### Transactions

- Toute modification métier est transactionnelle.
- `COMMIT` uniquement après succès complet.
- `ROLLBACK` automatique en cas d’échec.
- Les écritures de fichiers et SQLite restent cohérentes.

## Chapitre 3 — Exigences fonctionnelles

- **EF-001** — Créer un projet avec un nom libre et une langue cible.
- **EF-002** — Détecter automatiquement la langue source.
- **EF-003** — Accepter uniquement EPUB, DOCX, TXT, Markdown et SRT.
- **EF-004** — Convertir le texte en GFM et les images en WebP lossless.
- **EF-005** — Supprimer les originaux après conversion validée.
- **EF-006** — Conserver l’ordre de dépôt et permettre son réordonnancement.
- **EF-007** — Valider le projet avant traduction.
- **EF-008** — Exécuter quatre appels IA obligatoires.
- **EF-009** — Traiter une seule unité à la fois avec une file d’attente.
- **EF-010** — Permettre un arrêt propre après l’appel IA courant.
- **EF-011** — Autoriser l’édition uniquement après validation finale.
- **EF-012** — Rechercher et remplacer dans tout le projet.
- **EF-013** — Exporter l’œuvre complète dans un ou plusieurs formats.
- **EF-014** — Supprimer l’export après téléchargement.
- **EF-015** — Fournir une interface FR/EN et clair/sombre/sépia.
- **EF-016** — Afficher et filtrer les journaux dans l’interface.

## Chapitre 4 — Règles métier

- **RM-001** — Un projet représente exactement une œuvre.
- **RM-002** — Tout document présent appartient à l’export final.
- **RM-003** — `source.md` ne peut jamais être modifié.
- **RM-004** — `translated.md` est créé au lancement du pipeline.
- **RM-005** — Les corrections manuelles interviennent après le pipeline.
- **RM-006** — L’ordre pilote traduction, contexte et export.
- **RM-007** — Le projet est verrouillé pendant une traduction.
- **RM-008** — Le contexte reçoit le précédent traduit, le courant traduit et le suivant source.
- **RM-009** — Les délais de reprise sont 1, 5, 15, 30 et 60 secondes.
- **RM-010** — L’export est bloqué tant que tous les documents ne sont pas terminés.
- **RM-011** — Toute suppression destructive exige une confirmation renforcée.
- **RM-012** — Les paramètres IA ne changent pas pendant un traitement.

Cycle obligatoire :

```text
Import → Conversion → Validation → Traduction → Révision
→ Vérification contextuelle → Finalisation → Édition facultative → Export
```

## Chapitre 5 — Architecture logicielle

Services principaux :

- `AuthenticationService`
- `ProjectService`
- `DocumentService`
- `JobService`
- `TranslationService`
- `VerificationService`
- `ExportService`
- `SettingsService`
- `LogService`

Les services manipulent des objets métier et non des composants Streamlit. Les dépendances sont injectées pour permettre les tests.

## Chapitre 6 — Architecture Docker

Docker Compose est le mode de déploiement officiel.

### Conteneur

Un conteneur applicatif unique regroupe Streamlit et le Worker. Le fournisseur IA est externe ou distant.

### `.env`

Le fichier `.env` contient obligatoirement :

```env
APP_PASSWORD=mot_de_passe
```

Les paramètres fonctionnels sont stockés dans SQLite.

### Volume persistant

```text
data/
├── database.sqlite
├── logs/
└── projects/
```

La copie du dossier `data/` constitue une sauvegarde complète.

### Santé du conteneur

- SQLite accessible.
- Volume `data` accessible en lecture/écriture.
- Worker démarré.
- Configuration chargée.

## Chapitre 7 — Architecture Python

Python 3.12 minimum, type hints, Ruff et Pytest.

```text
app/
├── main.py
├── core/
├── ui/
├── modules/
│   ├── authentication/
│   ├── projects/
│   ├── documents/
│   ├── jobs/
│   ├── translation/
│   ├── verification/
│   ├── export/
│   ├── settings/
│   └── system/
└── tests/
```

Structure type d’un module :

```text
module/
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── exceptions.py
└── tests/
```

Aucune logique métier dans les callbacks Streamlit. Les API publiques possèdent des type hints et des docstrings.

## Chapitre 8 — Modèle de données SQLite

SQLite stocke uniquement les métadonnées.

### `projects`

- `id`
- `name`
- `source_language`
- `target_language`
- `status`
- `created_at`
- `updated_at`

### `documents`

- `id`
- `project_id`
- `display_name`
- `order_index`
- `source_path`
- `translated_path`
- `status`
- `pipeline_stage`
- `progress`
- `word_count`
- `character_count`
- `detected_language`
- `last_error`
- `updated_at`

La paire `(project_id, order_index)` est unique.

### `jobs`

- `id`
- `document_id`
- `state`
- `provider`
- `model`
- `retry_count`
- `started_at`
- `finished_at`

### Autres tables

- `settings`
- `logs`
- table de version de schéma

Les migrations sont versionnées, transactionnelles et non destructives.

## Chapitre 9 — Gestion des projets et documents

États projet : Brouillon, Prêt, En cours, En pause, Terminé, Erreur.

États document : À traduire, En cours, En pause, Terminé, Erreur.

- Le nom du projet est libre.
- La langue cible est unique par projet.
- La langue source est détectée automatiquement.
- L’ordre initial correspond au dépôt.
- Le glisser-déposer permet de réorganiser les documents.
- Les doublons de nom possèdent un identifiant interne distinct.
- La suppression d’un projet supprime ses données après confirmation.

## Chapitre 10 — Import et conversion

Pipeline :

```text
Copie temporaire → Analyse du format → Extraction → Conversion GFM
→ Conversion WebP lossless → Validation → Création source.md → Nettoyage
```

Contrôles :

- Markdown valide.
- Images référencées présentes.
- Liens internes cohérents.
- Langue détectée.
- Mots et caractères comptés.
- Aucune conservation de l’original.

## Chapitre 11 — Pipeline IA

Le même modèle est utilisé pendant les quatre appels.

1. **Traduction fidèle** : aucune omission ni ajout.
2. **Révision linguistique** : orthographe, grammaire, ponctuation et fluidité.
3. **Vérification contextuelle** : cohérence narrative et terminologique.
4. **Finalisation** : résultat complet, propre et prêt à éditer.

Les chapitres trop longs sont segmentés sans couper les blocs Markdown, paragraphes ou dialogues. Chaque résultat est validé et écrit atomiquement.

## Chapitre 12 — Worker et jobs

États internes : Waiting, Queued, Running, Paused, Retrying, Completed, Cancelled, Failed.

- File FIFO.
- Un seul job actif.
- Plusieurs chapitres peuvent être ajoutés en masse.
- L’arrêt attend la fin de l’appel courant.
- La reprise démarre à la dernière étape validée.
- Les étapes validées ne sont pas rejouées.
- Chaque changement d’état est enregistré.

Métriques : progression, étape, document, modèle, fournisseur, temps écoulé, estimation restante et nombre de jobs.

## Chapitre 13 — Interface utilisateur

### Premier lancement

1. Choix Français/English.
2. Choix clair/sombre/sépia.
3. Redirection vers Paramètres.

Les lancements suivants ouvrent la liste des projets.

### Écrans

- Connexion.
- Projets.
- Projet.
- Éditeur Markdown avec aperçu.
- Paramètres.
- Journaux.

L’interface est responsive et utilisable sur smartphone. Les tableaux sont triables et filtrables. Les états et progressions sont affichés clairement.

## Chapitre 14 — Paramètres et fournisseurs IA

Fournisseurs : Ollama, LM Studio, OpenAI, OpenRouter, Gemini, Claude, Grok et toute API OpenAI-compatible.

Paramètres globaux :

- langue et thème ;
- fournisseur ;
- URL ;
- clé API ;
- modèle ;
- paramètres compatibles avec le fournisseur.

Les modèles Ollama et LM Studio sont détectés automatiquement. Un bouton teste la connexion. Les secrets ne sont jamais journalisés.

## Chapitre 15 — Export

Formats : EPUB, DOCX, Markdown, TXT et SRT.

- Tous les documents doivent être terminés.
- Aucun job ne doit être actif.
- L’assemblage utilise `translated.md` selon `order_index`.
- Les images WebP sont intégrées.
- Le fichier est généré temporairement.
- Le téléchargement est immédiat.
- Le temporaire est supprimé après téléchargement.
- L’export ne modifie jamais le projet.

## Chapitre 16 — Journalisation, sécurité et robustesse

Niveaux : DEBUG, INFO, WARNING, ERROR, CRITICAL.

Chaque événement contient un horodatage UTC et, si pertinent, les identifiants du projet et du document.

- Aucun texte de chapitre dans les journaux.
- Aucun mot de passe ou secret affiché.
- Vérification SQLite au démarrage.
- Nettoyage des fichiers temporaires orphelins.
- Reprise sans perte des étapes validées.
- Journaux consultables depuis l’interface.

## Chapitre 17 — Tests et critères d’acceptation

- Tests unitaires des services.
- Tests d’intégration des flux complets.
- Tests d’interface PC et smartphone, FR et EN.
- Tests d’arrêt et reprise.
- Tests de migrations SQLite.
- Tests d’import massif et de Worker longue durée.
- Test de non-régression pour chaque correction de bug.
- 100 % des exigences critiques couvertes.

Aucune version n’est publiée si un test critique échoue.

## Chapitre 18 — Diagrammes et modèles

Diagrammes obligatoires :

- composants ;
- classes ;
- séquences ;
- états ;
- données SQLite ;
- cycle de vie d’un document ;
- cycle de vie d’un job.

Les diagrammes doivent rester synchronisés avec l’architecture. En cas de divergence, le texte normatif du SDD fait foi.

## Chapitre 19 — Exigences et traçabilité

Chaque exigence possède un identifiant `REQ-XXX`.

La matrice de traçabilité lie chaque exigence :

- au chapitre concerné ;
- au module Python ;
- à l’implémentation ;
- aux tests associés.

Toute nouvelle exigence est versionnée. Les exigences obsolètes restent historisées.

## Chapitre 20 — Annexes techniques

Les annexes regroupent :

- glossaire ;
- arborescence officielle ;
- conventions de nommage ;
- formats d’échange ;
- journal des décisions ;
- références techniques ;
- évolutions compatibles : nouveaux fournisseurs, nouveaux formats et optimisations du pipeline.

Le présent SDD est la référence technique unique du projet NovelTrad et doit rester synchronisé avec le code.
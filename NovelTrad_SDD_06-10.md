# NovelTrad — SDD

## Chapitres 6 à 10

# Chapitre 6 -- Architecture Docker

### 6.1 Déploiement officiel

Docker Compose est le mode officiel. Une commande doit suffire à
démarrer l'application.

### 6.2 Conteneur

Un conteneur applicatif unique regroupe Streamlit et le Worker. Le
fournisseur IA reste externe ou distant.

### 6.3 Environnement

.env contient APP_PASSWORD et éventuellement des options techniques.
Tous les paramètres fonctionnels sont dans SQLite.

### 6.4 Volume

Le volume data contient database.sqlite, logs et projects. Aucun export
n'est conservé.

### 6.5 Démarrage

Création des dossiers manquants, validation de APP_PASSWORD,
ouverture/migration SQLite et nettoyage des temporaires.

### 6.6 Arrêt

Fin de l'appel IA courant, sauvegarde atomique, mise à jour du job et
arrêt propre.

### 6.7 Sauvegarde et restauration

La copie du dossier data constitue une sauvegarde complète. Sa
restauration doit suffire à retrouver l'installation.

### 6.8 Mise à jour

Les migrations sont automatiques, transactionnelles et non destructives.
# Chapitre 7 -- Architecture Python

### 7.1 Objectif

Un projet Python unique, structuré en modules métier simples et
testables.

### 7.2 Environnement

Python 3.12 minimum, type hints, Ruff et Pytest. Les dépendances sont
gérées par uv ou pip.

### 7.3 Arborescence

app/main.py ; core/ ; ui/ ; modules/authentication, projects, documents,
jobs, translation, verification, export, settings, system ; tests/.

### 7.4 Structure d'un module

models.py, schemas.py, repository.py, service.py, exceptions.py et
tests/. Seuls les fichiers réellement utiles sont créés.

### 7.5 core

Base SQLite, transactions, chemins, journalisation, exceptions communes
et écritures atomiques. Aucun métier.

### 7.6 authentication

Lecture et validation de APP_PASSWORD sans persistance ni journalisation
du secret.

### 7.7 projects

Création, renommage, suppression, langue cible et état global.

### 7.8 documents

Import, conversion, ordre, statistiques, fichiers Markdown et images.

### 7.9 jobs

File FIFO, statut, progression, pause, reprise, erreur et récupération
après redémarrage.

### 7.10 translation

Segmentation, appels IA, reconstruction, politique de reprises et
sauvegarde.

### 7.11 verification

Révision linguistique, contexte et validation finale.

### 7.12 export

Assemblage, génération temporaire et nettoyage.

### 7.13 settings

Langue, thème, fournisseur, URL, clé, modèle, détection et test de
connexion.

### 7.14 system

Journaux, diagnostics, nettoyage et état du Worker.

### 7.15 Exceptions et tests

Exceptions métier explicites, injection des dépendances, fournisseurs et
système de fichiers simulables.
# Chapitre 8 -- Modèle de données SQLite

### 8.1 Objectif

SQLite est l'unique base de données de NovelTrad. Elle stocke uniquement
les métadonnées de l'application. Les contenus des chapitres restent
exclusivement dans source.md et translated.md.

### 8.2 Principes

La base contient les projets, documents, jobs, paramètres et journaux.
Aucun texte de chapitre ni image n'est enregistré dans SQLite.

### 8.3 Transactions

Toute modification est transactionnelle. En cas d'échec, un rollback
complet est effectué.

### 8.4 Intégrité

Les clés étrangères sont activées. Toutes les dates sont stockées au
format UTC ISO-8601.

### 8.5 Table projects

Colonnes : id, name, source_language, target_language, status,
created_at, updated_at.

### 8.6 Table documents

Colonnes : id, project_id, display_name, order_index, source_path,
translated_path, status, pipeline_stage, progress, word_count,
character_count, detected_language, last_error, updated_at. La paire
(project_id, order_index) est unique.

### 8.7 Table jobs

Colonnes : id, document_id, state, provider, model, retry_count,
started_at, finished_at. États : Queued, Running, Paused, Failed,
Completed.

### 8.8 Tables settings et logs

settings stocke les paramètres globaux. logs enregistre les événements
sans jamais contenir de secret ni le texte des chapitres.

### 8.9 Index

Indexes recommandés : projects(name), documents(project_id,order_index),
documents(status), jobs(state), logs(created_at).

### 8.10 Invariants

SQLite est l'unique source des métadonnées. Les suppressions sont
transactionnelles. Un projet supprimé supprime ses documents, jobs et
journaux associés.
# Chapitre 9 -- Gestion des projets et des documents

### 9.1 Objectif

Définir le cycle de vie complet d'un projet et des documents qui le
composent.

### 9.2 Création d'un projet

L'utilisateur saisit un nom et choisit une langue cible. Le projet est
créé vide.

### 9.3 Import

Les formats EPUB, DOCX, TXT, MD et SRT sont acceptés. Les textes sont
convertis en Markdown GFM et les images en WebP lossless. Les originaux
sont supprimés après conversion réussie.

### 9.4 Organisation

Chaque document devient un chapitre avec un source.md immuable et un
translated.md créé lors du pipeline.

### 9.5 Ordre

L'ordre initial correspond au dépôt. Il est modifiable par
glisser-déposer tant qu'aucune traduction n'est active.

### 9.6 Validation

Avant traduction, NovelTrad vérifie l'intégrité du projet, la
configuration IA, l'espace disque et la structure Markdown.

### 9.7 États

Projet : Brouillon, Prêt, En cours, En pause, Terminé, Erreur. Document
: À traduire, En cours, En pause, Terminé, Erreur.

### 9.8 Suppression

La suppression d'un projet supprime les métadonnées SQLite, les fichiers
Markdown, les images WebP, les jobs et les journaux associés après
confirmation.

### 9.9 Invariants

Un projet représente une seule œuvre. Tous les documents présents sont
destinés à l'export final. Aucun document ne peut appartenir à plusieurs
projets.
# Chapitre 10 -- Import et conversion

### 10.1 Objectif

Définir le processus d'import, de conversion et de validation des
documents avant toute traduction.

### 10.2 Formats supportés

EPUB, DOCX, TXT, Markdown (.md) et SRT uniquement.

### 10.3 Conversion

Le texte est converti en GitHub Flavored Markdown. Les images sont
converties en WebP lossless. Les originaux sont supprimés après
validation de la conversion.

### 10.4 Structure

Chaque document produit un source.md. translated.md sera créé lors du
lancement du pipeline.

### 10.5 Markdown

La structure (titres, listes, tableaux, liens, images et blocs de code
éventuels) doit être conservée autant que possible.

### 10.6 Contrôles

Détection de la langue, comptage des mots et caractères, validation des
images, vérification de la structure Markdown.

### 10.7 Gestion des erreurs

Un document en erreur est exclu de la traduction tant que le problème
n'est pas corrigé. Les autres documents restent exploitables.

### 10.8 Invariants

Aucun fichier d'origine n'est conservé. source.md est immuable. Les
chemins enregistrés dans SQLite sont relatifs au dossier du projet.

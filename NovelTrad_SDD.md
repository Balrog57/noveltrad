# NovelTrad — SDD

# Chapitre 1 — Vision, objectifs et périmètre

## 1.1 Vision

NovelTrad est une application locale de traduction littéraire assistée par intelligence artificielle. Son objectif est de permettre à un utilisateur d'importer une œuvre, de la traduire avec le fournisseur IA de son choix, d'appliquer automatiquement une révision complète puis d'exporter un résultat fidèle et propre.

## 1.2 Objectifs

- Simplicité : créer un projet, déposer les fichiers, lancer la traduction et exporter.
- Qualité : viser une traduction nécessitant le moins possible d'intervention humaine.
- Robustesse : aucune perte de données après interruption.
- Local-first : conservation locale des fichiers, sauf appels volontaires à une API distante.
- Maintenance : architecture simple à comprendre et à dépanner.

## 1.3 Périmètre fonctionnel

Création d'un projet représentant une œuvre ; import EPUB, DOCX, TXT, Markdown et SRT ; conversion automatique en Markdown GFM et WebP lossless ; réorganisation des chapitres ; pipeline automatique ; édition après validation ; export EPUB, DOCX, Markdown, TXT ou SRT.

## 1.4 Hors périmètre

Édition collaborative, multi-utilisateur, microservices, Redis, reverse proxy, multi-machine, multi-GPU, stockage cloud natif, conservation des originaux, historique complet des versions.

## 1.5 Principes fondateurs

- Un projet = une œuvre.
- source.md est immuable.
- translated.md est le seul fichier éditable.
- Le pipeline complet est obligatoire.
- Une seule traduction est active à la fois.
- Les exports sont temporaires.
- Toute écriture de translated.md est atomique.
- Les corrections humaines ne sont jamais écrasées automatiquement.

## 1.6 Objectifs qualité

NovelTrad vise une traduction fidèle nécessitant le moins de corrections manuelles possible. La révision automatique fait partie intégrante du produit et n'est jamais optionnelle. L'objectif est de fournir une base de très haute qualité, tout en reconnaissant que la validation humaine reste la référence finale.

## 1.7 Contraintes de conception

Aucune fonctionnalité ne doit complexifier inutilement l'installation.

Le temps de dépannage doit rester faible grâce à une architecture lisible.

Toutes les fonctionnalités doivent être compatibles avec un usage local.

Les évolutions futures ne doivent pas remettre en cause les principes fondateurs.

# Chapitre 2 — Principes d'architecture

## 2.1 Objectif

Privilégier la simplicité, la lisibilité et le dépannage. NovelTrad est un monolithe modulaire : un seul déploiement, plusieurs modules métier clairement séparés.

## 2.2 Couches logiques

Présentation Streamlit → Services métier → Repositories → SQLite et système de fichiers. Le Worker exécute les traitements longs et utilise une abstraction commune des fournisseurs IA.

## 2.3 Responsabilités

Streamlit affiche et collecte les actions. Les services appliquent les règles métier. Les repositories accèdent à SQLite. Le Worker exécute les jobs. Le fournisseur IA ne connaît pas les projets.

## 2.4 Dépendances autorisées

Streamlit → Services ; Services → Repositories ; Worker → Services ; Services de traduction → Fournisseur IA ; Repositories → SQLite.

## 2.5 Dépendances interdites

Aucun SQL dans Streamlit ou les services ; aucun appel IA depuis Streamlit ; aucune logique métier dans les repositories ; aucun accès direct aux fichiers depuis l'interface.

## 2.6 Invariants

SQLite est la source des métadonnées. source.md et translated.md sont la source des contenus. Une seule traduction s'exécute. Les paramètres IA sont globaux. Le pipeline est fixe.

## 2.7 Principes de conception

Responsabilité unique, faible couplage, forte cohésion, testabilité, erreurs explicites, absence d'état caché.

## 2.8 Contrats d'architecture

Les couches communiquent exclusivement selon les dépendances définies par le SDD. Toute violation constitue un défaut d'architecture.

L'interface Streamlit appelle uniquement les services métier.

Les services sont les seuls autorisés à appliquer les règles métier.

Les repositories n'effectuent que des opérations de persistance.

Le Worker ne communique jamais directement avec l'interface.

Les fournisseurs IA sont encapsulés derrière une interface unique.

## 2.9 Gestion des transactions

Toute modification de l'état métier est réalisée dans une transaction SQLite. Les écritures de fichiers et les mises à jour de la base doivent rester cohérentes.

Commit uniquement après succès complet de l'opération.

Rollback automatique en cas d'erreur.

Les écritures de translated.md sont atomiques.

Les exceptions sont propagées aux services puis journalisées.

# Chapitre 3 — Exigences fonctionnelles

EF-001 --- Créer un projet avec un nom libre et une langue cible.

EF-002 --- Détecter automatiquement la langue source après import.

EF-003 --- Accepter uniquement EPUB, DOCX, TXT, Markdown et SRT.

EF-004 --- Convertir immédiatement les textes en GFM et les images en WebP lossless.

EF-005 --- Supprimer l'original après conversion réussie et nettoyage de la copie temporaire.

EF-006 --- Conserver l'ordre de dépôt et autoriser le réordonnancement avant traduction.

EF-007 --- Valider le projet avant lancement.

EF-008 --- Exécuter quatre appels IA : traduction, révision linguistique, contexte, finalisation.

EF-009 --- Traiter une seule unité à la fois et accepter une file de nombreux chapitres.

EF-010 --- Autoriser l'arrêt propre après l'appel IA en cours.

EF-011 --- Autoriser l'édition uniquement après validation finale.

EF-012 --- Effectuer une recherche et un remplacement sur l'ensemble du projet.

EF-013 --- Exporter l'œuvre complète en EPUB, DOCX, Markdown, TXT ou SRT.

EF-014 --- Générer l'export à la volée et le supprimer après téléchargement.

EF-015 --- Fournir une interface FR/EN, claire/sombre/sépia et responsive.

EF-016 --- Afficher et filtrer les journaux dans l'interface.

## 3.1 Préconditions générales

Avant toute opération, l'application doit être initialisée, la base SQLite disponible et la configuration IA valide.

## 3.2 Postconditions générales

Chaque opération métier met à jour SQLite, les journaux et l'état de l'interface de manière cohérente.

## 3.3 Cas d'erreur communs

Projet inexistant.

Document introuvable.

Configuration IA invalide.

Espace disque insuffisant.

Erreur de conversion.

Fournisseur IA indisponible.

## 3.4 Critères d'acceptation

Chaque exigence fonctionnelle est considérée conforme lorsqu'elle est implémentée, testée et traçable via son identifiant `EF`.

# Chapitre 4 — Règles métier

RM-001 --- Un projet représente exactement une œuvre.

RM-002 --- Tout document présent dans le projet appartient à l'export final.

RM-003 --- source.md ne peut jamais être modifié.

RM-004 --- translated.md est créé au lancement de la traduction.

RM-005 --- Les corrections manuelles sont possibles uniquement après la fin du pipeline.

RM-006 --- L'ordre du projet pilote la traduction, le contexte et l'export.

RM-007 --- Le projet est verrouillé pendant une traduction active.

RM-008 --- La vérification contextuelle reçoit le chapitre précédent traduit, le courant traduit et le suivant source.

RM-009 --- Chaque appel IA échoué fait l'objet de cinq tentatives de reprise, après 1, 5, 15, 30 et 60 secondes, avant le passage du job en erreur.

RM-010 --- L'export est bloqué tant que tous les documents ne sont pas terminés.

RM-011 --- La suppression d'un document traduit exige une confirmation renforcée.

RM-012 --- Les paramètres IA globaux ne peuvent être modifiés pendant un traitement.

## 4.1 Cycle de vie métier

Chaque document suit obligatoirement le cycle : Import → Conversion → Validation → Traduction → Révision → Vérification contextuelle → Validation finale → Édition manuelle éventuelle → Export.

## 4.2 Règles de cohérence

Un document ne peut être exporté que s'il est terminé.

Un chapitre supprimé est exclu définitivement du projet.

L'ordre des chapitres est identique pour la traduction, le contexte et l'export.

Les statistiques sont recalculées après toute modification manuelle.

Toute erreur métier doit être journalisée.

## 4.3 Règles de verrouillage

Impossible de modifier l'ordre pendant une traduction.

Impossible de changer le fournisseur IA pendant un job actif.

Impossible de supprimer un projet en cours de traduction sans annulation préalable.

# Chapitre 5 — Architecture logicielle

## 5.1 Vue générale

Utilisateur → Streamlit → Services métier → Repositories / Worker → SQLite, fichiers et fournisseur IA.

## 5.2 Présentation

Affichage, navigation, formulaires, confirmations, progression et messages. Aucune logique métier.

## 5.3 Services

ProjectService, DocumentService, JobService, TranslationService, VerificationService, ExportService, SettingsService et LogService.

## 5.4 Repositories

Couche unique d'accès SQLite. Opérations de lecture, insertion, mise à jour et suppression seulement.

## 5.5 Worker

Exécute les opérations longues sans connaître Streamlit.

## 5.6 Fournisseur IA

Interface commune couvrant Ollama, LM Studio, OpenAI, OpenRouter, Gemini, Claude, Grok et les serveurs OpenAI-compatibles.

## 5.7 Fichiers persistants

SQLite, source.md, translated.md et images WebP uniquement.

## 5.8 Contrats des services

Chaque service expose une API métier stable. Les services ne communiquent jamais via l'interface utilisateur.

ProjectService : créer, renommer, supprimer et valider un projet.

DocumentService : importer, convertir, réordonner et supprimer des documents.

JobService : créer, planifier, suspendre, reprendre et annuler des jobs.

TranslationService : exécuter le pipeline IA complet.

ExportService : reconstruire puis exporter l'œuvre.

SettingsService : lire, valider et enregistrer la configuration.

## 5.9 Principes de découplage

Les services échangent des objets métier, jamais des composants Streamlit.

Les repositories ne s'appellent jamais entre eux.

Le Worker utilise uniquement les services.

Les dépendances sont injectées afin de faciliter les tests.

## 5.10 Performances

Les traitements coûteux (conversion, traduction, export) sont délégués au Worker afin de maintenir une interface réactive.

# Chapitre 6 — Architecture Docker

## 6.1 Déploiement officiel

Docker Compose est le mode officiel. Une commande doit suffire à démarrer l'application.

## 6.2 Conteneur

Un conteneur applicatif unique regroupe Streamlit et le Worker. Le fournisseur IA reste externe ou distant.

## 6.3 Environnement

.env contient APP_PASSWORD et éventuellement des options techniques. Tous les paramètres fonctionnels sont dans SQLite.

## 6.4 Volume

Le volume data contient database.sqlite, logs et projects. Aucun export n'est conservé.

## 6.5 Démarrage

Création des dossiers manquants, validation de APP_PASSWORD, ouverture/migration SQLite et nettoyage des temporaires.

## 6.6 Arrêt

Fin de l'appel IA courant, sauvegarde atomique, mise à jour du job et arrêt propre.

## 6.7 Sauvegarde et restauration

La copie du dossier data constitue une sauvegarde complète. Sa restauration doit suffire à retrouver l'installation.

## 6.8 Mise à jour

Les migrations sont automatiques, transactionnelles et non destructives.

## 6.9 Exigences de portabilité

Le même conteneur doit fonctionner sans modification sur Windows, Linux et les NAS compatibles Docker.

Aucun chemin absolu codé en dur.

Toutes les données persistantes sont stockées dans le volume data.

Les permissions des fichiers doivent être compatibles avec les principaux systèmes de fichiers.

Les migrations SQLite sont automatiques au démarrage.

## 6.10 Santé du conteneur

Le conteneur expose un mécanisme de vérification de santé permettant de confirmer que l'application est opérationnelle.

Base SQLite accessible.

Répertoire data accessible en lecture/écriture.

Worker démarré.

Configuration chargée.

# Chapitre 7 — Architecture Python

## 7.1 Objectif

Un projet Python unique, structuré en modules métier simples et testables.

## 7.2 Environnement

Python 3.12 minimum, type hints, Ruff et Pytest. Les dépendances sont gérées par uv ou pip.

## 7.3 Arborescence

app/main.py ; core/ ; ui/ ; modules/authentication, projects, documents, jobs, translation, verification, export, settings, system ; tests/.

## 7.4 Structure d'un module

models.py, schemas.py, repository.py, service.py, exceptions.py et tests/. Seuls les fichiers réellement utiles sont créés.

## 7.5 core

Base SQLite, transactions, chemins, journalisation, exceptions communes et écritures atomiques. Aucun métier.

## 7.6 authentication

Lecture et validation de APP_PASSWORD sans persistance ni journalisation du secret.

## 7.7 projects

Création, renommage, suppression, langue cible et état global.

## 7.8 documents

Import, conversion, ordre, statistiques, fichiers Markdown et images.

## 7.9 jobs

File FIFO, statut, progression, pause, reprise, erreur et récupération après redémarrage.

## 7.10 translation

Segmentation, appels IA, reconstruction, politique de reprises et sauvegarde.

## 7.11 verification

Révision linguistique, contexte et validation finale.

## 7.12 export

Assemblage, génération temporaire et nettoyage.

## 7.13 settings

Langue, thème, fournisseur, URL, clé, modèle, détection et test de connexion.

## 7.14 system

Journaux, diagnostics, nettoyage et état du Worker.

## 7.15 Exceptions et tests

Exceptions métier explicites, injection des dépendances, fournisseurs et système de fichiers simulables.

## 7.16 Standards de développement

Toutes les contributions doivent respecter des conventions communes afin de garantir un code homogène et facile à maintenir.

Type hints obligatoires sur les API publiques.

Docstrings pour les classes et services publics.

Aucune logique métier dans les callbacks Streamlit.

Fonctions courtes avec une responsabilité unique.

Journalisation structurée des erreurs.

## 7.17 Conventions de tests

Chaque module possède son propre dossier de tests. Les tests utilisent des doubles (mocks/fakes) pour les fournisseurs IA et le système de fichiers lorsque nécessaire.

# Chapitre 8 — Modèle de données SQLite

## 8.1 Objectif

SQLite est l'unique base de données de NovelTrad. Elle stocke uniquement les métadonnées de l'application. Les contenus des chapitres restent exclusivement dans source.md et translated.md.

## 8.2 Principes

La base contient les projets, documents, jobs, paramètres et journaux. Aucun texte de chapitre ni image n'est enregistré dans SQLite.

## 8.3 Transactions

Toute modification est transactionnelle. En cas d'échec, un rollback complet est effectué.

## 8.4 Intégrité

Les clés étrangères sont activées. Toutes les dates sont stockées au format UTC ISO-8601.

## 8.5 Table projects

Colonnes : id, name, source_language, target_language, status, created_at, updated_at.

## 8.6 Table documents

Colonnes : id, project_id, display_name, order_index, source_path, translated_path, status, pipeline_stage, progress, word_count, character_count, detected_language, last_error, updated_at. La paire (project_id, order_index) est unique.

## 8.7 Table jobs

Colonnes : id, document_id, state, provider, model, retry_count, started_at, finished_at. États : `Waiting`, `Queued`, `Running`, `Paused`, `Retrying`, `Completed`, `Cancelled` et `Failed`.

## 8.8 Tables settings et logs

settings stocke les paramètres globaux. logs enregistre les événements sans jamais contenir de secret ni le texte des chapitres.

## 8.9 Index

Indexes recommandés : projects(name), documents(project_id,order_index), documents(status), jobs(state), logs(created_at).

## 8.10 Invariants

SQLite est l'unique source des métadonnées. Les suppressions sont transactionnelles. Un projet supprimé supprime ses documents, jobs et journaux associés.

## 8.11 Stratégie de migration

Toute évolution du schéma SQLite est gérée par des migrations versionnées, transactionnelles et réversibles.

Sauvegarde logique avant migration majeure.

Version du schéma enregistrée en base.

Rollback automatique si une migration échoue.

Aucune migration ne modifie les fichiers source.md ou translated.md.

## 8.12 Contraintes d'intégrité

Un project_id référencé doit exister.

order_index est unique par projet.

Les états des jobs sont limités aux valeurs documentées.

Les chemins stockés sont relatifs au dossier du projet.

Toute suppression respecte les clés étrangères.

# Chapitre 9 — Gestion des projets et des documents

## 9.1 Objectif

Définir le cycle de vie complet d'un projet et des documents qui le composent.

## 9.2 Création d'un projet

L'utilisateur saisit un nom et choisit une langue cible. Le projet est créé vide.

## 9.3 Import

Les formats EPUB, DOCX, TXT, MD et SRT sont acceptés. Les textes sont convertis en Markdown GFM et les images en WebP lossless. Les originaux sont supprimés après conversion réussie.

## 9.4 Organisation

Chaque document devient un chapitre avec un source.md immuable et un translated.md créé lors du pipeline.

## 9.5 Ordre

L'ordre initial correspond au dépôt. Il est modifiable par glisser-déposer tant qu'aucune traduction n'est active.

## 9.6 Validation

Avant traduction, NovelTrad vérifie l'intégrité du projet, la configuration IA, l'espace disque et la structure Markdown.

## 9.7 États

Projet : Brouillon, Prêt, En cours, En pause, Terminé, Erreur. Document : À traduire, En cours, En pause, Terminé, Erreur.

## 9.8 Suppression

La suppression d'un projet supprime les métadonnées SQLite, les fichiers Markdown, les images WebP, les jobs et les journaux associés après confirmation.

## 9.9 Invariants

Un projet représente une seule œuvre. Tous les documents présents sont destinés à l'export final. Aucun document ne peut appartenir à plusieurs projets.

## 9.10 Cycle de vie d'un projet

Un projet évolue selon les états : Brouillon → Prêt → En cours → En pause (optionnel) → Terminé ou Erreur. Un projet terminé reste modifiable tant qu'aucune nouvelle traduction n'est lancée.

## 9.11 Règles d'import

Chaque fichier importé devient un document indépendant.

Les chapitres conservent l'ordre de dépôt jusqu'à une réorganisation manuelle.

Les doublons de nom sont autorisés mais possèdent un identifiant interne unique.

Un document en erreur n'empêche pas l'administration du projet.

## 9.12 Statistiques du projet

Le tableau de bord calcule automatiquement le nombre de documents, de mots, de caractères, l'avancement global, les erreurs en attente et le temps estimé restant lorsque des jobs sont actifs.

# Chapitre 10 — Import et conversion

## 10.1 Objectif

Définir le processus d'import, de conversion et de validation des documents avant toute traduction.

## 10.2 Formats supportés

EPUB, DOCX, TXT, Markdown (.md) et SRT uniquement.

## 10.3 Conversion

Le texte est converti en GitHub Flavored Markdown. Les images sont converties en WebP lossless. Les originaux sont supprimés après validation de la conversion.

## 10.4 Structure

Chaque document produit un source.md. translated.md sera créé lors du lancement du pipeline.

## 10.5 Markdown

La structure (titres, listes, tableaux, liens, images et blocs de code éventuels) doit être conservée autant que possible.

## 10.6 Contrôles

Détection de la langue, comptage des mots et caractères, validation des images, vérification de la structure Markdown.

## 10.7 Gestion des erreurs

Un document en erreur est exclu de la traduction tant que le problème n'est pas corrigé. Les autres documents restent exploitables.

## 10.8 Invariants

Aucun fichier d'origine n'est conservé. source.md est immuable. Les chemins enregistrés dans SQLite sont relatifs au dossier du projet.

## 10.9 Pipeline de conversion détaillé

Chaque import suit systématiquement les étapes : copie temporaire, analyse du format, extraction du contenu, conversion en GitHub Flavored Markdown, conversion des images en WebP lossless, validation de la structure, création de source.md puis suppression des fichiers temporaires.

## 10.10 Validation de la conversion

Le nombre de titres est vérifié.

Les liens internes et les images sont contrôlés.

Le Markdown généré doit être syntaxiquement valide.

Les images référencées doivent exister.

Toute anomalie est enregistrée dans les journaux.

## 10.11 Performances attendues

La conversion doit être indépendante du fournisseur IA et pouvoir être exécutée en lot sur plusieurs documents avant le lancement de la traduction.

# Chapitre 11 — Pipeline IA

## 11.1 Objectif

Définir le pipeline automatique obligatoire appliqué à chaque document.

## 11.2 Préparation

Validation du Markdown, segmentation si nécessaire et préparation des données d'entrée.

## 11.3 Traduction fidèle

Premier appel IA produisant une traduction fidèle sans ajout ni omission.

## 11.4 Révision linguistique

Deuxième appel IA corrigeant orthographe, grammaire, ponctuation et fluidité sans changer le sens.

## 11.5 Vérification contextuelle

Troisième appel IA utilisant le chapitre précédent traduit, le chapitre courant traduit et le chapitre suivant source pour assurer la cohérence.

## 11.6 Validation finale

Quatrième appel IA vérifiant qu'aucun passage n'est oublié, que la structure Markdown est conservée et que le résultat est prêt à être édité.

## 11.7 Sauvegarde

Après chaque étape, translated.md est écrit de façon atomique et la progression est mise à jour dans SQLite.

## 11.8 Politique de reprise

En cas d'échec d'un appel IA, cinq tentatives de reprise sont réalisées après 1, 5, 15, 30 et 60 secondes avant le passage du job en erreur.

## 11.9 Invariants

Le pipeline est toujours exécuté dans le même ordre et aucune étape ne peut être désactivée.

## 11.10 Segmentation et contexte

Lorsqu'un chapitre dépasse la fenêtre de contexte du modèle, il est découpé en segments. La reconstruction respecte strictement l'ordre d'origine. La vérification contextuelle utilise toujours le chapitre précédent traduit, le chapitre courant traduit et le chapitre suivant dans sa version source.

## 11.11 Contrats des appels IA

Chaque étape possède un prompt dédié et versionné.

Aucun appel ne doit modifier la structure Markdown.

Les images et leurs références doivent être conservées.

Chaque réponse est validée avant de passer à l'étape suivante.

Toute anomalie déclenche une nouvelle tentative ou un passage en erreur.

## 11.12 Critères de validation

Un document est considéré comme terminé uniquement lorsque les quatre étapes du pipeline sont validées, que le Markdown reste cohérent et qu'aucune erreur bloquante n'est détectée.

# Chapitre 12 — Worker et gestion des jobs

## 12.1 Objectif

Définir l'exécution séquentielle des traitements longs et la gestion des jobs.

## 12.2 File d'attente

Chaque document validé génère un job. Plusieurs jobs peuvent être ajoutés, mais un seul est exécuté à la fois.

## 12.3 États

Waiting, Queued, Running, Paused, Retrying, Completed, Cancelled et Failed.

## 12.4 Progression

Le Worker met à jour l'étape courante, le pourcentage, le fournisseur IA, le modèle utilisé et le dernier message.

## 12.5 Pause et reprise

Une pause est demandée proprement. L'appel IA en cours se termine, puis le job est suspendu. La reprise recommence à la dernière étape validée.

## 12.6 Erreurs

Après cinq tentatives de reprise, réalisées après 1, 5, 15, 30 et 60 secondes, le job passe en `Failed` et reste disponible pour une reprise manuelle.

## 12.7 Journalisation

Chaque changement d'état est enregistré dans SQLite et visible dans l'interface.

## 12.8 Invariants

Un seul Worker logique traite les jobs. L'ordre FIFO est respecté sauf réorganisation explicite avant démarrage.

## 12.9 Ordonnancement

Le Worker exécute les jobs de manière séquentielle selon une file FIFO. Les documents peuvent être ajoutés en masse avant le démarrage, mais un seul job est actif à un instant donné.

## 12.10 Reprise et annulation

Une annulation attend la fin de l'appel IA en cours avant d'arrêter le job.

Une reprise redémarre à la dernière étape validée.

Les étapes déjà validées ne sont jamais rejouées sauf demande explicite.

## 12.11 Métriques

Le Worker expose la progression globale, le document courant, le fournisseur, le modèle, le temps écoulé, une estimation du temps restant et le nombre de jobs restants.

## 12.12 Invariants d'exécution

Un seul Worker logique est autorisé.

Aucun job ne contourne la file d'attente.

Chaque changement d'état est enregistré dans SQLite et dans les journaux.

# Chapitre 13 — Interface utilisateur

## 13.1 Objectif

Définir une interface simple, responsive et cohérente sur ordinateur, tablette et smartphone.

## 13.2 Premier lancement

Choix de la langue (FR/EN), du thème (Clair/Sombre/Sépia), puis ouverture automatique des paramètres.

## 13.3 Authentification

Écran unique demandant APP_PASSWORD. Aucun compte utilisateur n'est géré.

## 13.4 Écran Projets

Création, renommage, suppression, recherche et ouverture d'un projet avec résumé de son état.

## 13.5 Écran Projet

Glisser-déposer, réorganisation des chapitres, aperçu des statistiques, lancement de la traduction et export.

## 13.6 Paramètres

Configuration du fournisseur IA, du modèle, de l'URL, de la clé API, de la langue et du thème. Paramètres verrouillés pendant un traitement.

## 13.7 Journaux

Consultation et filtrage des événements, erreurs et diagnostics.

## 13.8 Messages

Toutes les erreurs doivent être explicites et proposer une action corrective.

## 13.9 Responsive

Toutes les fonctionnalités restent accessibles sans perte d'information sur smartphone.

## 13.10 Invariants

Aucune logique métier dans Streamlit. Toutes les actions passent par les services métier.

## 13.11 Navigation et ergonomie

La navigation doit limiter le nombre de clics et rendre les traitements longs compréhensibles.

## 13.12 Composants réutilisables

Tableaux triables et filtrables.

Barres de progression par document et globales.

Panneaux d'état du Worker et du fournisseur IA.

Notifications de succès, avertissement et erreur.

## 13.13 Glisser-déposer

Import multiple de fichiers.

Réorganisation visuelle des chapitres.

Mise à jour immédiate de l'ordre dans SQLite.

Verrouillage pendant une traduction.

## 13.14 Accessibilité

Responsive PC, tablette et smartphone.

Contraste compatible avec les thèmes clair, sombre et sépia.

Libellés explicites et messages d'erreur compréhensibles.

# Chapitre 14 — Paramètres et fournisseurs IA

## 14.1 Objectif

Centraliser tous les paramètres globaux de l'application.

## 14.2 Paramètres généraux

Langue (FR/EN), thème (Clair/Sombre/Sépia), niveau de journalisation.

## 14.3 Fournisseurs IA

Ollama, LM Studio, OpenAI, OpenRouter, Gemini, Claude, Grok et toute API compatible OpenAI.

## 14.4 Configuration

URL, clé API (si nécessaire), modèle et options du fournisseur sont enregistrés dans SQLite.

## 14.5 Détection

Les modèles Ollama et LM Studio installés sont détectés automatiquement.

## 14.6 Validation

Un test de connexion permet de vérifier le fournisseur et le modèle avant toute traduction.

## 14.7 Verrouillage

Les paramètres IA ne peuvent pas être modifiés lorsqu'un job est en cours.

## 14.8 Sécurité

Les clés API ne sont jamais affichées en clair dans les journaux ni exportées.

## 14.9 Invariants

Une configuration IA globale est active à un instant donné pour toute l'application.

## 14.10 Gestion des fournisseurs

Le changement de fournisseur conserve les autres paramètres compatibles.

Chaque fournisseur expose les modèles disponibles via une interface commune.

La configuration active est unique pour toute l'application.

## 14.11 Validation des modèles

Vérification de la disponibilité du modèle avant lancement.

Détection automatique des modèles Ollama et LM Studio.

Message explicite si le modèle n'est plus disponible.

## 14.12 Paramètres avancés

Température, contexte maximal et options compatibles avec le fournisseur.

Les paramètres non supportés sont masqués automatiquement.

## 14.13 Sécurité de la configuration

Les clés API ne sont jamais affichées en clair.

Les tests de connexion n'enregistrent jamais les secrets dans les journaux.

# Chapitre 15 — Export

## 15.1 Objectif

Définir le processus d'assemblage et de génération des fichiers exportés.

## 15.2 Conditions

L'export est autorisé uniquement lorsque tous les documents du projet sont terminés.

## 15.3 Formats

EPUB, DOCX, Markdown, TXT et SRT.

## 15.4 Reconstruction

L'œuvre est reconstruite dans l'ordre défini par le projet à partir des translated.md.

## 15.5 Métadonnées

Le nom du projet est utilisé comme titre par défaut. Les autres métadonnées restent minimales afin de permettre une édition ultérieure avec un outil spécialisé.

## 15.6 Téléchargement

Le fichier est généré dans un emplacement temporaire, téléchargé par l'utilisateur puis supprimé.

## 15.7 Contrôles

Vérification de l'ordre, de la présence des chapitres, des images WebP et de la cohérence Markdown avant génération.

## 15.8 Invariants

Aucun export n'est conservé. Les fichiers source.md et translated.md ne sont jamais modifiés par l'export.

L'export ne modifie jamais source.md ni translated.md.

Les fichiers temporaires sont supprimés après téléchargement.

## 15.9 Reconstruction de l'œuvre

L'export assemble exclusivement les fichiers translated.md selon order_index. Les chapitres supprimés sont ignorés.

## 15.10 Contrôles avant export

Tous les documents sont terminés.

Aucun job n'est actif.

Toutes les images référencées existent.

Le Markdown est valide.

## 15.11 Gestion des erreurs d'export

Aucun fichier partiel n'est conservé.

Les erreurs sont journalisées.

L'utilisateur reçoit un message explicite.

# Chapitre 16 — Journalisation, sécurité et robustesse

## 16.1 Objectif

Garantir la traçabilité, la sécurité des données et la robustesse de l'application.

## 16.2 Journalisation

Tous les événements importants sont enregistrés : démarrage, arrêt, import, conversion, traduction, export, erreurs et changements d'état.

## 16.3 Sécurité

`APP_PASSWORD` est lu uniquement depuis le `.env`. Les clés API sont protégées et ne sont jamais affichées dans les journaux.

## 16.4 Robustesse

Toutes les écritures sont atomiques. Les transactions SQLite assurent la cohérence des métadonnées.

## 16.5 Reprise après incident

Après un redémarrage, les jobs interrompus sont restaurés à leur dernière étape validée.

## 16.6 Nettoyage

Les fichiers temporaires sont supprimés automatiquement au démarrage et après les exports.

## 16.7 Diagnostics

L'interface affiche l'état du Worker, du fournisseur IA, de la base SQLite et les erreurs récentes.

## 16.8 Invariants

Aucun secret n'est inscrit dans les journaux. Les erreurs utilisateur et techniques sont clairement distinguées.

## 16.9 Politique de journalisation

La journalisation doit fournir suffisamment d'informations pour diagnostiquer un problème sans divulguer de données sensibles.

- Horodatage UTC pour chaque événement.
- Niveaux `DEBUG`, `INFO`, `WARNING`, `ERROR` et `CRITICAL`.
- Identifiant du projet et du document lorsque pertinent.

## 16.10 Résilience

- Redémarrage sans perte des données validées.
- Détection des fichiers temporaires orphelins.
- Vérification automatique de l'intégrité SQLite au démarrage.

## 16.11 Sécurité des données

- Aucun contenu de chapitre dans les journaux.
- Les mots de passe et clés API ne sont jamais affichés.
- Les écritures sensibles sont limitées au volume `data`.

## 16.12 Audit

Les événements majeurs — création, suppression, import, traduction, export et erreurs — restent consultables depuis l'interface de journalisation.

# Chapitre 17 — Tests et critères d'acceptation

## 17.1 Objectif

Définir la stratégie de validation garantissant que chaque exigence est correctement implémentée.

## 17.2 Tests unitaires

Chaque service métier est testé indépendamment. Les appels IA, SQLite et le système de fichiers sont simulés lorsque nécessaire.

## 17.3 Tests d'intégration

Validation des flux complets : création de projet, import, pipeline, export et reprise après incident.

## 17.4 Tests d'interface

Vérification des écrans principaux sur ordinateur et smartphone, en français et en anglais.

## 17.5 Tests de robustesse

Arrêt pendant une traduction, reprise automatique, rollback SQLite et intégrité des fichiers Markdown.

## 17.6 Critères d'acceptation

Toutes les exigences fonctionnelles `EF` et règles métier `RM` doivent être couvertes par au moins un test documenté avant une version stable.

## 17.7 Non-régression

Chaque correction de bug doit être accompagnée d'un test empêchant sa réapparition.

## 17.8 Invariants

Aucune version ne peut être publiée si un test critique échoue.

## 17.9 Couverture minimale

- 100 % des exigences critiques sont couvertes par des tests.
- Tous les services métier disposent de tests unitaires.
- Chaque pipeline complet dispose de tests d'intégration.

## 17.10 Tests de performance

- Import massif de documents.
- Exécution prolongée du Worker.
- Validation des migrations SQLite.

# Chapitre 18 — Diagrammes et modèles

## 18.1 Objectif

Centraliser les représentations d'architecture et de flux utilisées dans le projet.

## 18.2 Diagramme de composants

Décrit les relations entre Streamlit, les services métier, les repositories, le Worker, SQLite, le système de fichiers et les fournisseurs IA.

## 18.3 Diagramme de séquence

Présente le déroulement complet : création du projet, import, conversion, traduction, révision, validation et export.

## 18.4 Diagramme de données

Représente les principales tables SQLite et leurs relations.

## 18.5 Cycle de vie d'un document

Illustration des états d'un document, de l'import à l'export.

## 18.6 Cycle de vie d'un job

Illustration des transitions `Waiting → Queued → Running → Retrying/Paused → Completed, Cancelled ou Failed`.

## 18.7 Conventions

Tous les diagrammes UML utilisent une nomenclature cohérente avec les noms des modules et services définis dans ce SDD.

## 18.8 Invariants

Les diagrammes sont documentaires : en cas de divergence, le texte normatif du SDD fait foi jusqu'à leur mise à jour.

## 18.9 Diagrammes UML

Les diagrammes obligatoires sont :

- diagrammes de classes ;
- diagrammes de séquence ;
- diagrammes d'états ;
- diagrammes de composants.

## 18.10 Maintenance des diagrammes

Toute évolution majeure de l'architecture impose une mise à jour des diagrammes concernés.

# Chapitre 19 — Exigences (REQ) et traçabilité

## 19.1 Objectif

Assurer la traçabilité entre les exigences, l'implémentation et les tests.

## 19.2 Identifiants

Chaque exigence possède un identifiant unique. Les exigences fonctionnelles utilisent `EF-XXX` et les règles métier utilisent `RM-XXX`. Le terme `REQ` désigne collectivement ces deux catégories dans la traçabilité.

## 19.3 Classification

Les exigences sont classées en fonctionnelles, techniques, sécurité, interface et performance.

## 19.4 Traçabilité

Chaque fonctionnalité implémentée référence les exigences qu'elle satisfait. Chaque exigence possède au moins un test associé.

## 19.5 Gestion des évolutions

Une modification d'exigence implique une mise à jour du SDD, des tests et, si nécessaire, des migrations de données.

## 19.6 Critères

Une exigence est considérée satisfaite uniquement lorsque son implémentation et ses tests sont validés.

## 19.7 Invariants

Aucune fonctionnalité ne doit être développée sans être rattachée à une ou plusieurs exigences documentées.

## 19.8 Matrice de traçabilité

Chaque exigence `EF` ou règle métier `RM` est reliée aux modules, aux tests et aux sections du SDD correspondantes.

## 19.9 Gestion des changements

- Toute nouvelle exigence reçoit un identifiant unique.
- Les exigences obsolètes restent historisées.

# Chapitre 20 — Annexes techniques

## 20.1 Glossaire

Définitions des termes techniques utilisés dans le SDD : GFM, Worker, Job, Pipeline, WebP, etc.

## 20.2 Arborescence de référence

Structure officielle des dossiers du projet et du volume `data`.

## 20.3 Conventions de nommage

Règles pour les modules, classes, services, tables SQLite et fichiers Markdown.

## 20.4 Formats d'échange

Description des formats importés et exportés ainsi que des contraintes de compatibilité.

## 20.5 Journal des décisions

Historique des choix d'architecture majeurs et justification des arbitrages.

## 20.6 Évolutions futures

Liste des améliorations envisageables sans remettre en cause l'architecture validée.

## 20.7 Références

Références documentaires : Markdown GFM, SQLite, Docker, Streamlit et fournisseurs IA.

## 20.8 Clôture

Le présent SDD constitue la référence technique unique du projet NovelTrad. Toute évolution devra modifier directement ce document.

## 20.9 Évolutions prévues

- Nouveaux fournisseurs IA.
- Nouveaux formats d'import et d'export.
- Optimisations du pipeline.

## 20.10 Révision du SDD

Le présent document est la référence unique et doit rester synchronisé avec l'implémentation.

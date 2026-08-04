# NovelTrad — SDD

## Chapitres 1 à 5

# Chapitre 1 -- Vision, objectifs et périmètre

### 1.1 Vision

NovelTrad est une application locale de traduction littéraire assistée
par intelligence artificielle. Son objectif est de permettre à un
utilisateur d'importer une œuvre, de la traduire avec le fournisseur IA
de son choix, d'appliquer automatiquement une révision complète puis
d'exporter un résultat fidèle et propre.

### 1.2 Objectifs

• Simplicité : créer un projet, déposer les fichiers, lancer la
traduction et exporter. • Qualité : viser une traduction nécessitant le
moins possible d'intervention humaine. • Robustesse : aucune perte de
données après interruption. • Local-first : conservation locale des
fichiers, sauf appels volontaires à une API distante. • Maintenance :
architecture simple à comprendre et à dépanner.

### 1.3 Périmètre fonctionnel

Création d'un projet représentant une œuvre ; import EPUB, DOCX, TXT,
Markdown et SRT ; conversion automatique en Markdown GFM et WebP
lossless ; réorganisation des chapitres ; pipeline automatique ; édition
après validation ; export EPUB, DOCX, Markdown, TXT ou SRT.

### 1.4 Hors périmètre

Édition collaborative, multi-utilisateur, microservices, Redis, reverse
proxy, multi-machine, multi-GPU, stockage cloud natif, conservation des
originaux, historique complet des versions.

### 1.5 Principes fondateurs

### 1. Un projet = une œuvre.

2.  source.md est immuable.
3.  translated.md est le seul fichier éditable.
4.  Le pipeline complet est obligatoire.
5.  Une seule traduction est active à la fois.
6.  Les exports sont temporaires.
7.  Toute écriture de translated.md est atomique.
8.  Les corrections humaines ne sont jamais écrasées automatiquement.
# Chapitre 2 -- Principes d'architecture

### 2.1 Objectif

Privilégier la simplicité, la lisibilité et le dépannage. NovelTrad est
un monolithe modulaire : un seul déploiement, plusieurs modules métier
clairement séparés.

### 2.2 Couches logiques

Présentation Streamlit → Services métier → Repositories → SQLite et
système de fichiers. Le Worker exécute les traitements longs et utilise
une abstraction commune des fournisseurs IA.

### 2.3 Responsabilités

Streamlit affiche et collecte les actions. Les services appliquent les
règles métier. Les repositories accèdent à SQLite. Le Worker exécute les
jobs. Le fournisseur IA ne connaît pas les projets.

### 2.4 Dépendances autorisées

Streamlit → Services ; Services → Repositories ; Worker → Services ;
Services de traduction → Fournisseur IA ; Repositories → SQLite.

### 2.5 Dépendances interdites

Aucun SQL dans Streamlit ou les services ; aucun appel IA depuis
Streamlit ; aucune logique métier dans les repositories ; aucun accès
direct aux fichiers depuis l'interface.

### 2.6 Invariants

SQLite est la source des métadonnées. source.md et translated.md sont la
source des contenus. Une seule traduction s'exécute. Les paramètres IA
sont globaux. Le pipeline est fixe.

### 2.7 Principes de conception

Responsabilité unique, faible couplage, forte cohésion, testabilité,
erreurs explicites, absence d'état caché.
# Chapitre 3 -- Exigences fonctionnelles

EF-001 --- Créer un projet avec un nom libre et une langue cible.

EF-002 --- Détecter automatiquement la langue source après import.

EF-003 --- Accepter uniquement EPUB, DOCX, TXT, Markdown et SRT.

EF-004 --- Convertir immédiatement les textes en GFM et les images en
WebP lossless.

EF-005 --- Supprimer l'original après conversion réussie et nettoyage de
la copie temporaire.

EF-006 --- Conserver l'ordre de dépôt et autoriser le réordonnancement
avant traduction.

EF-007 --- Valider le projet avant lancement.

EF-008 --- Exécuter quatre appels IA : traduction, révision
linguistique, contexte, finalisation.

EF-009 --- Traiter une seule unité à la fois et accepter une file de
nombreux chapitres.

EF-010 --- Autoriser l'arrêt propre après l'appel IA en cours.

EF-011 --- Autoriser l'édition uniquement après validation finale.

EF-012 --- Effectuer une recherche et un remplacement sur l'ensemble du
projet.

EF-013 --- Exporter l'œuvre complète en EPUB, DOCX, Markdown, TXT ou
SRT.

EF-014 --- Générer l'export à la volée et le supprimer après
téléchargement.

EF-015 --- Fournir une interface FR/EN, claire/sombre/sépia et
responsive.

EF-016 --- Afficher et filtrer les journaux dans l'interface.
# Chapitre 4 -- Règles métier

RM-001 --- Un projet représente exactement une œuvre.

RM-002 --- Tout document présent dans le projet appartient à l'export
final.

RM-003 --- source.md ne peut jamais être modifié.

RM-004 --- translated.md est créé au lancement de la traduction.

RM-005 --- Les corrections manuelles sont possibles uniquement après la
fin du pipeline.

RM-006 --- L'ordre du projet pilote la traduction, le contexte et
l'export.

RM-007 --- Le projet est verrouillé pendant une traduction active.

RM-008 --- La vérification contextuelle reçoit le chapitre précédent
traduit, le courant traduit et le suivant source.

RM-009 --- Les appels échoués sont retentés après 1, 5, 15, 30 et 60
secondes.

RM-010 --- L'export est bloqué tant que tous les documents ne sont pas
terminés.

RM-011 --- La suppression d'un document traduit exige une confirmation
renforcée.

RM-012 --- Les paramètres IA globaux ne peuvent être modifiés pendant un
traitement.
# Chapitre 5 -- Architecture logicielle

### 5.1 Vue générale

Utilisateur → Streamlit → Services métier → Repositories / Worker →
SQLite, fichiers et fournisseur IA.

### 5.2 Présentation

Affichage, navigation, formulaires, confirmations, progression et
messages. Aucune logique métier.

### 5.3 Services

ProjectService, DocumentService, JobService, TranslationService,
VerificationService, ExportService, SettingsService et LogService.

### 5.4 Repositories

Couche unique d'accès SQLite. Opérations de lecture, insertion, mise à
jour et suppression seulement.

### 5.5 Worker

Exécute les opérations longues sans connaître Streamlit.

### 5.6 Fournisseur IA

Interface commune couvrant Ollama, LM Studio, OpenAI, OpenRouter,
Gemini, Claude, Grok et les serveurs OpenAI-compatibles.

### 5.7 Fichiers persistants

SQLite, source.md, translated.md et images WebP uniquement.

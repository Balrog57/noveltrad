# NovelTrad — SDD

## Chapitres 11 à 15

# Chapitre 11 -- Pipeline IA

### 11.1 Objectif

Définir le pipeline automatique obligatoire appliqué à chaque document.

### 11.2 Préparation

Validation du Markdown, segmentation si nécessaire et préparation des
données d'entrée.

### 11.3 Traduction fidèle

Premier appel IA produisant une traduction fidèle sans ajout ni
omission.

### 11.4 Révision linguistique

Deuxième appel IA corrigeant orthographe, grammaire, ponctuation et
fluidité sans changer le sens.

### 11.5 Vérification contextuelle

Troisième appel IA utilisant le chapitre précédent traduit, le chapitre
courant traduit et le chapitre suivant source pour assurer la cohérence.

### 11.6 Validation finale

Quatrième appel IA vérifiant qu'aucun passage n'est oublié, que la
structure Markdown est conservée et que le résultat est prêt à être
édité.

### 11.7 Sauvegarde

Après chaque étape, translated.md est écrit de façon atomique et la
progression est mise à jour dans SQLite.

### 11.8 Politique de reprise

En cas d'échec, cinq tentatives sont réalisées avec des délais de 1, 5,
15, 30 et 60 secondes avant passage en erreur.

### 11.9 Invariants

Le pipeline est toujours exécuté dans le même ordre et aucune étape ne
peut être désactivée.
# Chapitre 12 -- Worker et gestion des jobs

### 12.1 Objectif

Définir l'exécution séquentielle des traitements longs et la gestion des
jobs.

### 12.2 File d'attente

Chaque document validé génère un job. Plusieurs jobs peuvent être
ajoutés, mais un seul est exécuté à la fois.

### 12.3 États

Waiting, Queued, Running, Paused, Retrying, Completed, Cancelled et
Failed.

### 12.4 Progression

Le Worker met à jour l'étape courante, le pourcentage, le fournisseur
IA, le modèle utilisé et le dernier message.

### 12.5 Pause et reprise

Une pause est demandée proprement. L'appel IA en cours se termine, puis
le job est suspendu. La reprise recommence à la dernière étape validée.

### 12.6 Erreurs

Après 5 tentatives (1, 5, 15, 30, 60 s), le job passe en Failed et reste
disponible pour une reprise manuelle.

### 12.7 Journalisation

Chaque changement d'état est enregistré dans SQLite et visible dans
l'interface.

### 12.8 Invariants

Un seul Worker logique traite les jobs. L'ordre FIFO est respecté sauf
réorganisation explicite avant démarrage.
# Chapitre 13 -- Interface utilisateur

### 13.1 Objectif

Définir une interface simple, responsive et cohérente sur ordinateur,
tablette et smartphone.

### 13.2 Premier lancement

Choix de la langue (FR/EN), du thème (Clair/Sombre/Sépia), puis
ouverture automatique des paramètres.

### 13.3 Authentification

Écran unique demandant APP_PASSWORD. Aucun compte utilisateur n'est
géré.

### 13.4 Écran Projets

Création, renommage, suppression, recherche et ouverture d'un projet
avec résumé de son état.

### 13.5 Écran Projet

Glisser-déposer, réorganisation des chapitres, aperçu des statistiques,
lancement de la traduction et export.

### 13.6 Paramètres

Configuration du fournisseur IA, du modèle, de l'URL, de la clé API, de
la langue et du thème. Paramètres verrouillés pendant un traitement.

### 13.7 Journaux

Consultation et filtrage des événements, erreurs et diagnostics.

### 13.8 Messages

Toutes les erreurs doivent être explicites et proposer une action
corrective.

### 13.9 Responsive

Toutes les fonctionnalités restent accessibles sans perte d'information
sur smartphone.

### 13.10 Invariants

Aucune logique métier dans Streamlit. Toutes les actions passent par les
services métier.
# Chapitre 14 -- Paramètres et fournisseurs IA

### 14.1 Objectif

Centraliser tous les paramètres globaux de l'application.

### 14.2 Paramètres généraux

Langue (FR/EN), thème (Clair/Sombre/Sépia), niveau de journalisation.

### 14.3 Fournisseurs IA

Ollama, LM Studio, OpenAI, OpenRouter, Gemini, Claude, Grok et toute API
compatible OpenAI.

### 14.4 Configuration

URL, clé API (si nécessaire), modèle et options du fournisseur sont
enregistrés dans SQLite.

### 14.5 Détection

Les modèles Ollama et LM Studio installés sont détectés automatiquement.

### 14.6 Validation

Un test de connexion permet de vérifier le fournisseur et le modèle
avant toute traduction.

### 14.7 Verrouillage

Les paramètres IA ne peuvent pas être modifiés lorsqu'un job est en
cours.

### 14.8 Sécurité

Les clés API ne sont jamais affichées en clair dans les journaux ni
exportées.

### 14.9 Invariants

Une configuration IA globale est active à un instant donné pour toute
l'application.
# Chapitre 15 -- Export

### 15.1 Objectif

Définir le processus d'assemblage et de génération des fichiers
exportés.

### 15.2 Conditions

L'export est autorisé uniquement lorsque tous les documents du projet
sont terminés.

### 15.3 Formats

EPUB, DOCX, Markdown, TXT et SRT.

### 15.4 Reconstruction

L'œuvre est reconstruite dans l'ordre défini par le projet à partir des
translated.md.

### 15.5 Métadonnées

Le nom du projet est utilisé comme titre par défaut. Les autres
métadonnées restent minimales afin de permettre une édition ultérieure
avec un outil spécialisé.

### 15.6 Téléchargement

Le fichier est généré dans un emplacement temporaire, téléchargé par
l'utilisateur puis supprimé.

### 15.7 Contrôles

Vérification de l'ordre, de la présence des chapitres, des images WebP
et de la cohérence Markdown avant génération.

### 15.8 Invariants

Aucun export n'est conservé. Les fichiers source.md et translated.md ne
sont jamais modifiés par l'export.

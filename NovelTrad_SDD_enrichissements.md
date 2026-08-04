# NovelTrad — SDD

## Enrichissements des chapitres 1 à 16

### 1.6 Objectifs qualité

NovelTrad vise une traduction fidèle nécessitant le moins de corrections
manuelles possible. La révision automatique fait partie intégrante du
produit et n'est jamais optionnelle. L'objectif est de fournir une base
de très haute qualité, tout en reconnaissant que la validation humaine
reste la référence finale.

### 1.7 Contraintes de conception

Aucune fonctionnalité ne doit complexifier inutilement l'installation.

Le temps de dépannage doit rester faible grâce à une architecture
lisible.

Toutes les fonctionnalités doivent être compatibles avec un usage local.

Les évolutions futures ne doivent pas remettre en cause les principes
fondateurs.

### 2.8 Contrats d'architecture

Les couches communiquent exclusivement selon les dépendances définies
par le SDD. Toute violation constitue un défaut d'architecture.

L'interface Streamlit appelle uniquement les services métier.

Les services sont les seuls autorisés à appliquer les règles métier.

Les repositories n'effectuent que des opérations de persistance.

Le Worker ne communique jamais directement avec l'interface.

Les fournisseurs IA sont encapsulés derrière une interface unique.

### 2.9 Gestion des transactions

Toute modification de l'état métier est réalisée dans une transaction
SQLite. Les écritures de fichiers et les mises à jour de la base doivent
rester cohérentes.

Commit uniquement après succès complet de l'opération.

Rollback automatique en cas d'erreur.

Les écritures de translated.md sont atomiques.

Les exceptions sont propagées aux services puis journalisées.

#### 3.1.1 Préconditions générales

Avant toute opération, l'application doit être initialisée, la base
SQLite disponible et la configuration IA valide.

#### 3.1.2 Postconditions générales

Chaque opération métier met à jour SQLite, les journaux et l'état de
l'interface de manière cohérente.

#### 3.1.3 Cas d'erreur communs

Projet inexistant.

Document introuvable.

Configuration IA invalide.

Espace disque insuffisant.

Erreur de conversion.

Fournisseur IA indisponible.

#### 3.1.4 Critères d'acceptation

Chaque exigence fonctionnelle est considérée conforme lorsqu'elle est
implémentée, testée et traçable via un identifiant REQ.

### 4.9 Cycle de vie métier

Chaque document suit obligatoirement le cycle : Import → Conversion →
Validation → Traduction → Révision → Vérification contextuelle →
Validation finale → Édition manuelle éventuelle → Export.

### 4.10 Règles de cohérence

Un document ne peut être exporté que s'il est terminé.

Un chapitre supprimé est exclu définitivement du projet.

L'ordre des chapitres est identique pour la traduction, le contexte et
l'export.

Les statistiques sont recalculées après toute modification manuelle.

Toute erreur métier doit être journalisée.

### 4.11 Règles de verrouillage

Impossible de modifier l'ordre pendant une traduction.

Impossible de changer le fournisseur IA pendant un job actif.

Impossible de supprimer un projet en cours de traduction sans annulation
préalable.

### 5.8 Contrats des services

Chaque service expose une API métier stable. Les services ne
communiquent jamais via l'interface utilisateur.

ProjectService : créer, renommer, supprimer et valider un projet.

DocumentService : importer, convertir, réordonner et supprimer des
documents.

JobService : créer, planifier, suspendre, reprendre et annuler des jobs.

TranslationService : exécuter le pipeline IA complet.

ExportService : reconstruire puis exporter l'œuvre.

SettingsService : lire, valider et enregistrer la configuration.

### 5.9 Principes de découplage

Les services échangent des objets métier, jamais des composants
Streamlit.

Les repositories ne s'appellent jamais entre eux.

Le Worker utilise uniquement les services.

Les dépendances sont injectées afin de faciliter les tests.

### 5.10 Performances

Les traitements coûteux (conversion, traduction, export) sont délégués
au Worker afin de maintenir une interface réactive.

### 6.9 Exigences de portabilité

Le même conteneur doit fonctionner sans modification sur Windows, Linux
et les NAS compatibles Docker.

Aucun chemin absolu codé en dur.

Toutes les données persistantes sont stockées dans le volume data.

Les permissions des fichiers doivent être compatibles avec les
principaux systèmes de fichiers.

Les migrations SQLite sont automatiques au démarrage.

### 6.10 Santé du conteneur

Le conteneur expose un mécanisme de vérification de santé permettant de
confirmer que l'application est opérationnelle.

Base SQLite accessible.

Répertoire data accessible en lecture/écriture.

Worker démarré.

Configuration chargée.

### 7.16 Standards de développement

Toutes les contributions doivent respecter des conventions communes afin
de garantir un code homogène et facile à maintenir.

Type hints obligatoires sur les API publiques.

Docstrings pour les classes et services publics.

Aucune logique métier dans les callbacks Streamlit.

Fonctions courtes avec une responsabilité unique.

Journalisation structurée des erreurs.

### 7.17 Conventions de tests

Chaque module possède son propre dossier de tests. Les tests utilisent
des doubles (mocks/fakes) pour les fournisseurs IA et le système de
fichiers lorsque nécessaire.

### 8.11 Stratégie de migration

Toute évolution du schéma SQLite est gérée par des migrations
versionnées, transactionnelles et réversibles.

Sauvegarde logique avant migration majeure.

Version du schéma enregistrée en base.

Rollback automatique si une migration échoue.

Aucune migration ne modifie les fichiers source.md ou translated.md.

### 8.12 Contraintes d'intégrité

Un project_id référencé doit exister.

order_index est unique par projet.

Les états des jobs sont limités aux valeurs documentées.

Les chemins stockés sont relatifs au dossier du projet.

Toute suppression respecte les clés étrangères.

### 9.10 Cycle de vie d'un projet

Un projet évolue selon les états : Brouillon → Prêt → En cours → En
pause (optionnel) → Terminé ou Erreur. Un projet terminé reste
modifiable tant qu'aucune nouvelle traduction n'est lancée.

### 9.11 Règles d'import

Chaque fichier importé devient un document indépendant.

Les chapitres conservent l'ordre de dépôt jusqu'à une réorganisation
manuelle.

Les doublons de nom sont autorisés mais possèdent un identifiant interne
unique.

Un document en erreur n'empêche pas l'administration du projet.

### 9.12 Statistiques du projet

Le tableau de bord calcule automatiquement le nombre de documents, de
mots, de caractères, l'avancement global, les erreurs en attente et le
temps estimé restant lorsque des jobs sont actifs.

### 10.9 Pipeline de conversion détaillé

Chaque import suit systématiquement les étapes : copie temporaire,
analyse du format, extraction du contenu, conversion en GitHub Flavored
Markdown, conversion des images en WebP lossless, validation de la
structure, création de source.md puis suppression des fichiers
temporaires.

### 10.10 Validation de la conversion

Le nombre de titres est vérifié.

Les liens internes et les images sont contrôlés.

Le Markdown généré doit être syntaxiquement valide.

Les images référencées doivent exister.

Toute anomalie est enregistrée dans les journaux.

### 10.11 Performances attendues

La conversion doit être indépendante du fournisseur IA et pouvoir être
exécutée en lot sur plusieurs documents avant le lancement de la
traduction.

### 11.10 Segmentation et contexte

Lorsqu'un chapitre dépasse la fenêtre de contexte du modèle, il est
découpé en segments. La reconstruction respecte strictement l'ordre
d'origine. La vérification contextuelle utilise toujours le chapitre
précédent traduit, le chapitre courant traduit et le chapitre suivant
dans sa version source.

### 11.11 Contrats des appels IA

Chaque étape possède un prompt dédié et versionné.

Aucun appel ne doit modifier la structure Markdown.

Les images et leurs références doivent être conservées.

Chaque réponse est validée avant de passer à l'étape suivante.

Toute anomalie déclenche une nouvelle tentative ou un passage en erreur.

### 11.12 Critères de validation

Un document est considéré comme terminé uniquement lorsque les quatre
étapes du pipeline sont validées, que le Markdown reste cohérent et
qu'aucune erreur bloquante n'est détectée.

### 12.9 Ordonnancement

Le Worker exécute les jobs de manière séquentielle selon une file FIFO.
Les documents peuvent être ajoutés en masse avant le démarrage, mais un
seul job est actif à un instant donné.

### 12.10 Reprise et annulation

Une annulation attend la fin de l'appel IA en cours avant d'arrêter le
job.

Une reprise redémarre à la dernière étape validée.

Les étapes déjà validées ne sont jamais rejouées sauf demande explicite.

### 12.11 Métriques

Le Worker expose la progression globale, le document courant, le
fournisseur, le modèle, le temps écoulé, une estimation du temps restant
et le nombre de jobs restants.

### 12.12 Invariants d'exécution

Un seul Worker logique est autorisé.

Aucun job ne contourne la file d'attente.

Chaque changement d'état est enregistré dans SQLite et dans les
journaux.

### 13.11 Navigation et ergonomie

La navigation doit limiter le nombre de clics et rendre les traitements
longs compréhensibles.

### 13.12 Composants réutilisables

Tableaux triables et filtrables.

Barres de progression par document et globales.

Panneaux d'état du Worker et du fournisseur IA.

Notifications de succès, avertissement et erreur.

### 13.13 Glisser-déposer

Import multiple de fichiers.

Réorganisation visuelle des chapitres.

Mise à jour immédiate de l'ordre dans SQLite.

Verrouillage pendant une traduction.

### 13.14 Accessibilité

Responsive PC, tablette et smartphone.

Contraste compatible avec les thèmes clair, sombre et sépia.

Libellés explicites et messages d'erreur compréhensibles.

### 14.10 Gestion des fournisseurs

Le changement de fournisseur conserve les autres paramètres compatibles.

Chaque fournisseur expose les modèles disponibles via une interface
commune.

La configuration active est unique pour toute l'application.

### 14.11 Validation des modèles

Vérification de la disponibilité du modèle avant lancement.

Détection automatique des modèles Ollama et LM Studio.

Message explicite si le modèle n'est plus disponible.

### 14.12 Paramètres avancés

Température, contexte maximal et options compatibles avec le
fournisseur.

Les paramètres non supportés sont masqués automatiquement.

### 14.13 Sécurité de la configuration

Les clés API ne sont jamais affichées en clair.

Les tests de connexion n'enregistrent jamais les secrets dans les
journaux.

### 15.9 Reconstruction de l'œuvre

L'export assemble exclusivement les fichiers translated.md selon
order_index. Les chapitres supprimés sont ignorés.

### 15.10 Contrôles avant export

Tous les documents sont terminés.

Aucun job n'est actif.

Toutes les images référencées existent.

Le Markdown est valide.

### 15.11 Gestion des erreurs d'export

Aucun fichier partiel n'est conservé.

Les erreurs sont journalisées.

L'utilisateur reçoit un message explicite.

### 15.12 Invariants

L'export ne modifie jamais source.md ni translated.md.

Les fichiers temporaires sont supprimés après téléchargement.

### 16.9 Politique de journalisation

La journalisation doit fournir suffisamment d'informations pour
diagnostiquer un problème sans divulguer de données sensibles.

Horodatage UTC pour chaque événement.

Niveaux DEBUG, INFO, WARNING, ERROR et CRITICAL.

Identifiant du projet et du document lorsque pertinent.

### 16.10 Résilience

Redémarrage sans perte des données validées.

Détection des fichiers temporaires orphelins.

Vérification automatique de l'intégrité SQLite au démarrage.

### 16.11 Sécurité des données

Aucun contenu de chapitre dans les journaux.

Les mots de passe et clés API ne sont jamais affichés.

Les écritures sensibles sont limitées au volume data.

### 16.12 Audit

Les événements majeurs (création, suppression, import, traduction,
export et erreurs) restent consultables depuis l'interface de
journalisation.

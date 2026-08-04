# NovelTrad — SDD

## Chapitres 16 à 20

# Chapitre 16 -- Journalisation, sécurité et robustesse

### 16.1 Objectif

Garantir la traçabilité, la sécurité des données et la robustesse de l'application.

### 16.2 Journalisation

Tous les événements importants sont enregistrés : démarrage, arrêt, import, conversion, traduction, export, erreurs et changements d'état.

### 16.3 Sécurité

`APP_PASSWORD` est lu uniquement depuis le `.env`. Les clés API sont protégées et ne sont jamais affichées dans les journaux.

### 16.4 Robustesse

Toutes les écritures sont atomiques. Les transactions SQLite assurent la cohérence des métadonnées.

### 16.5 Reprise après incident

Après un redémarrage, les jobs interrompus sont restaurés à leur dernière étape validée.

### 16.6 Nettoyage

Les fichiers temporaires sont supprimés automatiquement au démarrage et après les exports.

### 16.7 Diagnostics

L'interface affiche l'état du Worker, du fournisseur IA, de la base SQLite et les erreurs récentes.

### 16.8 Invariants

Aucun secret n'est inscrit dans les journaux. Les erreurs utilisateur et techniques sont clairement distinguées.

### 16.9 Politique de journalisation

La journalisation doit fournir suffisamment d'informations pour diagnostiquer un problème sans divulguer de données sensibles.

- Horodatage UTC pour chaque événement.
- Niveaux `DEBUG`, `INFO`, `WARNING`, `ERROR` et `CRITICAL`.
- Identifiant du projet et du document lorsque pertinent.

### 16.10 Résilience

- Redémarrage sans perte des données validées.
- Détection des fichiers temporaires orphelins.
- Vérification automatique de l'intégrité SQLite au démarrage.

### 16.11 Sécurité des données

- Aucun contenu de chapitre dans les journaux.
- Les mots de passe et clés API ne sont jamais affichés.
- Les écritures sensibles sont limitées au volume `data`.

### 16.12 Audit

Les événements majeurs — création, suppression, import, traduction, export et erreurs — restent consultables depuis l'interface de journalisation.

# Chapitre 17 -- Tests et critères d'acceptation

### 17.1 Objectif

Définir la stratégie de validation garantissant que chaque exigence est correctement implémentée.

### 17.2 Tests unitaires

Chaque service métier est testé indépendamment. Les appels IA, SQLite et le système de fichiers sont simulés lorsque nécessaire.

### 17.3 Tests d'intégration

Validation des flux complets : création de projet, import, pipeline, export et reprise après incident.

### 17.4 Tests d'interface

Vérification des écrans principaux sur ordinateur et smartphone, en français et en anglais.

### 17.5 Tests de robustesse

Arrêt pendant une traduction, reprise automatique, rollback SQLite et intégrité des fichiers Markdown.

### 17.6 Critères d'acceptation

Toutes les exigences `REQ` doivent être couvertes par au moins un test documenté avant une version stable.

### 17.7 Non-régression

Chaque correction de bug doit être accompagnée d'un test empêchant sa réapparition.

### 17.8 Invariants

Aucune version ne peut être publiée si un test critique échoue.

### 17.9 Couverture minimale

- 100 % des exigences critiques sont couvertes par des tests.
- Tous les services métier disposent de tests unitaires.
- Chaque pipeline complet dispose de tests d'intégration.

### 17.10 Tests de performance

- Import massif de documents.
- Exécution prolongée du Worker.
- Validation des migrations SQLite.

# Chapitre 18 -- Diagrammes et modèles

### 18.1 Objectif

Centraliser les représentations d'architecture et de flux utilisées dans le projet.

### 18.2 Diagramme de composants

Décrit les relations entre Streamlit, les services métier, les repositories, le Worker, SQLite, le système de fichiers et les fournisseurs IA.

### 18.3 Diagramme de séquence

Présente le déroulement complet : création du projet, import, conversion, traduction, révision, validation et export.

### 18.4 Diagramme de données

Représente les principales tables SQLite et leurs relations.

### 18.5 Cycle de vie d'un document

Illustration des états d'un document, de l'import à l'export.

### 18.6 Cycle de vie d'un job

Illustration des transitions `Waiting → Queued → Running → Retrying/Paused → Completed ou Failed`.

### 18.7 Conventions

Tous les diagrammes UML utilisent une nomenclature cohérente avec les noms des modules et services définis dans ce SDD.

### 18.8 Invariants

Les diagrammes sont documentaires : en cas de divergence, le texte normatif du SDD fait foi jusqu'à leur mise à jour.

### 18.9 Diagrammes UML

Les diagrammes obligatoires sont :

- diagrammes de classes ;
- diagrammes de séquence ;
- diagrammes d'états ;
- diagrammes de composants.

### 18.10 Maintenance des diagrammes

Toute évolution majeure de l'architecture impose une mise à jour des diagrammes concernés.

# Chapitre 19 -- Exigences (REQ) et traçabilité

### 19.1 Objectif

Assurer la traçabilité entre les exigences, l'implémentation et les tests.

### 19.2 Identifiants

Chaque exigence reçoit un identifiant unique `REQ-XXX` utilisé dans le code, les tests et la documentation.

### 19.3 Classification

Les exigences sont classées en fonctionnelles, techniques, sécurité, interface et performance.

### 19.4 Traçabilité

Chaque fonctionnalité implémentée référence les exigences qu'elle satisfait. Chaque exigence possède au moins un test associé.

### 19.5 Gestion des évolutions

Une modification d'exigence implique une mise à jour du SDD, des tests et, si nécessaire, des migrations de données.

### 19.6 Critères

Une exigence est considérée satisfaite uniquement lorsque son implémentation et ses tests sont validés.

### 19.7 Invariants

Aucune fonctionnalité ne doit être développée sans être rattachée à une ou plusieurs exigences documentées.

### 19.8 Matrice de traçabilité

Chaque exigence `REQ` est reliée aux modules, aux tests et aux sections du SDD correspondantes.

### 19.9 Gestion des changements

- Toute nouvelle exigence reçoit un identifiant unique.
- Les exigences obsolètes restent historisées.

# Chapitre 20 -- Annexes techniques

### 20.1 Glossaire

Définitions des termes techniques utilisés dans le SDD : GFM, Worker, Job, Pipeline, WebP, etc.

### 20.2 Arborescence de référence

Structure officielle des dossiers du projet et du volume `data`.

### 20.3 Conventions de nommage

Règles pour les modules, classes, services, tables SQLite et fichiers Markdown.

### 20.4 Formats d'échange

Description des formats importés et exportés ainsi que des contraintes de compatibilité.

### 20.5 Journal des décisions

Historique des choix d'architecture majeurs et justification des arbitrages.

### 20.6 Évolutions futures

Liste des améliorations envisageables sans remettre en cause l'architecture validée.

### 20.7 Références

Références documentaires : Markdown GFM, SQLite, Docker, Streamlit et fournisseurs IA.

### 20.8 Clôture

Le présent SDD constitue la référence technique unique du projet NovelTrad. Toute évolution devra modifier directement ce document.

### 20.9 Évolutions prévues

- Nouveaux fournisseurs IA.
- Nouveaux formats d'import et d'export.
- Optimisations du pipeline.

### 20.10 Révision du SDD

Le présent document est la référence unique et doit rester synchronisé avec l'implémentation.
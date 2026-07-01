# Volume 0 — Vision

## 0.1 Présentation

### Objectif

NovelTrad 2.0 est une application de bureau (Electron + Vue 3 + TypeScript) dédiée à la traduction assistée par IA de romans, web-novels et fan-fictions. L’objectif n’est plus de produire une traduction brute : il est de transformer un chapitre source en un chapitre **prêt à publier**, en un seul clic.

### Philosophie

- **Un seul bouton visible.** L’utilisateur clique sur *Traduire le chapitre*. Derrière, un workflow multi-agents exécute les étapes.
- **Autonomie totale.** Aucun serveur externe obligatoire : tout fonctionne localement avec Ollama (modèles recommandés : `qwen3.5:9b` pour la qualité, `qwen3.5:4b` pour la pré-traduction rapide).
- **Qualité prouvée.** Chaque chapitre reçoit un score qualité et un rapport de cohérence.
- **Extensibilité.** Le système de plugins permet d’ajouter de nouveaux modèles, exporteurs, agents ou workflows sans toucher au cœur.
- **Répétabilité.** Chaque projet est un dossier autonome contenant sources, lexique, traductions, cache, logs et base SQLite.

### Public visé

1. **Traducteurs amateurs** de web-novels chinois/coréens/japonais vers le français ou l’anglais.
2. **Éditeurs de fan-fictions** souhaitant industrialiser la relecture.
3. **Équipes de traduction** collaboratives (fichiers partagés via Git ou cloud).
4. **Développeurs** voulant étendre NovelTrad via plugins.

### Fonctionnalités principales (v1.0)

| ID | Feature | Priority |
|----|---------|----------|
| F01 | Gestion de projets autonomes (dossier + SQLite) | Must |
| F02 | Premier lancement guidé avec détection d’Ollama | Must |
| F03 | Configuration des fournisseurs IA (Ollama, OpenAI, Anthropic, Gemini, OpenRouter, LM Studio) | Must |
| F04 | Lexique structuré avec alias, catégories, priorité | Must |
| F05 | Translation Memory avec fuzzy matching | Must |
| F06 | Workflow multi-agents (pré-traduction, traduction, cohérence, lexique, grammaire, style, polish, QA, export) | Must |
| F07 | Vérification de cohérence avant/après | Must |
| F08 | Score qualité global et par dimension | Must |
| F09 | Export Markdown, TXT, DOCX, EPUB, HTML | Must |
| F10 | Historique des versions avec diff/rollback | Must |
| F11 | Traitement par lots avec file d’attente | Should |
| F12 | Auto-update via GitHub Releases | Should |
| F13 | Système de plugins | Could |
| F14 | RAG interne sur le lexique et les chapitres déjà traduits | Could |

### Fonctionnalités futures (v2.0+)

- Collaboration multi-utilisateurs (merge de traductions).
- Marketplace de plugins et de modèles.
- Mode serveur HTTP pour usage via navigateur.
- Comparaison côte à côte enrichie.
- Fine-tuning de modèle sur corpus projet.
- Audio/speech-to-text pour relecture.

## 0.2 Analyse des solutions existantes

### Points forts du marché

- **GPTWnTranslator** : pipeline automatique basé sur GPT.
- **OmegaT / Trados** : mémoire de traduction mature, mais interface lourde et pas d’IA native.
- **NovelAITrans** : workflow spécifique web-novel, mais peu extensible.
- **Deepl / Google Translate** : qualité générique, pas de gestion lexique propre.

### Points faibles

- Fragmentation : chaque outil fait une partie du travail.
- Peu de vérification automatique de cohérence.
- Gestion lexique manuelle ou inexistante.
- Pas de score qualité objectif.
- Dépendance aux API cloud coûteuses.

### Pourquoi repartir de zéro

La codebase v4 (PyQt6 + FastAPI Python) fonctionne mais mélange UI, backend, agents et pipeline dans un seul runtime Python. NovelTrad 2.0 adopte une architecture plus pérenne :

- UI moderne en Vue 3.
- Runtime Node.js unique côté desktop.
- Ollama comme seule dépendance IA locale.
- Workflow déclaratif, observable et testable.
- Système de plugins dès la conception.

## 0.3 Pourquoi NovelTrad ?

### Différenciation

| Problème des traducteurs IA classiques | Solution NovelTrad 2.0 |
|---|---|
| Traduction chapitre par chapitre sans mémoire | Translation Memory persistante au niveau phrase + RAG interne |
| Perte de cohérence entre chapitres | Lexique verrouillé, alias, cohérence source/cible mesurée |
| Glossaire statique et manuel | Extraction automatique de termes candidats + suggestions IA |
| Qualité subjective | Score qualité global + rapport par dimension |
| Pipelines non reproductibles | Workflow déclaratif, snapshots d'étape, retry/rollback |
| Dépendance aux API cloud | Ollama en local + providers cloud optionnels |

### Comparatif rapide

| Feature | NovelTrad | GalTransl | NovelForge | GPTWnTranslator |
|---|---|---|---|---|
| Multi-agent | ✅ | ✅ | ✅ | ❌ |
| Mémoire long terme | ✅ | ❌ | ✅ | ❌ |
| EPUB export | ✅ | ✅ | ❌ | ✅ |
| Workflow structuré | ✅ | ❌ | ✅ | ❌ |
| Score qualité objectif | ✅ | ❌ | ❌ | ❌ |
| 100 % local possible | ✅ | partiel | ❌ | ❌ |

*(Comparatif indicatif basé sur les documentations publiques des projets.)*

## 0.3 Roadmap

### MVP (Sprints 1–4)

- Electron + Vue 3 + Vite + Pinia fonctionnel.
- Création/ouverture de projet.
- Écran lexique et chapitres.
- SQLite + repositories.

### Version 1.0 (Sprints 5–12)

- Workflow multi-agents complet.
- Translation Memory et cohérence.
- Score qualité et export.
- Auto-update et tests E2E.

### Version 2.0

- Plugins, marketplace, RAG avancé, collaboration.

## ✅ Critères d’acceptation de la vision

- [ ] Le cahier des charges fonctionnel de v1.0 est complet et priorisé (table F01–F14 avec MoSCoW).
- [ ] Chaque fonctionnalité `Must` a un cas d’usage et un critère d’acceptation vérifiable dans les volumes correspondants.
- [ ] La roadmap est décomposée en sprints de 1 à 2 semaines avec des livrables mesurables (Volume 24).
- [ ] La différence entre NovelTrad v4 (PyQt6 + FastAPI Python monolithique) et NovelTrad 2.0 (Electron + Vue 3 + Node.js) est documentée dans ce volume.
- [ ] Le positionnement produit ("moteur de traduction de romans multi-agent") apparaît en haut du README et de la page d’accueil.

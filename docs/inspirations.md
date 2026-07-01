# Projets similaires et inspirations

Ce document rassemble les projets open source et commerciaux proches de **NovelTrad 2.0**. L'objectif n'est pas de tous les copier, mais d'identifier les patterns, les forces et les opportunités d'innovation pour notre architecture multi-agent de traduction littéraire.

::: tip
NovelTrad se positionne comme un **Multi-Agent Literary Translation Framework** — plus qu'un simple traducteur EPUB, moins qu'un CAT professionnel. Cette page aide à garder cette ligne claire.
:::


---

## Table récapitulative

| Projet | Type | Forces clés | Inspiration pour NovelTrad | Priorité d'étude |
|---|---|---|---|---|
| [epub-translator](https://github.com/oomol-lab/epub-translator) | Pipeline EPUB + IA | Traduction EPUB complète, affichage bilingue, multi-provider | Export EPUB, mode bilingue, UX lecteur | Must-study |
| [bbook-maker](https://pypi.org/project/bbook-maker/) | Outil CLI/Python | Multi-provider (OpenAI/Claude/Gemini/Ollama), EPUB bilingue | Gestion multi-modèles, simplicité | Inspiration |
| [gptwntranslator](https://github.com/combobulativedesigns/gptwntranslator) | Scraper + traducteur | Scraping web novels, EPUB automatique, pipeline end-to-end | MVP minimal, workflow "scrape → translate → export" | Inspiration |
| [honya](https://docs.rs/crate/honya/latest/source/README.md) | CLI/TUI Rust | Orchestrator / Translator / Reviewer, glossaire + personnages | Orchestration agents, boucle review → correction | Must-study |
| [LaTeXTrans](https://www.sourcepulse.org/projects/16076583) | Framework académique multi-agent | Parser / Translator / Validator / Summarizer / Terminology / Generator | QA agent, glossaire agent, validation pipeline | Must-study |
| [TransAgents](https://arxiv.org/abs/2405.11804) | Recherche multi-agent | Traduction littéraire longue, évaluation humaine + LLM | Cohérence stylistique, traduction de romans | Inspiration |
| [RepoTransAgent](https://arxiv.org/abs/2508.17720) | Recherche multi-agent | Repository-aware, RAG + correction + prompt dynamique | Mémoire globale du roman, contexte repository-aware | Inspiration |
| [multranslate](https://github.com/Lifailon/multranslate) | Comparateur de providers | Comparaison parallèle, détection langue, historique | Benchmark qualité, comparaison providers | Inspiration |
| [adaptNMT](https://arxiv.org/abs/2403.02367) | Framework NMT | UI training + eval, métriques intégrées | Dashboard qualité, scoring automatique | Inspiration |
| [AnythingLLM Desktop](https://useanything.com/) | App desktop LLM | Gestion modèles locaux, RAG, historique SQLite | Workspaces par roman, injection de contexte | Inspiration |
| [Chatbox](https://chatboxai.app/) | App desktop chat LLM | UI paramètres modèle par workspace | "Workspaces" par projet, paramètres modèle contextuels | Inspiration |
| [Sugoi Toolkit](https://www.youtube.com/watch?v=r8xFzIkFWJU) | Traducteur VN/LN offline | Découpage phrases, file d'attente, affichage côte à côte | Chunking, queue, UI côte à côte | Inspiration |
| [Ebook Translator (Calibre)](https://github.com/bookfere/Ebook-Translator-Calibre) | Plugin Calibre | Parsing EPUB propre, préservation balises, recompilation | Parsing EPUB sans casser le markup | Must-study |
| [OmegaT](https://omegat.org/) | CAT open source | Glossaires, mémoires de traduction, dictionnaires locaux | Glossaire verrouillé, TM, cohérence forcée | Must-study |
| [OpenNovel](https://www.reddit.com/r/machinetranslation/comments/1jvx963/i_found_it_too_hard_to_translate_web_novels_using/) | Extension navigateur | Simplicité extrême, scraping, glossaire auto, chunking | Zéro configuration, chunking intelligent | Inspiration |
| [LexiconForge](https://github.com/anantham/LexiconForge) | Web App | Feedback utilisateur 👍/👎, comparateur versions, exports EPUB enrichis, footnotes culturelles | Système de feedback, comparateur source/brute/IA, exports enrichis | Inspiration |
| [Glossarion](https://github.com/Shirochi-stack/Glossarion) | GUI PySide6 | 40+ providers IA (incl. Ollama), glossaire robuste, EPUB/manga, gestion quotas | Gestion multi-modèles, terminologie verrouillée, UI riche | Must-study |
| [NovelTrans](https://github.com/YuBing-link/noveltrans) | SaaS / plateforme | Projet resumable par épisode, QA queue, glossary lock/conflict, RAG TM, workspaces | Structure projet par épisode, file d'attente QA, termes forbidden/locked | Must-study |
| [TranslateBooksWithLLMs](https://github.com/hydropix/TranslateBooksWithLLMs) | Desktop App | Formats variés (EPUB, DOCX, SRT, TXT), préservation formatage, checkpoints, pas de limite taille | Reprise sur incident, robustesse formatage, pas de limite taille | Must-study |
| [OPUS-CAT](https://github.com/Helsinki-NLP/OPUS-CAT) | MT Engine + Plugins | Modèles NMT locaux Marian, offline, plugins Trados/memoQ | Option modèles NMT locaux pour confidentialité/performance | Inspiration |
| [PolyglotShelf](https://gitlab.com/sansors/polyglotshelf) | Service Docker + UI web + API REST | Traduction en masse EPUB/PDF/DOCX/TXT/SRT/MOBI/AZW3/FB2 via Ollama Cloud, file SQLite durable, merge incrémental, glossaires | Architecture Docker, gestion de file durable, merge incrémental de gros EPUB, API REST | Must-study |

---

## Projets récents identifiés (DeepSeek 2)

### PolyglotShelf

- **Type** : Service Docker + UI web + API REST.
- **Forces** : traduction en masse de EPUB/PDF/DOCX/TXT/SRT/MOBI/AZW3/FB2 via Ollama Cloud, orchestrateur mince qui route vers TranslateBooksWithLLMs / Calibre / pdf2zh-next, file SQLite durable, merge incrémental des gros EPUB découpés par chapitre, glossaires CSV, API REST documentée (OpenAPI).
- **Inspiration** :
  - architecture conteneurisée pour le déploiement serveur (v2.0+) ;
  - file d’attente SQLite durable et jobs qui survivent au redémarrage ;
  - merge incrémental des chapitres traduits pour les gros EPUB ;
  - gestion des glossaires via API ;
  - support de nombreux formats source au-delà de l’EPUB.

---

## Projets EPUB + IA

### epub-translator

- **Pourquoi regarder** : c'est le pipeline EPUB le plus propre du moment.
- **Points forts** : traduction EPUB complète, affichage bilingue, LLM multi-provider.
- **Ce qu'on peut en tirer** :
  - structurer l'export EPUB en deux pistes (original + traduction)
  - garder la navigation par chapitre et les métadonnées
  - permettre un mode "lecture bilingue" dans la UI

### bbook-maker

- **Pourquoi regarder** : simplicité et support Ollama natif.
- **Points forts** : CLI minimal, EPUB bilingue, multi-provider.
- **Ce qu'on peut en tirer** :
  - garder la config provider simple (URL + modèle + clé)
  - générer un EPUB côte à côte comme option d'export

### gptwntranslator

- **Pourquoi regarder** : c'est le MVP le plus direct.
- **Points forts** : scraping web novels, génération EPUB automatique.
- **Ce qu'on peut en tirer** :
  - le workflow idéal pour un nouvel utilisateur : source → traduction → EPUB
  - garder une version "one-shot" du pipeline pour les cas simples

---

## Projets multi-agent

### honya

- **Pourquoi regarder** : architecture 3 agents très proche de NovelTrad.
- **Agents** : Orchestrator, Translator, Reviewer.
- **Ce qu'on peut en tirer** :
  - séparer explicitement l'orchestrateur des agents de travail
  - ajouter une boucle review → correction avant le QA final
  - garder le glossaire et les personnages dans le contexte de l'orchestrateur

### LaTeXTrans

- **Pourquoi regarder** : c'est notre idée, mais appliquée à des papers.
- **Agents** : Parser, Translator, Validator, Summarizer, Terminology, Generator.
- **Ce qu'on peut en tirer** :
  - renommer nos agents selon des responsabilités très précises
  - ajouter un agent "Summarizer" qui maintient un résumé global du roman
  - formaliser le QA comme un validator indépendant

### TransAgents

- **Pourquoi regarder** : traduction littéraire ultra-longue avec évaluation humaine.
- **Ce qu'on peut en tirer** :
  - évaluer la cohérence stylistique sur plusieurs chapitres
  - permettre un mode "évaluation humaine" intégrée dans la UI
  - documenter les agents de relecture comme pairs

### RepoTransAgent

- **Pourquoi regarder** : RAG et contexte repository-aware.
- **Ce qu'on peut en tirer** :
  - enrichir la mémoire globale du projet (lexique + chapitres traduits)
  - prompts dynamiques en fonction du contexte du chapitre
  - indexation sémantique des chapitres précédents

---

## Outils TAO et professionnels

### OmegaT

- **Pourquoi regarder** : standard open source de la traduction assistée.
- **Ce qu'on peut en tirer** :
  - glossaires avec termes verrouillés
  - mémoires de traduction au format TMX
  - segmentation fine au niveau phrase
  - interface côte à cible avec statut segment par segment

### Plugins Calibre (Ebook Translator)

- **Pourquoi regarder** : Calibre domine la gestion d'eBooks et utilise SQLite.
- **Ce qu'on peut en tirer** :
  - parsing EPUB sans destruction du markup
  - recompilation fidèle du HTML
  - gestion des styles CSS et des métadonnées

---

## Apps desktop LLM

### AnythingLLM Desktop

- **Pourquoi regarder** : Electron + LLM local + base de données.
- **Ce qu'on peut en tirer** :
  - workspaces par projet (un workspace = un roman)
  - injection RAG dans le contexte
  - gestion de l'historique dans SQLite

### Chatbox

- **Pourquoi regarder** : UI très propre pour paramètres modèles.
- **Ce qu'on peut en tirer** :
  - paramètres modèles par workspace/projet
  - temperature, context length, system prompts configurables
  - interface minimaliste pour les non-tech

---

## Communauté et VN/LN

### Sugoi Toolkit

- **Pourquoi regarder** : outil communautaire pour Visual Novels et Light Novels.
- **Ce qu'on peut en tirer** :
  - découpage intelligent des phrases
  - file d'attente pour ne pas saturer le modèle local
  - affichage côte à côte original/traduction

### OpenNovel

- **Pourquoi regarder** : extension navigateur très simple.
- **Ce qu'on peut en tirer** :
  - zéro configuration pour le premier lancement
  - scraping + glossaire automatique
  - chunking intelligent

---

## Projets récents identifiés (DeepSeek 2)

### LexiconForge

- **Type** : Web App.
- **Forces** : feedback utilisateur 👍/👎, comparateur de versions (source vs brute vs fan vs IA), génération de footnotes culturelles, exports EPUB enrichis.
- **Inspiration** :
  - ajouter un système de feedback sur les paragraphes traduits
  - comparateur de versions côte à côte
  - exports EPUB avec notes et métadonnées enrichies

### Glossarion

- **Type** : GUI PySide6.
- **Forces** : 40+ providers IA (incluant Ollama), traduction manga (OCR + YOLO), gestion avancée des clés API et quotas, glossaire robuste.
- **Inspiration** :
  - gestion multi-modèles et multi-clés
  - terminologie verrouillée et gestion des conflits
  - UI riche pour le glossaire

### NovelTrans

- **Type** : SaaS / plateforme.
- **Forces** : projet resumable par épisode, file d'attente QA, extraction/mise à jour/conflits de glossaire, RAG translation memory, workspaces.
- **Inspiration** :
  - structure de projet par épisode
  - file d'attente QA pour erreurs de traduction
  - termes "forbidden" et "locked"

### TranslateBooksWithLLMs

- **Type** : Desktop App.
- **Forces** : formats variés (EPUB, DOCX, SRT, TXT), préservation parfaite du formatage, checkpoints, pas de limite de taille.
- **Inspiration** :
  - fiabilité et reprise sur incident
  - préservation sans faille du formatage source

### OPUS-CAT

- **Type** : MT Engine + Plugins.
- **Forces** : modèles NMT locaux Marian, offline, sécurisés, plugins Trados/memoQ.
- **Inspiration** :
  - option modèles NMT locaux en plus d'Ollama
  - cas d'usage confidentialité accrue ou performance

---

## Projets mentionnes comme concurrents mais non retenus comme inspiration

Ces outils ont ete identifies dans les retours externes comme comparables, mais leur architecture ou leur public cible est trop eloigne pour une reutilisation directe dans NovelTrad :

| Projet | Categorie | Pourquoi non retenu |
|---|---|---|
| **NovelGenerator** | Generation assistee | Generation complete de romans, pas traduction. |
| **NovelForge** | Creation assistee | Knowledge graph + creation, scope different. |
| **GalTransl** | Traduction VN | Patch de Visual Novels, pas pipeline EPUB/roman. |
| **Chinese Novel Translator** | Reddit/MVP | Fonctionnalites deja couvertes par `gptwntranslator` / `OpenNovel`. |
| **clipboard-based translator pipeline** | Reddit/MVP | Queue/batch deja couverts par `Sugoi Toolkit`, `PolyglotShelf`, `NovelTrans`. |

---

## Ce que NovelTrad doit retenir

1. **Multi-agent literary translation framework** : notre catégorie est là. Il ne faut pas se comparer aux simples translate tools.
2. **Glossaire verrouillé + TM** : la cohérence sur les longs romans est notre avantage.
3. **EPUB propre** : parsing et recompilation sans casser le markup.
4. **Workspace par projet** : chaque roman a son propre contexte, lexique, mémoire, paramètres modèle.
5. **Boucle review/QA** : un agent reviewer + une file d'attente QA avant validation.
6. **Checkpoints et resumability** : reprise sur incident critique pour des romans longs.
7. **UI côte à côte** : lecture bilingue et comparaison versions.
8. **Feedback utilisateur** : 👍/👎 pour améliorer itérativement la qualité.
9. **Termes forbidden/locked** : interdire certaines traductions comme le fait NovelTrans/Glossarion.
10. **Modèles NMT locaux** : option future pour confidentialité ou performance.

---

## Pistes d'évolution pour NovelTrad

| Piste | Priorité | Projet inspirant |
|---|---|---|
| Mode bilingue / côte à côte dans l'UI | Should | epub-translator, Sugoi Toolkit, LexiconForge |
| Workspaces par roman avec paramètres modèles | Should | AnythingLLM, Chatbox, NovelTrans |
| Agent Reviewer + file d'attente QA | Must | honya, NovelTrans, LaTeXTrans |
| Résumé global du roman pour cohérence | Should | LaTeXTrans, TransAgents |
| Parsing EPUB sans perte de balises | Must | Ebook Translator, Calibre |
| Checkpoints / reprise sur incident | Must | TranslateBooksWithLLMs, NovelTrans |
| Indexation sémantique des chapitres (RAG avancé) | Could | RepoTransAgent, NovelTrans |
| Dashboard qualité + benchmark providers | Could | multranslate, adaptNMT |
| Feedback utilisateur (👍/👎) sur les traductions | Could | LexiconForge |
| Termes "forbidden" et "locked" | Must | NovelTrans, Glossarion |
| Comparateur de versions source/brute/IA | Could | LexiconForge |
| Modèles NMT locaux | Could | OPUS-CAT |

---

## Références

- [epub-translator — GitHub](https://github.com/oomol-lab/epub-translator)
- [bbook-maker — PyPI](https://pypi.org/project/bbook-maker/)
- [gptwntranslator — GitHub](https://github.com/combobulativedesigns/gptwntranslator)
- [honya — Docs.rs](https://docs.rs/crate/honya/latest/source/README.md)
- [LaTeXTrans — SourcePulse](https://www.sourcepulse.org/projects/16076583)
- [TransAgents — arXiv](https://arxiv.org/abs/2405.11804)
- [RepoTransAgent — arXiv](https://arxiv.org/abs/2508.17720)
- [AnythingLLM](https://useanything.com/)
- [Chatbox](https://chatboxai.app/)
- [OmegaT](https://omegat.org/)
- [Ebook Translator for Calibre](https://github.com/bookfere/Ebook-Translator-Calibre)
- [LexiconForge — GitHub](https://github.com/anantham/LexiconForge)
- [Glossarion — GitHub](https://github.com/Shirochi-stack/Glossarion)
- [NovelTrans — GitHub](https://github.com/YuBing-link/noveltrans)
- [TranslateBooksWithLLMs — GitHub](https://github.com/hydropix/TranslateBooksWithLLMs)
- [OPUS-CAT — GitHub](https://github.com/Helsinki-NLP/OPUS-CAT)
- [PolyglotShelf — GitLab](https://gitlab.com/sansors/polyglotshelf)
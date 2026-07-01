# Matrice de reutilisation — NovelTrad 2.0 vs projets similaires

> Objectif : pour chaque feature cle de NovelTrad, identifier un projet open source existant dont on peut s'inspirer ou reutiliser des patterns, afin de creer le minimum de code maison.

---

## Legende

- **Pattern** : concept/architecture a reprendre tel quel.
- **Librairie** : dependance npm/pip directement utilisable.
- **Inspiration** : approche a adapter, pas de copie directe.
- **Must-study** : projet a etudier en priorite car tres proche.

---

## 1. Orchestration multi-agent

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Workflow declaratif, agents en sequence | **honya** (Rust CLI/TUI) | Pattern Orchestrator / Translator / Reviewer ; boucle review → correction. | Must-study |
| Pipeline Parser / Translator / Validator / Summarizer / Terminology / Generator | **LaTeXTrans** (academique) | Architecture des roles d'agents ; QA agent, glossaire agent, validation pipeline. | Must-study |
| Traduction litteraire longue, coherence stylistique | **TransAgents** (recherche) | Idees de coherence long terme et evaluation humaine + LLM. | Inspiration |
| RAG repository-aware, contexte global du roman | **RepoTransAgent** (recherche) | Indexation semantique des chapitres precedents pour enrichir le contexte. | Inspiration |

## 2. Export EPUB & parsing

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Traduction EPUB complete, affichage bilingue | **epub-translator** (OOMOL Lab), **PolyglotShelf** | Structure de pipeline EPUB ; mode bilingue ; UX lecteur ; file durable ; merge incremental. | Must-study |
| Multi-provider IA + EPUB bilingue | **bbook-maker** (PyPI) | Gestion multi-modeles ; simplicite d'UX. | Inspiration |
| Scrape web novel → EPUB auto | **gptwntranslator** | MVP ultra simple "scrape → translate → export". | Inspiration |
| Parsing EPUB sans casser le markup | **Ebook Translator for Calibre** | Extraction/recompilation propre des balises HTML dans l'EPUB. | Must-study |
| Formats varies, preservation formatage, checkpoints | **TranslateBooksWithLLMs**, **PolyglotShelf** | Robustesse formatage, reprise sur incident, pas de limite taille, file durable. | Must-study |
| Architecture Docker + API REST + file durable | **PolyglotShelf** | Service Docker, file SQLite durable, merge incremental de gros EPUB, API REST. | Must-study |

## 3. Glossaire & Translation Memory

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Glossaire verrouille + TM | **OmegaT** (CAT open source) | Memoire de traduction mature, glossaires, dictionnaires locaux. | Must-study |
| Glossaire robuste, 40+ providers, gestion quotas | **Glossarion** (PySide6 GUI) | Gestion multi-modeles, terminologie verrouillee, UI riche. | Must-study |
| Projet resumable par episode, file d'attente QA, termes forbidden/locked | **NovelTrans** (SaaS) | Structure projet par episode, QA queue, termes forbidden/locked. | Must-study |
| Feedback utilisateur 👍/👎, comparateur versions, footnotes | **LexiconForge** (Web App) | Systeme de feedback, comparateur source/brute/IA, exports enrichis. | Inspiration |

## 4. UI / Workspaces / Cote a cote

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Workspaces par roman avec parametres modeles | **AnythingLLM Desktop** | Gestion modeles locaux, RAG, historique SQLite, workspaces. | Inspiration |
| UI parametres modele par workspace | **Chatbox** | Logique de "workspace" avec temperature, context length, system prompts. | Inspiration |
| Affichage cote a cote source/traduction | **Sugoi Toolkit** | Decoupage phrases, file d'attente, affichage cote a cote. | Inspiration |
| Simplicite extreme, scraping, glossaire auto | **OpenNovel** (extension navigateur) | Zero configuration, chunking intelligent. | Inspiration |

## 5. Modeles NMT locaux & comparateurs

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Modeles NMT locaux Marian, offline | **OPUS-CAT** | Option modeles NMT locaux pour confidentialite/performance. | Inspiration (v1.5+) |
| Comparaison parallele de providers, benchmark | **multranslate** | Dashboard qualite, comparaison providers. | Inspiration (v1.5+) |
| Framework NMT avec UI training/eval | **adaptNMT** (recherche) | Metriques integrees, scoring automatique. | Inspiration (v1.5+) |

## 6. Parsing de fichiers source

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| DOCX → HTML → Markdown | **mammoth.js** | Librairie npm directement utilisable. | Librairie |
| EPUB parsing | **@likecoin/epub-ts** ou **epubjs** | Verifier la maturite ; sinon utiliser `adm-zip` + `jsdom`/`cheerio`. | A valider |
| Detection encodage | **chardet** / **iconv-lite** | Librairies npm standards. | Librairie |
| Detection langue | **franc** | Librairie npm directement utilisable. | Librairie |
| Decoupage phrase par langue | **franc** + custom, ou librairies NLP cible | Tokenisation basee sur la ponctuation cible. | Librairie / custom |

## 7. Export

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Generation DOCX | **docx** (dolanmiu) | Librairie npm directement utilisable. | Librairie |
| Generation EPUB | **epub-gen-memory** | Verifier la maturite ; alternative : generation manuelle avec `archiver`. | A valider |
| Validation EPUB | **epubcheck** (Java) | Lancer en sous-processus si disponible. | Outil externe |
| EPUB mode bilingue | **epub-translator**, **bbook-maker** | Structure paragraphes source/cote a cote ou alternes. | Must-study |

## 8. Developpement & distribution

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Build/packaging Electron | **electron-builder** | Outil standard. | Librairie |
| Auto-update | **electron-updater** | Integration standard avec electron-builder. | Librairie |
| Tests E2E Electron | **Playwright + @playwright/test** | Support experimental d'Electron. | Librairie |
| Tests unitaires | **Vitest** | Test runner rapide pour Node/Vue. | Librairie |
| Code signing / notarization | **electron-builder** docs + **Apple notarytool** | Configuration CSC_LINK, APPLE_ID, notarytool. | Documentation |

## 9. Securite & confidentialite

| Feature NovelTrad | Projets similaires | Ce qu'on peut recuperer | Priorite |
|---|---|---|---|
| Stockage securise des cles API | **keytar** (keyring OS) | Librairie npm standard pour Credential Locker / Keychain / libsecret. | Librairie |
| Chiffrement fallback cles API | Node.js `crypto` AES-256-GCM | Pattern documente dans `21-Security.md`. | Pattern |
| Isolation renderer/preload | Electron security baseline officielle | `contextIsolation`, `nodeIntegration: false`, `contextBridge`. | Pattern |
| Validation de chemins (path traversal) | Patterns Node.js + tests unitaires | `path.resolve` + verification prefixe. | Pattern |

---

## Detail des parties reutilisables par projet

Cette section precise, pour chaque projet identifie, **quelles fonctions, patterns ou librairies** sont concretement recuperables afin de minimiser le code maison.

### Projets Must-study

#### honya (Rust CLI/TUI)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Architecture a 3 roles : `Orchestrator`, `Translator`, `Reviewer`.
  - Boucle `review → correction` avant validation finale.
  - Glossaire et personnages maintenus dans le contexte de l'orchestrateur.
- **Recuperation dans NovelTrad** :
  - Decomposer l'agent `Reviewer` de honya en `ConsistencyAgent`, `QAAgent`, `PolishAgent`.
  - Ajouter un mecanisme de retry automatique quand un step retourne un score insuffisant.
  - Voir `docs/volumes/07-Workflow.md`, `08-Agents.md`.

#### LaTeXTrans (framework academique multi-agent)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Roles d'agents : `Parser`, `Translator`, `Validator`, `Summarizer`, `Terminology`, `Generator`.
  - Agent `Summarizer` qui maintient un resume global du document.
  - Agent `Validator` / QA formel avec schema de sortie JSON.
- **Recuperation dans NovelTrad** :
  - Renommer / aligner les agents existants sur ces responsabilites precises.
  - Ajouter un agent `Summarizer` (v1.5) pour maintenir un resume du roman et ameliorer la coherence long terme.
  - Formaliser le `QAAgent` comme un validateur independant avec sortie JSON structurée.
  - Voir `docs/volumes/08-Agents.md`, `12-Quality.md`.

#### epub-translator (OOMOL Lab)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Pipeline EPUB complet : extraction → traduction → recompilation.
  - Mode bilingue (original + traduction) preserve dans le fichier EPUB.
  - Multi-provider LLM configurable.
  - UX lecteur avec navigation par chapitre.
- **Recuperation dans NovelTrad** :
  - Structurer l'export EPUB en deux pistes (source + cible) ou alternance de paragraphes.
  - Conserver les metadonnees OPF et la table des matieres.
  - Permettre un mode "lecture bilingue" dans l'UI.
  - Voir `docs/volumes/13-Export.md`.

#### Ebook Translator for Calibre
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Parsing EPUB sans destruction du markup HTML.
  - Recompilation fidèle des balises, styles CSS, metadonnees.
  - Gestion des tags inlines (`<span>`, `<em>`, `<strong>`) pendant la traduction.
- **Recuperation dans NovelTrad** :
  - Utiliser une strategie de parsing DOM (`cheerio` / `jsdom`) pour extraire le texte sans perdre les balises.
  - Mapper les fragments traduits aux noeuds d'origine.
  - Voir `docs/volumes/05-Project-Management.md`, `13-Export.md`.

#### OmegaT (CAT open source)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Memoire de traduction au format TMX.
  - Glossaires avec termes verrouilles.
  - Segmentation fine au niveau phrase.
  - Interface cote-a-cote source/cible avec statut segment par segment.
- **Recuperation dans NovelTrad** :
  - Implementer l'import/export TMX (`docs/volumes/09-Translation-Memory.md`).
  - Appliquer les termes verrouilles imperativement (`docs/volumes/10-Lexicon.md`).
  - Segmenter au niveau phrase avant stockage TM.
  - S'inspirer de l'UI cote-a-cote segmentee pour l'ecran de relecture.

#### Glossarion (PySide6 GUI)
- **Type** : Inspiration.
- **Parties interessantes** :
  - Gestion de 40+ providers (OpenAI, Anthropic, Gemini, OpenRouter, Ollama, etc.).
  - Gestion avancee des cles API et des quotas.
  - Glossaire robuste avec terminologie verrouillee.
  - Gestion des conflits de traduction.
- **Recuperation dans NovelTrad** :
  - Etendre le `AiRouter` pour supporter les providers cloud optionnels.
  - Ajouter une table `provider_quotas` ou une configuration de limites.
  - Renforcer l'interface de gestion du lexique avec conflits et verrouillage.
  - Voir `docs/volumes/03-AI-Models.md`, `10-Lexicon.md`.

#### NovelTrans (SaaS / plateforme)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Structure de projet resumable par episode.
  - File d'attente QA pour erreurs de traduction.
  - Termes `forbidden` et `locked` avec resolution de conflits.
  - RAG translation memory et workspaces.
- **Recuperation dans NovelTrad** :
  - Persister l'etat du workflow par chapitre dans `job_steps` pour permettre la reprise.
  - Implementer une file d'attente QA dans l'UI.
  - Ajouter le champ `forbidden` aux entrees du lexique.
  - Voir `docs/volumes/07-Workflow.md`, `10-Lexicon.md`, `09-Translation-Memory.md`.

#### TranslateBooksWithLLMs (Desktop App)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Support de formats varies (EPUB, DOCX, SRT, TXT).
  - Preservation du formatage source.
  - Systeme de checkpoints / reprise sur incident.
  - Aucune limite de taille grace au decoupage.
- **Recuperation dans NovelTrad** :
  - Decouper les gros EPUB par chapitre avant traduction.
  - Sauvegarder l'etat apres chaque step dans SQLite.
  - Permettre la reprise apres crash ou fermeture de l'app.
  - Voir `docs/volumes/07-Workflow.md`, `13-Export.md`, `22-Performance.md`.

#### PolyglotShelf (Service Docker + UI web + API REST)
- **Type** : Pattern / Inspiration.
- **Parties interessantes** :
  - Orchestrateur mince qui route vers differents traducteurs selon le format.
  - File d'attente SQLite durable et jobs survivant au redemarrage.
  - Merge incremental des gros EPUB decoupes par chapitre.
  - Glossaires CSV et API REST documentee (OpenAPI).
- **Recuperation dans NovelTrad** :
  - Utiliser `better-sqlite3` comme file d'attente de jobs durable.
  - Implementer le merge incremental pour l'export EPUB multi-chapitres.
  - Garder l'architecture API REST en vue de la v2.0 serveur.
  - Voir `docs/volumes/06-Database.md`, `07-Workflow.md`, `13-Export.md`.

### Projets Inspiration

#### bbook-maker (PyPI)
- **Type** : Inspiration.
- **Parties interessantes** :
  - Configuration provider simple : URL + modele + cle.
  - Generation EPUB bilingue.
- **Recuperation dans NovelTrad** :
  - Garder le formulaire provider minimaliste (URL, modele, cle, temperature).
  - Proposer l'export EPUB cote-a-cote comme option.

#### gptwntranslator
- **Type** : Inspiration.
- **Parties interessantes** :
  - Scraping web novels → EPUB automatique.
  - Pipeline end-to-end ultra simple.
- **Recuperation dans NovelTrad** :
  - Offrir un mode "one-shot" pour les cas simples.
  - Documenter le flux ideal nouvel utilisateur : source → traduction → EPUB.

#### TransAgents (recherche)
- **Type** : Inspiration.
- **Parties interessantes** :
  - Traduction litteraire ultra-longue avec evaluation humaine + LLM.
  - Cohérence stylistique sur plusieurs chapitres.
- **Recuperation dans NovelTrad** :
  - Evaluer la coherence stylistique par comparaison de chapitres.
  - Permettre un mode evaluation humaine integree dans l'UI (v1.5+).

#### RepoTransAgent (recherche)
- **Type** : Inspiration.
- **Parties interessantes** :
  - RAG repository-aware.
  - Prompts dynamiques en fonction du contexte.
  - Indexation semantique des chapitres precedents.
- **Recuperation dans NovelTrad** :
  - Enrichir la memoire globale du projet (lexique + resumes + chapitres traduits).
  - Utiliser les embeddings Ollama pour l'indexation semantique (v1.5+).

#### multranslate
- **Type** : Inspiration (v1.5+).
- **Parties interessantes** :
  - Comparaison parallele de providers.
  - Detection de langue, historique.
- **Recuperation dans NovelTrad** :
  - Ajouter un dashboard de benchmark qualite entre providers.
  - Comparer plusieurs traductions d'un meme paragraphe.

#### adaptNMT (recherche)
- **Type** : Inspiration (v1.5+).
- **Parties interessantes** :
  - UI training/eval pour NMT.
  - Metriques integrees (BLEU, COMET, etc.).
- **Recuperation dans NovelTrad** :
  - Dashboard qualite avec scoring automatique.
  - Metriques de calibration sur le jeu de 20 chapitres.

#### AnythingLLM Desktop
- **Type** : Inspiration.
- **Parties interessantes** :
  - Workspaces par projet.
  - RAG / injection de contexte.
  - Historique dans SQLite.
- **Recuperation dans NovelTrad** :
  - Un workspace = un roman avec son lexique, sa TM, ses parametres modele.
  - Voir `docs/volumes/04-UI-UX.md`, `05-Project-Management.md`.

#### Chatbox
- **Type** : Inspiration.
- **Parties interessantes** :
  - UI de parametres modele par workspace (temperature, context length, system prompt).
- **Recuperation dans NovelTrad** :
  - Ecran de configuration des modeles par projet.

#### Sugoi Toolkit
- **Type** : Inspiration.
- **Parties interessantes** :
  - Decoupage intelligent des phrases.
  - File d'attente pour ne pas saturer le modele local.
  - Affichage cote-a-cote original/traduction.
- **Recuperation dans NovelTrad** :
  - Chunking des chapitres en paragraphes / phrases.
  - Limiter la concurrence pour Ollama local.
  - Vue cote-a-cote dans l'UI.

#### OpenNovel (extension navigateur)
- **Type** : Inspiration.
- **Parties interessantes** :
  - Zero configuration au premier lancement.
  - Scraping + glossaire automatique.
  - Chunking intelligent.
- **Recuperation dans NovelTrad** :
  - Wizard de premier lancement auto-detectant Ollama.
  - Extraction automatique de termes candidats au premier import.

#### LexiconForge (Web App)
- **Type** : Inspiration.
- **Parties interessantes** :
  - Feedback utilisateur 👍/👎 sur les paragraphes.
  - Comparateur de versions (source vs brute vs fan vs IA).
  - Footnotes culturelles, exports EPUB enrichis.
- **Recuperation dans NovelTrad** :
  - Système de feedback sur les traductions.
  - Comparateur de versions cote-a-cote.
  - Exports enrichis avec metadonnees et notes.

#### OPUS-CAT
- **Type** : Inspiration (v1.5+).
- **Parties interessantes** :
  - Modeles NMT locaux Marian, offline.
  - Plugins TAO (Trados/memoQ).
- **Recuperation dans NovelTrad** :
  - Option modeles NMT locaux en complement d'Ollama.
  - Cas d'usage confidentialite / performance.

---

## Concurrents identifies mais non retenus comme reutilisation

Ces projets ont ete mentionnes dans les retours comme comparables, mais leur architecture ou leur scope est trop eloigne pour une reutilisation directe :

| Projet | Pourquoi non retenu |
|---|---|
| **NovelGenerator** | Generation complete de romans, pas de traduction assistee. |
| **NovelForge** | Creation assistee avec knowledge graph, scope different. |
| **GalTransl** | Traduction de Visual Novels (patch VN), pas de pipeline EPUB/roman. |
| **Chinese Novel Translator** | Projet Reddit communautaire leger ; fonctionnalites deja couvertes par `gptwntranslator` / `OpenNovel`. |
| **clipboard-based translator pipeline** | Projet Reddit leger ; queue/batch deja couvert par `Sugoi Toolkit`, `PolyglotShelf`, `NovelTrans`. |

---

## Recommandations de reutilisation par phase

### MVP (sprints 1–4)
1. **Project structure** : s'inspirer de `honya` pour l'arborescence CLI/desktop.
2. **Parsing** : utiliser `mammoth.js`, `franc`, et une librairie EPUB validee.
3. **Database** : `better-sqlite3` + pattern Repository deja documente.
4. **Securite** : appliquer la baseline Electron officielle, valider `keytar`.

### v1.0 (sprints 5–12)
1. **Agents** : calquer les roles de `LaTeXTrans` (Parser/Validator/Terminology/Generator).
2. **Export EPUB** : etudier `epub-translator` et `PolyglotShelf` pour le pipeline et le mode bilingue.
3. **TM/Glossaire** : s'inspirer d'`OmegaT` et `NovelTrans` pour les termes locked/forbidden et la QA queue.
4. **Checkpoints** : reprendre le pattern de `TranslateBooksWithLLMs` et de `PolyglotShelf`.

### v1.5+ / v2.0
1. **RAG semantique** : s'inspirer de `RepoTransAgent` et `NovelTrans`.
2. **Feedback utilisateur** : reprendre le 👍/👎 de `LexiconForge`.
3. **NMT local** : option `OPUS-CAT` pour les cas de confidentialite.
4. **Marketplace plugins** : rester prudent ; commencer par un dossier `plugins/` local.

---

## Liens consolidés

- [epub-translator](https://github.com/oomol-lab/epub-translator)
- [bbook-maker](https://pypi.org/project/bbook-maker/)
- [gptwntranslator](https://github.com/combobulativedesigns/gptwntranslator)
- [honya](https://docs.rs/crate/honya/latest/source/README.md)
- [LaTeXTrans](https://www.sourcepulse.org/projects/16076583)
- [TransAgents](https://arxiv.org/abs/2405.11804)
- [RepoTransAgent](https://arxiv.org/abs/2508.17720)
- [multranslate](https://github.com/Lifailon/multranslate)
- [adaptNMT](https://arxiv.org/abs/2403.02367)
- [AnythingLLM](https://useanything.com/)
- [Chatbox](https://chatboxai.app/)
- [OmegaT](https://omegat.org/)
- [Ebook Translator for Calibre](https://github.com/bookfere/Ebook-Translator-Calibre)
- [LexiconForge](https://github.com/anantham/LexiconForge)
- [Glossarion](https://github.com/Shirochi-stack/Glossarion)
- [NovelTrans](https://github.com/YuBing-link/noveltrans)
- [TranslateBooksWithLLMs](https://github.com/hydropix/TranslateBooksWithLLMs)
- [OPUS-CAT](https://github.com/Helsinki-NLP/OPUS-CAT)
- [PolyglotShelf](https://gitlab.com/sansors/polyglotshelf)

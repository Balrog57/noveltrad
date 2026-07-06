# Gap Analysis — NovelTrad 2.1.3 → SDD 2.0

> **Date** : 2026-07-05
> **Périmètre** : Audit chirurgical du code en production (v2.1.3) vs le SDD VitePress (`docs/volumes/`).
> **Cadrage** : Durcissement de l'existant — **ne pas réinventer la roue**. Le code 2.1.3 implémente déjà la stack cible (Electron 31 + Vue 3 + TS + SQLite + 10 agents Ollama). Le `WORKFLOW_STATE.md` affirme que tous les volumes sont couverts ; l'audit révèle que la couverture est **large mais inégale** : plusieurs briques sont des **bouchons heuristiques MVP** non conformes au SDD, et le branching adaptatif (retry, QA score) est documenté mais absent.
> **Stack actuelle confirmée** : Electron 31 ESM · Vue 3.4 · TS 5.5 · `node-sqlite3-wasm` (synchrone, type better-sqlite3) · Ollama (`net.fetch`) · 782 tests verts · 10 agents · 10 prompts TS.

---

## 🔁 Revue post-implémentation T1-T15 (2026-07-06)

Suite à l'audit initial, 15 tâches correctives (T1-T15) ont été implémentées. Une **revue indépendante sceptique** (lecture du code réel, pas des commits/messages) a été conduite. Verdict factuel :

| # | Tâche | Verdict | Preuve file:line |
|---|-------|---------|------------------|
| **T1** | Sécurité (CSP/safeStorage/preload) | ✅ **Conforme** | CSP prod active `index.ts:55-89` + `session.defaultSession.webRequest.onHeadersReceived:81-88` ; `safeStorage` `secrets.ts:36-85`, SALT hardcodé supprimé ; preload log gardé par `import.meta.env.DEV` `preload/index.ts:102-103` |
| **T2** | Migration runner unifié | ✅ **Conforme** | Runner file-based `connection.ts:67-94`, `009_chapter_metadata.sql` existe, inline array supprimé. ⚠️ transaction raw `BEGIN` fragile (`connection.ts:81-82`) → Phase 4B |
| **T3** | Workflow (retry/branching/queue/resume) | ⚠️ **Partiel** 🐛 | Retry+branching QA `WorkflowEngine.ts:514-555` + p-queue `:772` + auto-resume `index.ts:270-272` présents. **MAIS** 🐛 double p-retry (AiRouter × Provider = jusqu'à 16 tentatives `AiRouter.ts:83` + `OllamaProvider.ts:26`) ; 🐛 auto-resume ignore jobs `single` (`WorkflowEngine.ts:874`) |
| **T4** | Câbler 3 agents LLM | ✅ **Conforme** | Consistency/Lexicon/Qa appellent `aiRouter.chat()` avec leurs prompts importés + fallback heuristique (`ConsistencyAgent.ts:57-64`, `LexiconAgent.ts:47-54`, `QaAgent.ts:72-79`) |
| **T5** | PromptLoader DB | ⚠️ **Partiel** 🐛 | **Dead code** : class correcte mais jamais instanciée, `setPromptLoader` jamais appelée, queries colonne `active` inexistante (table `prompts` migration 005 n'a pas cette colonne) → override DB non fonctionnel |
| **T6** | Agent I/O Zod | ✅ **Conforme** | `inputSchema`/`outputSchema` `Agent.ts:24,27`, `validateOutput()` appelé `WorkflowEngine.ts:501-512`, 10 agents équipés, 73 tests |
| **T7** | ConsistencyChecker 7/7 | ✅ **Conforme** | 7 métriques `ConsistencyChecker.ts:145-293`, pondération SDD §11.5 exacte `:82-90`, caps `:305-314`, tolérances zh-fr = SDD `:17-24` |
| **T8** | HallucinationDetector | ⚠️ **Partiel** 🐛 | Détecteur appelé **MAIS** hallucination = hardcoded `95` en fallback (`QualityChecker.ts:43-45`) ; QaAgent fallback ne passe pas `consistencyReport` (`QaAgent.ts:58-63`) → dimension = 90 |
| **T9** | EPUB epub-gen-memory | ⚠️ **Partiel** 🐛 | Dep `epub-gen-memory@^1.1.2` + import `ExportEngine.ts:14` + utilisé single `:565` et multi `:284`. **MAIS** 🐛 multi-chapitre hardcode `lang:"fr"` (`ExportEngine.ts:279`) ignore targetLanguage |
| **T10** | EPUB/DOCX import | ✅ **Conforme** | `readEpubSpine()` `ProjectManager.ts:858-899` lit le spine OPF ; DOCX mammoth styleMap Heading 1 `:752-766` |
| **T11** | TM 5 tiers | ⚠️ **Partiel** 🐛 | Segmentation + exact + global réels **MAIS** `findBestMatch()` 5-tier cascade a **0 caller production** (TranslateAgent n'appelle que `fuzzyMatches`) ; tier 5 = null pas embeddings |
| **T12** | TM MiniSearch | ✅ **Conforme** ⚠️ | Two-pass implémenté. 🐛 préfiltre SQL `\w{3,}` Latin-only → CJK fuzzy dégrade vers fallback |
| **T13** | RAG batch/seuil/reindex | ⚠️ **Partiel** 🐛 | Seuil ✅ (0.7). **MAIS** `computeEmbeddings`/`storeEmbeddings` batch + `reindex()` = **dead code jamais appelé** ; sqlite-vec declared unused (POC KO) |
| **T14** | Worker threads | 🐛 **Bug critique** | Fix named-export correct **MAIS** path `../services/agents/${agentId}.js` avec stage lowercase (`"translate"`) alors que fichiers sont PascalCase (`TranslateAgent.ts`) → **chaque import worker échoue → fallback silencieux systématique** (workers jamais fonctionnés) |
| **T15** | Signature code | ❌ **Non faite** | `forceCodeSigning`/`signAndEditExecutable`/`verifyUpdateCodeSignature` tous à `false` ; CSC/Apple vars en commentaires uniquement ; pas de build signé. **Reportée sine die** (décision utilisateur) |

**Bilan revue** : 6 conformes · 6 partielles (bugs) · 1 bug critique · 1 non-faite. **Plusieurs features = dead code non câblé.**

### Note RAG (décision utilisateur 2026-07-06)
Le SDD §9.3 (`docs/volumes/09-Translation-Memory.md:87-138`) **ne requiert aucune lib vectorielle** — brute-force + cosinus JS est 100% conforme (seuil `> 0.75`, critères d'acceptation qualitatifs uniquement). Le POC `sqlite-vec` a échoué sur `node-sqlite3-wasm` (pas de `loadExtension`). **Décision** : abandonner `sqlite-vec`, garder MiniSearch préfiltre + cosinus JS, optimiser (batch, cache, reindex réel). La dépendance `sqlite-vec@^0.1.9` sera supprimée.

### Feuille de route résiduelle (cycles correctifs suivant)
- **Phase 1** — 3 bugs runtime : T3 double-retry, T9 EPUB lang, T14 worker path
- **Phase 2** — Wiring dead code : T5 PromptLoader, T11 findBestMatch, T13 RAG batch/reindex + rm sqlite-vec
- **Phase 3** — Dégradations : T8 hallucination/consistency, T12 CJK tokenization
- **Phase 4** — Cleanup : T3 single-job resume, T2 robustesse transactions, doc finale
- **Exclu** : T15 signature (reportée sine die)

---

## TL;DR — verdict par bloc critique

| Bloc | Maturité réelle vs SDD | Verdict |
|---|---|---|
| Architecture Electron (ESM, sandbox, preload CJS, IPC Zod) | ✅ Solide | Conforme SDD 01/21 (à l'exception CSP + signature) |
| Base de données SQLite | ⚠️ Partiel | 14/15 tables SDD, mais dual-runner migrations, table `history` renommée, **aucune recherche vectorielle native** |
| Workflow / orchestration | ⚠️ Partiel | Pipeline séquentiel fiable, mais **pas de retry, pas de queue, pas de branching QA, pas d'auto-resume** |
| 10 Agents | ⚠️ Partiel | Tous présents, mais **9/10 prompts TS non câblés** et 6 agents tournent en heuristique pure sans LLM |
| Prompts (Vol 25) | ❌ Faible | `prompts` table morte, pas de versioning, pas de frontmatter YAML, 9/10 non utilisés |
| Mémoire de traduction (Vol 09) | ❌ Faible | Pas de segmentation phrase, pas de match exact câblé, pas de priorité 5 tiers, pas de global TM |
| RAG / embeddings | ⚠️ Partiel | Fonctionne mais **brute-force O(n) en JS**, pas de seuil, pas de réindexation, 1 round-trip Ollama/paragraphe |
| Lexique (Vol 10) | ⚠️ Partiel | Regex OK mais **pas de préservation casse, pas de forbidden words, pas d'import** |
| Consistency (Vol 11) | ❌ Faible | **3 métriques sur 7 manquantes** (dialogues/nombres/markup), formule de score fausse, tolérances trop laxes |
| Quality (Vol 12) | ❌ Faible | Heuristique MVP, **5/8 dimensions = constantes**, pas de LLM, HallucinationDetector non câblé |
| Export (Vol 13) | ⚠️ Partiel | 5 formats (MD/TXT/HTML/DOCX/EPUB), mais **EPUB maison sans spine/nav**, pas de PDF, lib SDD non utilisée |
| Import / parsing (Vol 05) | ⚠️ Partiel | mammoth+adm-zip+cheerio OK mais **EPUB flatten sans spine**, **DOCX sans détection Heading 1** |
| Sécurité (Vol 21) | ⚠️ Partiel | webPreferences locked, AES-256-GCM, nonce plugins — mais **CSP désactivée en prod, pas de signature, sel KDF hardcodé, preload log les args IPC** |
| Auto-update (Vol 17) | ✅ Solide | electron-updater câblé, canaux paramétrables (manque signature) |
| Plugins (Vol 15) | ✅ Solide | PluginHost + contexte + hot-reload + exemple ESM — complet |

---

## 1. Cartographie de l'Existant vs Cible 2.0

### 1.1 Ce qui est 100 % récupérable (ne pas toucher)

- **Stack Electron 31 ESM + electron-vite + electron-builder** — configuration éprouvée, build Windows signable.
- **Main process entry** `apps/desktop/src/main/index.ts:160-185` — `webPreferences` strict (sandbox:true, contextIsolation:true, nodeIntegration:false, webSecurity:true), preload forcé en **CJS** (`electron.vite.config.ts:33-39`) pour contourner le bug Electron #41460 (sandbox ≠ ESM preload). **Garder tel quel.**
- **Preload** `apps/desktop/src/preload/index.ts` — pont `contextBridge` avec allowlist de 79 canaux.
- **Couche IPC** — 66 handlers Zod-validés (`apps/desktop/src/main/ipc/handlers/*.ts`), router modulaire avec fault isolation par domaine.
- **Driver SQLite** — `node-sqlite3-wasm` (`apps/desktop/src/main/db/connection.ts`) utilisé **synchrone** comme better-sqlite3 (WAL + FK ON). **Garder, ne pas migrer vers better-sqlite3** (cf. §2.1).
- **OllamaProvider / OllamaManager** — utilisation correcte d'`electron.net.fetch` (v2.1.3), streaming NDJSON, `AbortSignal.timeout()`. Bonne implémentation.
- **StructuredLogger** (`utils/logger.ts`) — NDJSON, redaction, correlation IDs, `child()`. Conforme SDD 18.
- **Crypto secrets** (`utils/secrets.ts`) — AES-256-GCM, format `base64(iv+authTag+ciphertext)`. Algo correct, dérivation à durcir.
- **CalibrationService** (`services/CalibrationService.ts`) — régression linéaire least-squares par dimension, formule SDD §12.5 exacte. Bien bâti.
- **PluginHost / PluginContext / Disposable** (Vol 15) — complet, hot-reload dev, exemple ESM pré-compilé. Conserve.
- **Système UI** — composants `Nt*` + vues + stores Pinia + router. Mature, ne pas toucher.
- **AI cache** (`services/AiCache.ts`) — hash SHA-256(system+user+model+temp). Bon.
- **805 tests** (782 unit + E2E) — filet de sécurité solide pour refactor.

### 1.2 Ce qui doit évoluer (réécriture partielle)

| Bloc | Fichier(s) | Problème | Action |
|---|---|---|---|
| Migrations DB | `db/connection.ts:8-362` + `db/migrations/*.sql` | **Dual-runner** : tableau inline v1-9 ombre les 8 fichiers `.sql` (jamais exécutés). v9 inline n'a pas de `.sql` jumeau. | Source unique = fichiers `.sql`. Créer `009_chapter_metadata.sql`. Supprimer le tableau inline. |
| `history` table | `002_jobs.sql:42` vs SDD §6.2 | SDD nomme `history`, code crée `history_snapshots` avec un schéma différent (JSON `paragraphs`/`metadata`). | Soit renommer + aligner, soit **mettre à jour le SDD §6.2** pour entériner le design `history_snapshots` (recommandé : le design code est plus riche). |
| `statistics` table | `005_alias_export_prompts_stats.sql:37` vs SDD §6.2 | SDD = agrégat 1 ligne/projet (`total_chapters`...) ; code = table long/thin (`metric`, `value`). Incompatibles. | Soit implémenter la vue agrégée SDD, soit fixer le SDD sur le modèle long/thin (plus flexible). |
| WorkflowEngine | `managers/WorkflowEngine.ts` | Ordonnanceur séquentiel, `maxConcurrentJobs` lu **mais jamais appliqué**, pas de retry, pas de branching QA. | Introduire `p-queue` + `p-retry` + branch score (cf. §2.3 + §3). |
| `jobs` table | `002_jobs.sql:10` + `JobRepository.ts` | **Ledger de statut, pas une queue** (pas de `claimed_by`, `next_run_at`, dequeue atomique). | Étendre le schéma + ajouter dequeue atomique OU adopter p-queue en mémoire + persistance minimale. |
| Agents heuristic-only | `services/agents/{Consistency,Lexicon,Grammar,Style,Polish,Qa}Agent.ts` | 6 agents ne font **aucun appel LLM**, tournent en heuristique locale, ignorent leur system prompt SDD. | Câbler les prompts TS via `AiRouter.chat()` (les prompts existent déjà, ils sont juste morts). |
| ConsistencyChecker | `services/ConsistencyChecker.ts` | 3/7 métriques manquantes (dialogues/nombres/markup), formule score fausse, tolérances trop laxes. | Compléter les 7 métriques + appliquer pondération SDD §11.5 + caps. |
| QualityChecker | `services/QualityChecker.ts:9-44` | MVP heuristique, 5/8 dimensions = constantes, `comments = "Scoring heuristique MVP"`. | Brancher `ConsistencyReport.globalScore`, `HallucinationDetector`, et LLM eval pour fluency/style/dialogue. |
| LexiconEngine.apply | `services/LexiconEngine.ts:25-50` | Regex replace sans préservation de casse, pas de contrôle `forbidden`, pas de `import()`. | Ajouter préservation casse (regex capture + transform), check forbidden → warning, méthode `import()`. |
| RagEngine.findSimilar | `services/RagEngine.ts:81-125` | Brute-force O(n) sur tous les embeddings projet, pas de seuil, pas de batching. | Soit `sqlite-vec` KNN, soit MiniSearch préfiltre + Levenshtein. (cf. §2.6) |
| ExportEngine.toEpub | `services/ExportEngine.ts:605-641` (+ `:240-351`) | EPUB maison sans spine/TOC/nav.xhtml/NCX, langue hardcodée `fr`. | Migrer vers `epub-gen-memory` (cf. §2.4). |
| ProjectManager.extractEpub/Docx | `managers/ProjectManager.ts:761-881` | EPUB flatten sans spine ; DOCX perd les Heading 1 → chapter split foireux. | EPUB : lire `content.opf` spine ; DOCX : `mammoth` styleMap Heading 1. |

### 1.3 Ce qui est manquant (à bâtir)

- **Branche adaptative QA** (SDD §7.1) : `score≥90 → export`, `70-89 → retry weakest step`, `<70 → pause`. **Totalement absent** — `qualityThreshold` accepté en IPC mais jamais consommé (`WorkflowEngine.ts`).
- **Retry réseau Ollama** (SDD §7.10) : `Retry ×3 + backoff exponentiel + fallback provider`. Aucun retry dans `OllamaProvider.chat()` ni `AiRouter`.
- **Auto-resume des jobs au démarrage** (SDD §7.11) : `app.whenReady()` (`index.ts:207-287`) **n'appelle jamais** `JobRepository.listActive()`. Les jobs `running`/`paused` restent bloqués après un crash ; seuls les batch peuvent être repris manuellement.
- **Segmentation phrase de la TM** (SDD §9.2 `segmentSentences`) : nulle part. TM travaille au niveau paragraphe uniquement.
- **Match exact TM câblé** (SDD §9.9) : `exactMatch()` existe mais n'est jamais appelé par aucun agent.
- **TM globale cross-projet** + **priorité 5 tiers** (SDD §9.4) : absent.
- **Versioning des prompts en DB** (SDD §25.11) : `prompts` table existe mais n'est jamais lue/écrite. Pas de `frontmatter` YAML, pas de résolution "latest version".
- **CSP production** (SDD §21.6) : `setupCspHeaders()` (`index.ts:54-91`) early-return quand `!VITE_DEV_SERVER_URL`. **Pas de CSP en production**, pas de meta tag dans `index.html`.
- **Signature de code** (SDD §21.9) : `electron-builder.yml` à `forceCodeSigning:false`, `verifyUpdateCodeSignature:false`, `signAndEditExecutable:false`. Pas d'Authenticode.
- **OS keyring** (SDD §21.5) : `keytar`/`safeStorage` mentionnés en commentaire `secrets.ts:5,9-11` mais **jamais importés**. KDF via `scryptSync(userData, SALT="NovelTrad-v1-key-derivation", 32)` — sel **hardcodé constant**.
- **PDF export** (SDD §13.7 futur) : pas de cas `pdf` dans `ExportEngine.render()`, pas de plugin PDF livré.
- **Agent I/O JSON Schema validation** (SDD §8.13) : l'interface `Agent` (`agents/Agent.ts:7-14`) n'a **aucun champ** `inputSchema`/`outputSchema`. Pas de `validateOutput()` dans le runner.
- **Réindexation embeddings manuelle** (SDD §9) : pas de méthode `index()` / rebuild.

---

## 2. Analyse des Écarts par Volume Critique + recommandation OSS

### 2.1 Base de données (Vol 06)

**Écart technique**
- Driver : `node-sqlite3-wasm` au lieu de `better-sqlite3`. API synchrone équivalente, mais ce n'est pas la lib nommée par le SDD.
- **Dual migration runner** (`connection.ts:8-429`) : un tableau inline `MIGRATIONS` (v1-9) + un lecteur de fichiers `.sql` (v1-8). Les fichiers ne s'exécutent jamais sur DB fraîche car le tableau inline enregistre déjà v1-8 dans `__migrations`. v9 inline n'a pas de `.sql`.
- `history` → `history_snapshots` (renommage + redesign JSON non documenté au SDD).
- `statistics` : shape long/thin ≠ agrégat SDD.
- **Aucune extension vectorielle** chargée. `embeddings.embedding_json TEXT` = JSON sérialisé, pas de colonne native, pas d'index KNN, pas de FTS5/BM25.
- Pas de `down` migration (SDD §6.4 non implémenté).

**Recommandation OSS**
- ❌ **Ne pas migrer vers `better-sqlite3`** — `electron-rebuild` + toolchain C++ Windows + friction `app.asar.unpacked` à chaque montée de version Electron. **`node-sqlite3-wasm` est le bon choix** (WASM, synchrone, zero rebuild, perf suffisante pour mono-utilisateur desktop). **Mettre à jour le SDD §6.1** pour entériner.
- ✅ **`sqlite-vec`** pour la recherche vectorielle — extension C précompilée, API `CREATE VIRTUAL TABLE v USING vec0(emb float[768])` + `WHERE emb MATCH ? ORDER BY distance LIMIT k`. ⚠️ Pour `node-sqlite3-wasm`, vérifier le binding `sqlite-vec-wasm` ou charger le `.wasm` via le bridge WASM (les bindings officiels visent better-sqlite3 et node:sqlite). **Prouver le POC avant d'adopter.**
  - `npm i sqlite-vec` (ou variant wasm).
- **Action migrations** : source unique = fichiers `.sql` triés numériquement, créer `009_chapter_metadata.sql`, supprimer le tableau inline `MIGRATIONS`.

### 2.2 Workflow / orchestration (Vol 07)

**Écart technique**
- Pipeline = `for await` séquentiel dans `WorkflowRunner.runFromIndex()` (`WorkflowEngine.ts:376-420`). Pas de DAG, pas de parallélisme intra-chapitre ni intra-stage.
- `maxConcurrentJobs` lu (`WorkflowEngine.ts:694`) mais **jamais vérifié** avant de lancer un runner → `start()`/`startBatch()` créent un runner inconditionnellement.
- **Pas de retry** malgré SDD §7.10. `OllamaProvider.chat()` (`OllamaProvider.ts:23-42`) : un seul `net.fetch`, 300 s timeout, throw immédiat sur HTTP error.
- **Pas de branching QA** malgré SDD §7.1. `QaAgent` calcule le score, `WorkflowRunner` l'ignore. `qualityThreshold` présent en schéma IPC mais non consommé.
- **Pas d'auto-resume au démarrage** malgré SDD §7.11. `index.ts:207-287` n'appelle jamais `listActive()`. Resume batch = manuel via renderer uniquement.
- Worker threads (`agent-worker.ts`) : importe les agents par chemin et appelle `module.default` — or les agents exportent des **classes nommées**, pas default. Le worker échoue silencieusement et retombe sur `agent.execute()` direct → fonctionnalité morte.

**Recommandation OSS**
- ❌ **`bullmq` + Redis** — surdimensionné pour une app desktop mono-utilisateur. Rejeter.
- ✅ **`p-queue`** — file asynchrone pure JS, `new PQueue({concurrency})`, `.add(fn,{priority})`. À utiliser pour : (a) `maxConcurrentJobs` gate au niveau `WorkflowEngine.start()`, (b) parallélisme optionnel intra-batch (chapitres indépendants).
  - `npm i p-queue`
- ✅ **`p-retry`** — wrap `OllamaProvider.chat()` / `AiRouter.chat()` avec retry ×3 + backoff exponentiel (`ExponentialBackoff`). Implémente directement SDD §7.10.
  - `npm i p-retry`
- **Crash recovery** : étendre la table `jobs` avec `attempts INTEGER`, `next_run_at TEXT`, `claimed_by TEXT` + fonction `claimNextJob()` atomique (`UPDATE ... WHERE status='pending' RETURNING *`). Une centaine de lignes max, plus léger que toute lib durable.
- **Branching QA** : dans `WorkflowRunner.runStep('qa')`, après `agent.execute()`, lire `result.score` → si `≥qualityThreshold` continuer, si `70-89` retry weakest step, si `<70` `pause()`. ~30 lignes.

### 2.3 Agents + prompts (Vol 08 + 25)

**Écart technique** — le plus gros trou fonctionnel du projet :
- **10 agents présents**, mais **6 sont purement heuristiques** et **n'appellent jamais l'LLM** : `ConsistencyAgent`, `LexiconAgent`, `GrammarAgent`, `StyleAgent`, `PolishAgent`, `QaAgent`. (`SplitAgent` et `ExportAgent` légitimement sans LLM.)
- **9 system prompts sur 10 sont importés nulle part** — seul `TranslateAgent` importe et utilise `TRANSLATE_SYSTEM_PROMPT`. Les 9 autres `*_SYSTEM_PROMPT` sont du code mort.
- `prompts` table (Vol 25) : **jamais lue ni écrite**. Pas de versioning, pas de résolution latest, pas de frontmatter YAML `target_model`/`version`.
- Pas de JSON-Schema I/O par agent (SDD §8.13).
- `LexiconAgent` appelle directement `lexiconEngine.apply()` (regex) en court-circuitant le prompt LLM SDD §25 Agent-4.

**Recommandation**
- **Câbler les prompts existants** dans les 6 agents concernés via `this.services.aiRouter.chat(SYSTEM_PROMPT, userPrompt, {jsonMode:true})`. Les fichiers prompts **existent déjà**, il suffit de les importer et de construire le `build*UserPrompt()`. C'est un travail de câblage, pas de rédaction.
- Implémenter un **`PromptLoader`** qui lît la table `prompts` (override runtime) avec fallback sur les constantes TS (défaut compilé). Résolution "latest version" par `ORDER BY version DESC LIMIT 1`. Permet à un utilisateur avancé de tuner un prompt sans rebuild.
- Ajouter `inputSchema`/`outputSchema` (Zod) à l'interface `Agent` + `validateOutput()` dans le runner.

### 2.4 Export / Import (Vol 13 + 05)

**Écart technique — Export**
- 5 formats : `markdown`, `txt`, `html`, `docx`, `epub` (`ExportEngine.render()` switch `:491-504`). **Pas de PDF.**
- **EPUB maison via `adm-zip`** — pas la lib `epub-gen-memory` du SDD §13.3. Lacunes : pas de `nav.xhtml`, pas de NCX, langue hardcodée `fr` (`:337`), OPF single-chapter sans `properties="nav"` (`:631-636`). Multi-chapitre meilleur (`:240-351`) mais reste artisanal.
- `CustomRenderer` Map + `registerRenderer()` existent pour plugins → bon point d'extension.

**Écart technique — Import**
- EPUB : `adm-zip` + `cheerio` (`ProjectManager.ts:761-806`) itère les entrées HTML **sans lire le spine/TOC** de `content.opf`. Concatène tout puis re-split par regex → structure de chapitres perdue.
- DOCX : `mammoth.convertToHtml` puis regex HTML→Markdown (`:821-881`). **Les Heading 1 sont aplatis en `#`** au lieu d'être utilisés comme délimiteurs de chapitres (SDD §5.5).
- TXT/MD : `chardet.detectFileSync` + `iconv-lite.decode` — correct.
- Détection langue : `franc` (`:887-919`) — correct.

**Recommandation OSS**
- ✅ **`epub-gen-memory`** — remplace le EPUB maison. Maintenu, multi-chapitre natif, `lang`, `css` custom, EJS templates, EPUB v2/v3. Gère spine/nav/NCX correctement. ⚠️ Images fetchées par URL → passer data-URI pour local-first.
  - `npm i epub-gen-memory`
- ✅ **`mammoth` conservé**, mais ajouter un `styleMap` : `"p[style-name='Heading 1'] => chapter:fresh"` pour détecter les chapitres (SDD §5.5).
- **PDF** : plugin futur via `CustomRenderer` (le point d'extension existe). Pas urgent.

### 2.5 Translation Memory + RAG (Vol 09)

**Écart technique — TM**
- Table `translation_memory` (`001_initial.sql:48-58`), index `(project_id, source_text)`.
- `TranslationMemoryEngine` : `exactMatch()` (jamais appelé), `fuzzyMatches()` (Levenshtein sur **toutes les lignes du projet**, threshold 0.85, top 3). `TranslateAgent:98` n'utilise que fuzzy, sur le 1er paragraphe seulement.
- **Pas de segmentation phrase** (SDD §9.2). TM au niveau paragraphe uniquement.
- **Pas de normalisation** avant exact match (SDD §9.3).
- **Pas de priorité 5 tiers** (project-exact → project-fuzzy → global-exact → global-fuzzy → embeddings) ni de **TM globale cross-projet**.
- TMX import/export OK (`fast-xml-parser`).

**Écart technique — RAG**
- `RagEngine` : embeddings Ollama `nomic-embed-text` via `net.fetch`, similarité `compute-cosine-similarity`, stockage `embeddings.embedding_json TEXT` JSON.
- `findSimilar()` **brute-force** : charge tous les embeddings du projet, calcule cosinus en JS, top-K sans seuil.
- `storeEmbedding` idempotent par paragraphe (skip si déjà présent) — **pas de réindexation** si changement de modèle.
- 1 round-trip Ollama **par paragraphe** pendant la traduction (`WorkflowEngine.ts:574-583`) — pas de batch.

**Recommandation OSS**
- ✅ **`sqlite-vec`** (cf. §2.1) pour KNN vectoriel — remplace le brute-force O(n) par O(log n).
- ✅ **`minisearch`** pour préfiltre fuzzy TM two-pass : SQL `LIKE '%term%'` substring préfiltre → MiniSearch fuzzy `{fuzzy:0.2}` + Levenshtein refine sur le sous-ensemble. Évite de charger toutes les lignes du projet.
  - `npm i minisearch`
- **Segmentation phrase** : `sbd` est **déjà en dépendance** et utilisé par `ConsistencyChecker`. Le réutiliser pour `segmentSentences()` côté TM.
- **Batch embeddings** : `OllamaProvider.embeddings()` accepter un tableau, appeler `/api/embeddings` en boucle ou `/api/embed` (batch natif Ollama récent).

### 2.6 Consistency + Quality + Hallucination (Vol 11 + 12)

**Écart technique — Consistency**
- **3 métriques sur 7 implémentées** : paragraphs ✅, sentences ✅ (via `sbd`), length ✅. **Manquent : dialogues, numbers, markup.**
- `named_entities` : présence/absence only, pas de comparaison de comptes d'occurrences, pas de gestion des alias.
- **Formule de score fausse** : `100 - warnings.length*15` plat, au lieu de la moyenne pondérée SDD §11.5 (paragraphs:30/sentences:15/dialogues:15/length:10/NE:15/numbers:10/markup:5) + caps (paragraph issue → ≤50, locked-name → ≤70, missing number → ≤80).
- **Tolérances trop laxes** : code `zh-fr` sentence 0.5-2.0 / length 0.6-2.5 vs SDD 0.95-1.05 / 0.5-1.5.

**Écart technique — Quality**
- `QualityChecker` explicitement taggué `"Version simplifiee sans IA pour le MVP"` (`:9`).
- **5/8 dimensions = constantes** : consistency=90, lexicon=90, hallucination=95, dialogue=90, grammar=3 patterns regex triviaux.
- **`QA_SYSTEM_PROMPT` jamais appelé**. Pas d'éval LLM pour fluency/style/hallucination/dialogue.
- `consistency` dimension = 90 hardcodé au lieu d'être alimenté par `ConsistencyReport.globalScore`.

**Écart technique — Hallucination**
- `HallucinationDetector` est **construit et testé unitairement** (entités inventées cross-script, références suspectes `chapitre N`) mais **jamais instancié en production** — seul `tests/unit/quality-advanced.spec.ts:339` l'utilise. Code mort runtime.

**Recommandation**
- **Compléter les 7 métriques ConsistencyChecker** : `compareDialogues` (regex `「」""''` + `"-`), `compareNumbers` (`/\d+/g` + map occurences), `compareMarkup` (Markdown `**_[]()` + tags HTML). ~150 lignes.
- **Corriger la formule de score** : moyenne pondérée + caps, strictement SDD §11.5.
- **Câbler HallucinationDetector** dans `QualityChecker.evaluate()` (remplacer le `95` hardcodé).
- **Brancher `QA_SYSTEM_PROMPT`** via LLM eval pour fluency/style/dialogue (dimension `hallucination` peut rester locale via le détecteur — SDD §12.6 le permet).

### 2.7 Sécurité (Vol 21)

**Écart technique** (classé par criticité)
1. 🔴 **CSP production absente** — `index.ts:55-56` early-return. Pas de meta tag `index.html`. Violation directe SDD §21.6.
2. 🔴 **Pas de signature de code** — `electron-builder.yml:7,24,25` à `false`. SDD §21.9 mandate Authenticode/Apple. Conséquence : SmartScreen Windows, Gatekeeper macOS, alertes update.
3. 🟠 **Sel KDF hardcodé** — `secrets.ts:20` `SALT = "NovelTrad-v1-key-derivation"`. KDF via `scryptSync(userData, SALT, 32)` seulement. Un attaquant avec lecture fichier + connaissance du path `userData` (public) rederive la même clé.
4. 🟠 **Pas d'OS keyring** — `keytar`/`safeStorage` absents (SDD §21.5 tier-1).
5. 🟠 **Preload log les args IPC** — `preload/index.ts:102` `console.log("[IPC invoke]", channel, ...args)`. Risque fuite clé API via `settings:set`/`model:test` (SDD §21.7).
6. 🟡 **Gate main-process channels inefficace** — `router.ts:41-46` `ipcMain.on("message", preventDefault)` inopérant sur les invokes. La vraie protection est côté preload.
7. 🟡 Heuristique migration plaintext `length > 44` (clé courte cassée).

**Solide** (à conserver)
- `webPreferences` strict (sandbox+contextIsolation+no nodeIntegration+webSecurity).
- AES-256-GCM + authTag + IV aléatoire.
- Nonce CSRF dédié pour plugin permissions (`plugins.ts:40,190-214`).
- `preload-error` listener qui surface les échecs preload (défense ajoutée en v2.1.3).
- 53 Zod `.parse()` sur 66 handlers.

**Recommandation**
- **CSP** : implémenter `session.defaultSession.webRequest.onHeadersReceived` setant `Content-Security-Policy: default-src 'self'; script-src 'self'; ...` **en production aussi** (adapter pour `file://` : `default-src 'self' 'unsafe-inline' data:` minima).
- **Signature** : configurer certificat Windows (EV/OV) dans `electron-builder.yml` + `CSC_LINK`/`CSC_KEY_PASSWORD` en CI. Apple notarization via `notarize` API.
- **KDF** : remplacer le sel constant par `safeStorage` (Electron natif, OS-backed) pour la clé maître + enveler le sel. Si `safeStorage` indisponible, sel par-machine (`machine-id`).
- **OS keyring** : `electron.safeStorage.encryptString()` (déjà dans Electron 31, pas de dépendance). Remplace keytar.
- **Preload log** : retirer/guarder derrière `process.env.NODE_ENV === "development"`.

---

## 3. Plan d'Action Immédiat (Quick Wins)

> Objectif : lancer la transition **sans casser les 805 tests** ni le build. Séquencé par risque décroissant et valeur montante.

### Quick Win 1 — Sécurité critique (1 après-midi, 0 rupture)

```bash
# 1a. Désactiver le log IPC payload en production (preload)
#     apps/desktop/src/preload/index.ts:102 — wrapper dans if (import.meta.env.DEV)

# 1b. Activer CSP production
#     apps/desktop/src/main/index.ts:54-91 — retirer l'early-return, porter la CSP
#     dans session.defaultSession.webRequest.onHeadersReceived (SDD §21.6).

# 1c. Brancher safeStorage pour la clé maître (remplace sel hardcodé)
#     apps/desktop/src/main/utils/secrets.ts — electron.safeStorage.encryptString()
#     avec fallback scrypt + machine-id (pas de sel constant).
```

**Justification** : 3 correctifs localisés, 0 dépendance, filet de tests déjà présent (`secrets.spec.ts`, `path-traversal.spec.ts`).

### Quick Win 2 — Migration runner unifié (1 journée)

```bash
# 2a. Créer le fichier manquant
cat > apps/desktop/src/main/db/migrations/009_chapter_metadata.sql <<'SQL'
ALTER TABLE chapters ADD COLUMN metadata TEXT;
SQL

# 2b. Supprimer le tableau inline MIGRATIONS de db/connection.ts:8-362
#     (ne conserver que le runner par fichiers .sql, connection.ts:408-429).

# 2c. Lancer les tests DB + vérifier qu'une DB fraîche a bien chapters.metadata
npm run test --workspace=apps/desktop -- db
```

**Justification** : élimine la divergence source-de-vérité, rend les `.sql` consultables = source de schéma. Faible risque (les `.sql` couvrent déjà v1-8).

### Quick Win 3 — Workflow adaptatif (retry + branching QA, 2 jours)

```bash
npm i p-queue p-retry
```

Puis dans `apps/desktop/src/main/services/providers/OllamaProvider.ts` et `services/AiRouter.ts` :
- wrapper `chat()` dans `pRetry(fn, {retries:3, factor:2, minTimeout:1000})` — SDD §7.10.

Dans `managers/WorkflowEngine.ts` :
- `WorkflowRunner.runStep('qa')` : lire `result.score`, si `<qualityThreshold` → `this.pause()`, si `<threshold+20` → retry weakest step (`retryStep` interne), sinon continuer — SDD §7.1.
- `WorkflowEngine.start()` : vérifier `this.runners.size < maxConcurrentJobs` avant de créer un runner (queue via `PQueue`).

**Justification** : 2 libs légères (<10 ko), implémente les 3 plus gros écarts fonctionnels du workflow (retry, branching, concurrency), ~100 lignes de code, tests faciles à mocker (déjà des mocks OllamaProvider).

---

## 4. Roadmap post-Quick Wins (priorisée)

| Priorité | Bloc | Effort | Dépendance |
|---|---|---|---|
| P1 | Câbler les 9 prompts TS restants dans les 6 agents LLM | 3 j | Aucune — prompts déjà écrits |
| P2 | ConsistencyChecker 7/7 métriques + formule pondérée + caps | 2 j | — |
| P3 | HallucinationDetector câblé dans QualityChecker | 1 j | — |
| P4 | `p-queue` + `p-retry` + auto-resume au démarrage (`listActive()` in `whenReady`) | 2 j | Quick Win 3 |
| P5 | EPUB export → `epub-gen-memory` | 2 j | — |
| P6 | EPUB/DOCX import : lire spine + Heading 1 styleMap | 2 j | — |
| P7 | TM : segmentation phrase (`sbd`) + match exact câblé + priorité 5 tiers | 3 j | — |
| P8 | RAG : `sqlite-vec` KNN + seuil + batch embeddings | 3 j | POC binding wasm |
| P9 | TM fuzzy two-pass : `minisearch` préfiltre | 1 j | P7 |
| P10 | `PromptLoader` DB + fallback TS constant | 2 j | — |
| P11 | Signature code (Authenticode + Apple notarize) | 1 j | Certificat |
| P12 | Agent I/O Zod schemas + `validateOutput()` runner | 2 j | — |
| P13 | Worker threads : fix `module.default` → import nommé | 0,5 j | — |

**Total estimé** : ~25 jours-homme pour alignement complet SDD. Les Quick Wins (1+2+3) livrent ~40 % de la valeur perçue en ~3 jours.

---

## 5. Notes méthodologiques

- **Le `WORKFLOW_STATE.md` est optimiste** : il conclut « READY TO DEPLOY, tous volumes couverts » mais l'audit révèle que 6 agents sont heuristic-only, le QA branching est absent, la TM n'est pas segmentée, Consistency n'a que 4/7 métriques. Le revendu "couvert" s'entendait au sens *présence de fichiers*, pas *conformité fonctionnelle au SDD*. **Recommandation : introduire un critère "SDD-compliant" (pas seulement "SDD-covered") dans la Definition of Done.**
- **Pas de réécriture from-scratch justifiée**. La base saine (Electron + IPC + DB + providers + plugins + UI + tests) représente des milliers de lignes éprouvées. Les écarts sont des *trous fonctionnels dans des modules existants*, comblables par câblage + ajouts ciblés + 2-3 libs légères.
- **Libs à éviter** : `better-sqlite3` (rebuild natif), `bullmq` (Redis), toute dépendance Python.
- **Libs à adopter** : `sqlite-vec`, `p-queue`, `p-retry`, `epub-gen-memory`, `minisearch`. Total : 5 deps, toutes pure-JS, toutes alignées philosophie Node/Ollama local.

---

*Audit réalisé par ZCode (GLM-5.2) le 2026-07-05. Sources : exploration directe du code (13 sous-agents), SDD VitePress `docs/volumes/`, validation OSS via context7.*

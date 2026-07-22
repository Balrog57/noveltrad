# Changelog

## v3.0.1 — Fix: auto-clean stale recentProjects (2026-07-22)

### Fix
- `ProjectManager.listRecent()` retire désormais automatiquement les chemins
  devenus inaccessibles (dossier supprimé, déplacé, ou reste d'une install v2)
  du paramètre `recentProjects`. Auparavant, un chemin stale déclenchait un
  warning à **chaque lancement** sans jamais être nettoyé. Self-heal : un seul
  passage suffit à nettoyer les settings.

### Version
- Bump 3.0.0 → **3.0.1** (bugfix mineur, aucune feature).

## v3.0.0 — Simplification majeure : pipeline 4 agents + UI tout-en-un (2026-07-22)

> Refonte délibérée : moins de fonctionnalités, mais plus solide. Pilotée par
> les bugs/crashes réels et la complexité excessive de l'UI (12 vues).

### Breaking changes
- **Pipeline 12 → 4 stages** : `translate → proofread → glossary → validate`.
  Les stages split, pre_translate, consistency, grammar, style, polish, review,
  revise, qa, export sont supprimés (fusionnés dans les 4 nouveaux).
- **Schéma DB greenfield** : 18 migrations → 5. Les tables jobs, job_steps,
  history_snapshots, audit_log, embeddings, exports, prompts (override),
  statistics, model_calibrations, review_reports, agents, models sont supprimées.
  **Pas de migration de données** (aucun utilisateur en production).
- **Canaux IPC 79 → 52** : supprimé plugins, history, audit, workflow pause/
  resume/retry/quality-failed/resume-batch/list-active, ai:stream.

### Supprimé (features délibérément retirées)
- **Plugins** : PluginHost, PluginContext, système d'extensibilité complet.
- **RAG** : RagEngine, embeddings, recherche vectorielle.
- **Calibration** : CalibrationService (scoring calibré par modèle).
- **Audit / Historique** : AuditService, snapshots, diff, rollback.
- **Worker threads** : exécution désormais in-thread (plus simple, pas de freeze).
- **Boucle de révision pro** : ReviewAgent/ReviseAgent (v1.4).
- **QA auto-retry branching** : le validateur produit un score, l'utilisateur
  décide de relancer.

### Conservé (features utiles, non over-engineered)
- **EPUB multi-file splitting** (v2.3.0) — modèle chapters/paragraphs intact.
- **Translation Memory (TMX)** + **Lexique/Glossaire**.
- **Summarizer transverse** (cohérence cross-chapitre, déclenché après validate).
- **CLI `noveltrad`** (create/list/import/chapters/translate/export/status/doctor).
- **Auto-update** + **Settings** (Ollama, modèles, langues).

### UI (12 vues → 3)
- **Dashboard** (HomeView) : cartes projet + création/ouverture/suppression.
- **ProjectView tout-en-un** : sélecteur de chapitre, panes source/cible,
  bouton Traduire, inspecteur 4 agents temps réel, import/export.
- **Settings** : Ollama URL, modèle, langues, ton (inchangé).

### Architecture
- `SimpleWorkflowRunner` (~370 LOC) remplace `WorkflowEngine` (1370 LOC) +
  `WorkflowRunner` + `PauseController` + `QaBranchPolicy` + `agent-worker`.
- `ProofreaderAgent` (fusion grammar+style+polish via TextRefineAgent).
- `ValidatorAgent` (fusion consistency+qa ; internalise le ConsistencyReport).
- `AgentFactory` simplifié : switch 4 stages only.
- `QualityChecker` + `HallucinationDetector` conservés (dépendances Validator).

### Tests
- 570 tests (49 fichiers) — baseline v2.3.0 était 1054 (75 fichiers).
- Supprimé : tests des features retirées (plugins, RAG, calibration, audit,
  history, worker-threads, review/revise, qa-branch-policy, workflow-*).
- Ajouté : `v3-agents.spec.ts` (13), `simple-workflow-runner.spec.ts` (5),
  `db-migrations.spec.ts` réécrit (5).

### Version
- Bump 2.3.0 → **3.0.0** (breaking changes majeurs : pipeline, schéma, UI).

## v2.3.0 — EPUB multi-file splitting + CLI pilotable par agent IA (2026-07-20)

### Features
- **Découpage EPUB multi-fichiers** : les sammelbände (recueils de plusieurs romans dans un seul EPUB) sont maintenant correctement découpés. Chaque fichier xhtml du spine devient un chapitre séparé. Un chapitre de plus de 100 000 caractères est re-découpé au prochain séparateur de paragraphe (jamais au milieu). Validé sur Perry Rhodan Sammelband 1876-1899 : **73 chapitres** au lieu d'1 seul de 4M caractères.
- **CLI `noveltrad`** : nouvelle interface en ligne de commande complète, pilotable par un agent IA.
  - Commandes : `create`, `list`, `import`, `chapters`, `translate`, `export`, `status`, `doctor`.
  - Sortie JSON structurée (`--json`) : `{ ok, data }` ou `{ ok: false, error: { code, message } }`.
  - Exit codes sémantiques : 0 OK / 1 user / 2 Ollama / 3 DB / 4 traduction / 5 inconnu.
  - Progrès du workflow en NDJSON sur stderr (une ligne JSON par event).
  - `doctor` diagnostique Ollama + settings + modèles + recommandations.
  - Documentation complète : `docs/cli.md`.
- **Shim fetch** : `utils/fetch.ts` permet aux providers (OllamaProvider, RagEngine, OllamaManager) de fonctionner à la fois dans Electron (`electron.net.fetch`) et en CLI pure Node (`globalThis.fetch`).
- **Hook `onProgress`** sur WorkflowEngine : callback optionnel pour suivre le progrès du workflow sans BrowserWindow (CLI, scripts).

### Refactor
- `extractEpub` insère un séparateur `EPUB_FILE_BREAK` entre fichiers xhtml consécutifs.
- `splitIntoChapters` réécrit avec 3 niveaux de priorité : séparateur EPUB → patterns (Chapter/Chapitre/第N章) → texte entier. Chunking par taille appliqué à toutes les branches.
- Découplage d'Electron : 3 fichiers (OllamaProvider, RagEngine, OllamaManager) n'importent plus `net` depuis Electron directement.

### Tests
- `epub-split.spec.ts` (14 tests) : séparateur EPUB, patterns fallback, chunking par taille.
- Suite complète : 1054 tests (75 fichiers), +14 vs v2.2.7.
- Test e2e `epub-import.spec.ts` : valide 73 chapitres sur Perry Rhodan réel.

### Version
- Bump 2.2.7 → **2.3.0** (EPUB splitting + CLI = nouvelles features utilisateur).

## v2.2.7 — Refactor clean architecture consolidation (2026-07-20)

### Refactor (internal architecture — no behavior change)
Refactor complet de la structure du codebase (~30K LOC, 1022 tests préservés à
chaque commit). Objectif : séparer les responsabilités, augmenter la
modularité, réduire le couplage, préparer la scalabilité. **Aucun changement
de fonctionnalité** — 1022 tests verts du début à la fin.

- **DB layer** : nouveau `db/base/BaseRepository<T>` avec helpers `protected`
  opt-in (`queryOne`/`queryMany`/`execute`/`findById`/`deleteById` +
  `abstract map()`). Les 7 repositories migrent vers la base ; aucun
  call-site changé (9 sites d'import préservés).
- **IPC layer** : les 8 schémas Zod handler-local sont promus vers
  `packages/shared/src/schemas/ipc.ts` (source unique). Tuer une copie stale
  de `workflowStageSchema` dans les tests (manquait `review`/`revise` —
  bug-masker). Nouveau helper opt-in `ipc/safeHandle.ts` standardisant le
  error path (Zod parse + try/catch + log + re-throw lisible).
- **Services layer** : le god-class `AiRouter` (416 LOC, 8 responsabilités)
  devient une facade + 6 collaborateurs dans `services/ai/` :
  `TokenUsageAccumulator`, `CostEstimator`, `TextChunker`, `PromptResolver`,
  `jsonRepair.ts` (pure fn), `refusalDetector.ts` (pure fn). API publique
  byte-compatible — 0 changement aux 16 call-sites agents.
- **Managers layer** : nouveau `managers/ProjectPathResolver.ts` qui tue la
  duplication 8× du scan `recentProjects` (ProjectManager + 6 handlers IPC).
  Corrige 2 fuites DB latentes (history.ts et tm.ts oubliaient le try/finally
  intérieur). Nouveau `managers/workflow/PauseController.ts` extrait du
  WorkflowRunner (cohorte pause/resume/cancel auto-contenue).
- **Renderer** : nouveau dossier `composables/` (n'existait pas) avec
  `useAsyncAction` (wrapper loading/error) et `useStatusLabels`
  (consolidation de 9 sources de maps de statut). Nouveaux
  `utils/format.ts` et `utils/download.ts`. `WorkflowView` adopte
  `useStatusLabels` (5 fonctions locales → 1 import).
- **Cleanup** : suppression du `ipcChannelSchema` mort (enum Zod stale de
  25 entrées jamais importé). Fix d'une dérive latente : `workflow:quality-failed`
  manquait dans l'allowlist du preload (aurait rejeté un listener renderer).
- **Docs** : nouveau `ARCHITECTURE.md` (diagramme de couches, règles de
  dépendance, conventions par couche, cheat-sheet "où va le nouveau code",
  6 décisions architecturales documentées).

### Décisions de scope documentées
Plusieurs axes ont été volontairement réduits après audit car la version
"complète" aurait cassé le comportement ou ajouté du risque sans valeur :
- Enveloppe IPC `{ok,data,error}` imposée → aurait cassé les stores renderer
  (ils consomment la valeur de retour directement ; erreurs via throw path).
  `safeHandle` standardise le error path uniquement.
- 4 collaborateurs `WorkflowRunner` restants (QaBranchPolicy, JobRecorder,
  AgentIoAssembler, RunnerServices) → chacun aurait dû partager du mutable
  state heavy avec le runner. PauseController seul était clean.
- Décomposition des 6 vues oversized (~5000 LOC) → churn mécanique non testé
  (pas de tests unitaires renderer). Pattern établi, adoption au cas par cas.

### Version
- Bump 2.2.6 → **2.2.7** (refactor interne pur ; aucune nouvelle feature,
  aucun breaking change, 1022 tests préservés).

## v2.2.1 — Audit complet + 20 bugs corrigés (2026-07-10)

### Bug Fixes
- **"An object could not be cloned" à la création de projet** : `newProject` (Vue `ref`) passé tel quel à `ipcRenderer.invoke()` → structured clone algorithm rejette les Proxy Vue. Fix : helper `toPlain()` centralisé (`utils/toPlain.ts`) appliqué sur tous les appels IPC concernés (editor `chapter:save`, history `create-snapshot`, lexicon `find-conflicts`, plugins `set-config`, workflow `resume-batch`, export `run`, settings tolerances). HomeView `open()` a désormais un try/catch + `openError` affiché.
- **ProjectManager.create() partial-state** : si la migration ou l'insert DB échoue après création des dossiers, le dossier partiel restait sur disque et bloquait les futures créations du même nom. Fix : `try/catch` avec `fs.rmSync(projectDir)` + `db.close()` en finally.
- **export:run / export:batch DB leak** : chaque export fuyait 1-2 connexions SQLite (DB de traçage stockée sur le singleton `ExportEngine` jamais fermée) + race sur `this.db` du singleton. Fix : une seule DB, fermée en `finally` + `setDatabase(null)`.
- **WorkflowRunner DB leak** : `this.db` n'était fermé qu'en completion de `runBatch` — constructeur qui throw, early-returns (cancel/failed), et `.catch` async fuyaient. Fix : `db.close()` dans tous les chemins de sortie.
- **history:rollback incomplet** : `ParagraphRepository.updateMany` n'updatait pas `source_text` → rollback restaurait translated/status mais gardait silencieusement le source modifié. Fix : `source_text = ?` ajouté à l'UPDATE.
- **history:rollback-partial cassé sur snapshots incrémentaux** : les paragraphes reconstruits ont un ID synthétique `reconstructed-*` qui ne matche aucun UUID réel → partial rollback silencieusement vide. Fix : résolution via lookup `(chapterId, indexInChapter)`.
- **importSource orphan .md** : `fs.writeFileSync` du `.md` avant la transaction DB ; sur rollback DB, les fichiers orphelins restaient dans `source/`. Fix : suivi des fichiers écrits + suppression dans le catch.
- **refreshSource file/DB mismatch** : nouveau contenu écrit avant la transaction DB → sur rollback, fichier et DB divergeaient (hash stale). Fix : sauvegarde de l'ancien contenu + restauration dans le catch (branches merge et replace).
- **WorkflowEngine race runner** : `runners.set` après le retour de `startBatch` → fenêtre où pause/cancel/retry échouaient silencieusement. Fix : `set` immédiat après création. `resumeBatch` supprime l'ancien runner (delete + cancel best-effort) avant d'en créer un nouveau (évite double runner + fuite DB).
- **history:diff "Snapshot introuvable" erroné** : un snapshot existant peut légitimement avoir 0 paragraphes (chapitre vide au moment du snapshot). Fix : `getById()` séparé pour vérifier l'existence.
- **resolveProjectPath DB leak** : `getById` dans `.find()` sans try/finally → fuite si la DB est corrompue. Fix : try/finally.
- **lexicon:import JSON.parse** : `SyntaxError` brute propagée au renderer. Fix : try/catch avec message lisible.
- **HMR double-register IPC handlers** : `ipcMain.handle` lance si appelé deux fois (HMR dev). Fix : monkey-patch dans `router.ts` qui fait `removeHandler` avant chaque registration → idempotent.
- **promoteToGlobal NOT NULL violation** : code dormant insérait `project_id = NULL` mais le schéma déclarait NOT NULL. Fix : migration 016 qui recrée `translation_memory` avec `project_id` nullable + FK `ON DELETE SET NULL`.
- **OllamaProvider 429 structure** : commentaire documentant que `handle429: Promise<never>` (le 429 ne doit jamais tomber dans la branche 4xx).
- **RagEngine embeddings fragility** : warning loggé sur mismatch de longueur avant fallback per-text (diagnostic Ollama tronqué).

### Version
- Bump 2.2.0 → **2.2.1** (audit complet du main process + renderer IPC, 20 bugs identifiés et corrigés, aucun breaking change).

## v2.2.0 — Corrections mise à jour auto + release 2.2.0 (2026-07-09)

### Bug Fixes (auto-update)
- **Double instance UpdateManager éliminée** : le main créait une instance pour le check auto au démarrage, et les handlers IPC en créaient une seconde → chaque event autoUpdater (update-available, update-downloaded) était émis en double et ouvrait des dialogues natifs en double. Désormais une instance unique partagée via `setUpdateManager()`.
- **HomeView "Vérifier mise à jour" donne enfin un retour** : le `setTimeout(3s)` qui arrêtait le spinner prématurément est supprimé ; le store écoute désormais `update:not-available` et `update:checking` → l'utilisateur voit clairement "NovelTrad est à jour" ou "Vérification…" ou le détail d'une erreur.
- **SettingsView "Vérifier maintenant" fonctionnel** : bouton désactivé pendant le check, message "Recherche en cours…", puis retour "à jour" / "nouvelle version" / "erreur".
- **Store update enregistré au démarrage** : `App.vue` instancie `useUpdateStore()` au mount (pas seulement à la navigation vers Settings) → l'événement `update:available` du check auto (5s après démarrage) n'est plus manqué.

### Version
- Bump 2.1.3 → **2.2.0** (les entrées CHANGELOG 2.1.4 et 2.1.5 n'avaient pas été accompagnées d'un bump de version ; cette release les englobe).

## v2.1.5 — Boucle de révision pro + Summarizer + câblage plugin (2026-07-08)

### Features (v1.4 — traduction pro révisée)
- **Boucle Review→Revise** : 2 nouveaux stages (`review`, `revise`) insérés avant QA. Le `ReviewAgent` produit un rapport de corrections ciblées paragraphe-par-paragraphe (`ReviewReport`), le `ReviseAgent` les applique via réécriture LLM. C'est ce qui transforme une "traduction retry-boucle" en "traduction révisée comme par un humain". Pipeline désormais 12 passes. Inspiration : honya (Reviewer), LaTeXTrans (Validator).
- **Summarizer transverse** : agent hors-pipeline appelé après l'export d'un chapitre. Maintient un `NovelSummary` incrémental injecté dans le contexte de `translate`/`style`/`polish`/`review` des chapitres suivants → cohérence des noms et de l'intrigue sur 500+ chapitres. Inspiration : LaTeXTrans (Summarizer), TransAgents.
- **Câblage PluginHost → WorkflowEngine** : `getPluginAgent` et `setPluginProviderResolver` désormais réellement alimentés. Un plugin peut remplacer n'importe quel agent built-in ou fournir un provider IA. (Avant : le hook existait mais n'était jamais câblé → plugins d'agents inertes.)
- **Toggles mode pro** : `reviewLoopEnabled` et `summarizerEnabled` dans les Settings (défaut `true`). Mode rapide = pipeline 10 passes original.
- **UI ReviewReport** : affichage des corrections (sévérité, catégorie, suggestion, raison) dans le panneau de détail du workflow.

### Bug Fixes (doc SDD)
- **Coquilles caractères ESC** : `25-Prompt-Book.md` §25.6 avait des caractères ESC (0x1b) qui mangeaient la première lettre de `export`, `translate`, `target_model`, `text`, `failed`. Corrigé.
- **`06-Database.md`** : entériné `node-sqlite3-wasm` (WONTFIX migration better-sqlite3) + table `history_snapshots` (au lieu de `history`).
- **Commentaire worker threads** : note obsolète "Non implémenté MVP" corrigée (workers activés par défaut `true`, bug T14 résolu).

### Infrastructure
- Migrations `014_review_stage.sql` (table `review_reports` + registre agents), `015_summaries.sql` (`chapter_summaries`, `novel_summaries`).
- Types `ReviewReport`/`ReviewIssue`/`ChapterSummary`/`NovelSummary` + schémas Zod (`reviewOutputSchema`, `reviseOutputSchema`, `summarizerOutputSchema`).
- 981 tests (71 suites), 0 failed, 0 type-check error, 0 lint error.

## v2.1.4 — Post-T1-T15 gap fixes (2026-07-06)

Cycle correctif suite à la revue indépendante des 15 tâches T1-T15. 12 commits atomiques sur branche `fix/post-t1-t15-gaps`. 940 tests (62 suites), 0 failed, 0 type-check error.

### Bug Fixes (runtime critiques)
- **T3 — Double p-retry éliminé** : `AiRouter.chat()` ET `OllamaProvider.chat()` wrappaient chacun dans `pRetry(retries:3)` → jusqu'à 16 tentatives sur erreur 5xx. Retry centralisé au niveau AiRouter uniquement (4 tentatives max). (`68b3b19`)
- **T9 — EPUB multi-chapitre lang** : `toEpubMultiChapter()` hardcodait `lang:"fr"`, ignorant la targetLanguage du projet. Désormais propagée via `options.targetLanguage` depuis la DB projet. (`38174ab`)
- **T14 — Worker threads path** : `agent-worker.ts` importait `../agents/${agentId}.js` avec stage lowercase, mais les fichiers sont PascalCase → tous les imports worker échouaient (fallback silencieux systématique). Registre explicite `AGENT_MODULES` (10 entrées PascalCase). Workers désormais fonctionnels. (`a2bd1fa`)

### Features (wiring dead code)
- **T5 — PromptLoader câblé** : la classe existait mais n'était jamais instanciée, et queryait une colonne `active` inexistante. Migration `012_prompts_active.sql` + `AiRouter.resolvePrompt()` + `TranslateAgent` l'utilise. Override DB des prompts fonctionnel. (`dedf82b`)
- **T11 — findBestMatch 5 tiers actif** : la cascade SDD §9.4 (project-exact → project-fuzzy → global-exact → global-fuzzy) était implémentée mais jamais appelée. `TranslateAgent.buildMemoryBlock()` l'utilise désormais. (`7fb56ee`)
- **T13 — RAG optimisé** : batch embeddings par chapitre (O(N)→O(1) appels Ollama), `reindex()` async recalcule réellement (avant: DELETE seulement), cache MiniSearch par projet (avant: reconstruit à chaque requête). Dépendance `sqlite-vec` supprimée (POC KO, SDD §9.3 ne la requiert pas). (`cb841a5`)

### Bug Fixes (dégradations)
- **T8 — Quality scoring honnête** : hallucination fallback `95` trompeur → `0` quand le détecteur échoue. `QaAgent` fallback transmet désormais le `ConsistencyReport` du stage précédent (avant: dimension consistency toujours `90`). (`3ab178b`)
- **T12 — TM fuzzy CJK** : le préfiltre `/\b\w{3,}\b/` ne matchait pas le CJK (zh/ja/ko) → dégradation vers fallback. Remplacé par `/[\p{L}]{2,}/gu` (Unicode). (`84a9809`)

### Bug Fixes (cleanup)
- **T4A — Jobs single abandonnés** : `resumeActiveJobs()` ne reprenait que les batch ; les single restaient bloqués en `running`. Désormais marqués `failed` proprement. (`7eedf07`)
- **T4B — Transactions migrations** : le runner wrappait systématiquement dans `BEGIN/COMMIT` → cassait si la migration contenait sa propre transaction. Détection `hasOwnTransaction` + wrapper conditionnel. (`a263779`)

### Excluded (décision produit définitive)
- **T15 — Signature code** : 🚫 WONTFIX. La signature de code ne sera jamais activée. Config CSC/Apple retirée de `electron-builder.yml` et `release.yml` ; `docs/SIGNING.md` supprimé. Les builds sont délibérément non signés (Windows SmartScreen avertira au premier lancement — c'est un choix assumé, pas un manque).

## v2.1.1 — Security + Performance + Accessibility (2026-07-05)

### Security
- **IPC channel validation in preload**: Added `IPC_CHANNELS` allowlist with `validateChannel()` — blocks unauthorized channels from renderer process, hardening `contextIsolation`
- **Preload event cleanup**: Changed `removeAllListeners` → `removeListener` for targeted, safe event removal

### Performance
- **SQLite transactions**: Wrapped `ParagraphRepository.createMany/updateMany` and `LexiconRepository.syncAliases` in explicit `BEGIN/COMMIT` transactions — eliminates N+1 auto-commit bottleneck on bulk DB writes

### Accessibility
- **NtTable**: Added `tabindex`, `keydown.enter/space` on sortable headers and rows with `:focus-visible` outlines
- **HomeView**: Added `role="button"`, `tabindex`, `keydown.enter/space` on project list items
- **LexiconForm**: Added `aria-label` + `disabled` state on remove (✕) buttons with not-allowed cursor when minimum items reached

### Tooling
- **ESLint**: 0 errors, 0 warnings (config created with TypeScript parser + Vue 3 support)
- **14 duplicate auto-PRs closed**, stale branches deleted
- **HomeView version**: 2.0.4 → 2.1.1

## v2.1.0 — Stabilization Release (2026-07-05)

### Bug Fixes

- **Ollama connection fix**: Migrated all HTTP calls from `globalThis.fetch()` to Electron's `net.fetch()` — resolves silent connection failures on desktop builds
- **RagEngine**: Migrated 2 remaining bare `fetch()` calls to `net.fetch()` with `AbortSignal.timeout()`
- **Production chunk loading**: Added `node_modules/**/*` to `electron-builder.yml` files list — fixes all 12 dynamic chunks failing silently
- **Menu system**: Added `project:open-dialog` IPC handler, all menu clicks use `getMainWindow()` with `isDestroyed()` checks
- **Log forwarding**: Uses `getMainWindow()` instead of closure for surviving window recreation
- **Settings fallback**: Added `DEFAULT_SETTINGS` in stores/settings.ts
- **Wizard**: Suivant button `:disabled="!canProceed"`, `finish()` wrapped in try/catch
- **App.vue**: `project:open-dialog` navigates to opened project

### Security

- **Path traversal**: Added `assertWithinProject()` to `project:open` handler
- **Logging**: Replaced raw `console.warn` with structured `logger.warn` in ProjectManager (NDJSON, redaction, correlation IDs)
- **Debug log dedup**: Removed 3 duplicate `debugLog()` functions, replaced with `logger.debug()` — eliminates `fs.appendFileSync` race conditions

### Testing

- **782 tests, 0 failures** (up from 737 baseline in v2.0.7)
- **+45 new tests** across 6 new/modified test files:
  - `ollama-manager.spec.ts`: expanded to 20 tests (timeout, HTTP 500, invalid JSON)
  - `providers.spec.ts`: expanded to 24 OllamaProvider tests
  - `rag-engine.spec.ts`: rewritten with `vi.mock("electron")` pattern
  - `ollama-ipc.spec.ts`: new 20 IPC integration tests
  - `non-regression.spec.ts`: new 8 router smoke tests
  - `ollama.spec.ts`: new 5 E2E scenarios
- **Per-file coverage targets met**:
  - OllamaManager.ts: 100% (target ≥90%)
  - OllamaProvider.ts: 98.98% (target ≥90%)
  - handlers/ollama.ts: 100% (target ≥85%)

### Architecture

- **`net.fetch()`**: All main-process HTTP uses Electron's `net.fetch()` (Chrome network stack) — no `node:http` fallback
- **Zod validation**: All IPC handlers validated with Zod schemas
- **Plugin system**: Complete (Volume 15 SDD) — PluginHost, PluginContext, PluginsView, hot-reload, example plugin
- **Structured logging**: NDJSON format, sensitive data redaction, correlation IDs

### Documentation

- `docs/PHASE0_VALIDATION_REPORT.md`: Ollama fix validation results
- `docs/STABILIZATION_AUDIT.md`: Phase 1 code audit findings

---

## v2.0.7 (2026-07-05)

- Repair broken index.ts (regex mangled try/catch)
- Isolated IPC loader

## v2.0.6 (2026-07-05)

- Native menu Help + Ollama default host
- Try/catch IPC router
- HelpView

## v2.0.5 (2026-07-05)

- Update check 5s + banner MAJ visible on Accueil
- Lazy gpt-tokenizer + HelpView

## v2.0.4 (2026-07-05)

- gpt-tokenizer lazy import (fix crash prod)
- HelpView + sidebar Aide

## v2.0.3 (2026-07-05)

- gpt-tokenizer version fix + build fix
- Consistency: replace custom countSentences with sbd
- RAG: replace custom cosineSimilarity with compute-cosine-similarity

# Changelog

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

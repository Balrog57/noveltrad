# Workflow State — NovelTrad 2.0

## Request
Continuer le développement de NovelTrad 2.0 par rapport au SDD (`docs/`). Audit complet des 26 volumes SDD, implémentation des écarts restants avec todo claire et retour visuel (PROGRESS.md).

## Clarified Scope
- **Audit SDD complet** : 9 phases d'écarts identifiées (A à I), toutes implémentées ✅
- **Ordre révisé** : C → A → B → D → F → E → H → G → I
- **Réutilisation maximale** : code, librairies, patterns existants — rien inventé
- **Modèle sous-agents** : `deepseek/deepseek-v4-flash` configuré (fichiers `~/.config/opencode/agents/*.md`)
- **Retour visuel** : `PROGRESS.md` (checkboxes)

## Open Questions
1. `opencode.json` non modifié (permissions) — sous-agents configurés via fichiers `.md`. À valider.
2. PROGRESS.md créé via PowerShell à la racine du repo.
3. Push GitHub : à faire après validation finale.

## Constraints
- Suivre le SDD à la lettre (tous les volumes)
- Réutiliser au maximum le code existant + patterns des projets d'inspiration
- Pas de Tailwind CSS — tokens CSS (`tokens.css`)
- Zod obligatoire pour tous les nouveaux payloads IPC
- UI et code en français
- `npm run type-check` et `npm run test` passent après chaque modif
- Commits atomiques sur `main`

## Plan (Phases A→I)

### Ordre d'implémentation : C → A → B → D → F → E → H → G → I

| Phase | SDD | Description | Statut |
|-------|-----|-------------|--------|
| C | §9.7 | TMX test | ✅ |
| A | §4.13, §23.3 | 6 composants UI (NtButton, NtInput, NtSelect, NtTextarea, NtCard, NtLogViewer) | ✅ |
| B | §7.9, §13.6 | Batch processing (sélection multiple, maxConcurrentJobs, reprise crash, export lots) | ✅ |
| D | §12.5, §12.6, §11.4 | Qualité avancée (calibration, hallucination, tolérances) | ✅ |
| F | §5.8, §5.10, §5.11 | Projets avancés (refreshSource, detectDuplicate, suppression) | ✅ |
| E | §14.3, §14.5, §14.6 | Historique avancé (snapshots hybrides, zlib, rollback partiel, audit) | ✅ |
| H | §10.9, §10.10 | Lexique avancé (findConflicts, suggestTranslation IA) | ✅ |
| G | §22.2, §22.6 | Performance (profiler métriques, export CSV) | ✅ |
| I | §17, §20 | CI (generate-latest-json, upload release) | ✅ |

## Debate Notes

### Verdict : revise before implementation
- **Phase C (TMX)** déjà à 95% — seul test manquait → quick win en premier
- **Phase B (Batch)** partiellement existante — 4 ajouts ciblés au lieu de tout recréer
- **Phase F (Projets)** `delete()` existe déjà — ne pas recréer
- **Ordre révisé** : C→A→B→D→F→E→H→G→I (C quick win d'abord)
- **Version initiale** du plan surestimait le travail pour C, B, F

## Files To Change (résumé global)

### Nouveaux fichiers (~25)
```
apps/desktop/src/renderer/src/components/ui/NtButton.vue
apps/desktop/src/renderer/src/components/ui/NtInput.vue
apps/desktop/src/renderer/src/components/ui/NtSelect.vue
apps/desktop/src/renderer/src/components/ui/NtTextarea.vue
apps/desktop/src/renderer/src/components/ui/NtCard.vue
apps/desktop/src/renderer/src/components/ui/NtLogViewer.vue
apps/desktop/src/main/services/CalibrationService.ts
apps/desktop/src/main/services/HallucinationDetector.ts
apps/desktop/src/main/services/AuditService.ts
apps/desktop/src/main/services/PerformanceProfiler.ts
apps/desktop/src/main/db/migrations/006_batch_state.sql
apps/desktop/src/main/db/migrations/007_quality.sql
apps/desktop/src/main/db/migrations/008_audit.sql
apps/desktop/src/main/db/migrations/009_chapter_metadata.sql
scripts/generate-latest-json.ts
apps/desktop/tests/unit/tmx.spec.ts
apps/desktop/tests/unit/ui-components.spec.ts
apps/desktop/tests/unit/batch.spec.ts
apps/desktop/tests/unit/quality-advanced.spec.ts
apps/desktop/tests/unit/project-advanced.spec.ts
apps/desktop/tests/unit/audit.spec.ts
apps/desktop/tests/unit/lexicon-advanced.spec.ts
apps/desktop/tests/unit/performance.spec.ts
apps/desktop/tests/unit/latest-json.spec.ts
```

### Fichiers modifiés (~25)
```
apps/desktop/src/main/managers/WorkflowEngine.ts
apps/desktop/src/main/managers/ProjectManager.ts
apps/desktop/src/main/services/ExportEngine.ts
apps/desktop/src/main/services/ConsistencyChecker.ts
apps/desktop/src/main/services/LexiconEngine.ts
apps/desktop/src/main/services/agents/QaAgent.ts
apps/desktop/src/main/services/agents/AgentFactory.ts
apps/desktop/src/main/services/agents/ConsistencyAgent.ts
apps/desktop/src/main/db/repositories/HistoryRepository.ts
apps/desktop/src/main/db/repositories/JobRepository.ts
apps/desktop/src/main/db/connection.ts
apps/desktop/src/main/ipc/channels.ts
apps/desktop/src/main/ipc/handlers/lexicon.ts
apps/desktop/src/main/ipc/handlers/history.ts
apps/desktop/src/main/ipc/handlers/project.ts
apps/desktop/src/main/ipc/handlers/export.ts
apps/desktop/src/main/ipc/handlers/workflow.ts
apps/desktop/src/main/managers/SettingsManager.ts
apps/desktop/src/renderer/src/views/ChaptersView.vue
apps/desktop/src/renderer/src/views/HomeView.vue
apps/desktop/src/renderer/src/views/SettingsView.vue
apps/desktop/src/renderer/src/views/LexiconView.vue
apps/desktop/src/renderer/src/views/HistoryView.vue
apps/desktop/src/renderer/src/stores/workflow.ts
apps/desktop/src/renderer/src/stores/lexicon.ts
apps/desktop/src/renderer/src/stores/history.ts
apps/desktop/src/renderer/src/components/export/ExportDialog.vue
packages/shared/src/types/index.ts
packages/shared/src/schemas/export.ts
packages/shared/src/schemas/lexicon.ts
packages/shared/src/schemas/history.ts
.github/workflows/release.yml
```

## Implementation Notes (par phase)

### Phase C — TMX test (SDD §9.7)
- Créé : `tmx.spec.ts` (15 tests) — importTmx, exportTmx, round-trip, schémas Zod
- TMX était déjà implémenté à 95% (TranslationMemoryEngine, handlers, schémas, boutons UI)
- Mock DB SQLite en mémoire, pattern cohérent avec autres tests

### Phase A — Composants UI (SDD §4.13, §23.3)
- Créés : NtButton, NtInput, NtSelect, NtTextarea, NtCard, NtLogViewer (6 composants)
- 31 tests, CSS tokens uniquement, UI en français, accessibilité (aria-*)
- Aucune vue modifiée (ajout pur design system)

### Phase B — Batch processing (SDD §7.9, §13.6)
- 4 ajouts ciblés : sélection multiple checkboxes, maxConcurrentJobs (défaut 1), reprise crash (migration 006), export lots EPUB agrégé
- 24 tests dont 7 non-régression (pause/resume/cancel préservés)
- Code existant intact (startBatch/runBatch étendus, pas écrasés)

### Phase D — Qualité avancée (SDD §12.5, §12.6, §11.4)
- CalibrationService : régression linéaire moindres carrés, bornes [0,100]
- HallucinationDetector : entités nommées source vs cible (CJK + Latin)
- ConsistencyChecker : 6 paires de langues, tolérances configurables
- QAAgent : calibration appliquée avant globalScore
- SettingsView : section Workflow (seuil qualité + tolérances)
- 38 tests, migration 007 (model_calibrations)

### Phase F — Projets avancée (SDD §5.8, §5.10, §5.11)
- `refreshSource()` : SHA256 + 3 stratégies (Remplacer/Fusionner/Nouvelle version)
- `detectDuplicate()` : titre + SHA256 (hash original stocké dans metadata)
- Suppression projet HomeView : clic droit → confirmation → 2 modes
- v2 : corrigé C1 (hash mismatch multi-chapitres) + C2 (hash mismatch formats binaires)
- 17 tests, migration 009 (chapter metadata)

### Phase E — Historique avancé (SDD §14.3, §14.5, §14.6)
- Snapshots hybrides : complet (v1/v5/v10) + incrémental (diff-based)
- Compression zlib si > 10 Ko
- Rollback partiel : restaurer paragraphes sélectionnés (checkboxes UI)
- Journal d'audit : AuditService + table audit_log + actions tracées
- v2 : corrigé C1 (snapshot liste complète vs sélection)
- 45 tests (29 history + 16 audit), migration 008

### Phase H — Lexique avancé (SDD §10.9, §10.10)
- `findConflicts()` : duplicate_term + overlap, O(n²), normalizeTerm()
- `suggestTranslation()` : IA via AiRouter, prompt JSON strict, fallback
- UI : panneau conflits intégré + modal suggestion IA
- 14 tests

### Phase G — Performance (SDD §22.2, §22.6)
- PerformanceProfiler : collecte métriques (durationMs, tokensIn, tokensOut) par job/step
- Export CSV avec échappement
- Intégré dans WorkflowEngine.runStep() (succès + échec)
- Worker threads stub documenté (non implémenté)
- 14 tests

### Phase I — CI (SDD §17, §20)
- `scripts/generate-latest-json.ts` : CLI (--version, --installer, --output, --channel)
- Calcul SHA256, construit URLs download/release_notes
- `.github/workflows/release.yml` : étape génération + upload latest.json
- 9 tests

## Review Findings

| Phase | Verdict | CRITICAL | HIGH | MEDIUM | LOW |
|-------|---------|----------|------|--------|-----|
| C (TMX) | ✅ Approved | 0 | 0 | 1 | 5 |
| A (UI) | ✅ Approved | 0 | 0 | 3 | 6 |
| B (Batch) | ✅ Approved | 0 | 0 | 4 | 6 |
| D (Qualité) | ✅ Approved | 0 | 0 | 1 | 7 |
| F (Projets) | ❌ Rejected v1 → ✅ Approved v2 | 0 | 0 | 1 | 3 |
| E (Historique) | ❌ Rejected v1 → ✅ Approved v2 | 0 | 2 | 4 | 4 |
| H (Lexique) | ✅ Approved | 0 | 0 | 1 | 3 |
| G (Performance) | ✅ Approved | 0 | 0 | 0 | 3 |
| I (CI) | ✅ Approved | 0 | 0 | 1 | 3 |

### Corrections critiques appliquées :
- **F-C1** : `refreshSource()` hash mismatch multi-chapitres → stocke originalFileHash dans metadata
- **F-C2** : `detectDuplicate()` hash mismatch formats binaires → utilise metadata.originalFileHash
- **E-C1** : snapshot rollback partiel liste incomplète → utilise allParagraphs après restauration

### Review Findings — Phase I (CI latest.json)

**Verdict:** ✅ Approved

**Ce qui est BON :**
- `scripts/generate-latest-json.ts` : SHA256 correct (`node:crypto.createHash('sha256')`), CLI arguments complets (--version, --installer, --output, --channel, --owner, --repo), URLs GitHub correctement construites, export JSON pretty-printed
- `.github/workflows/release.yml` : détection de channel automatique (tag v* → stable/beta/alpha), génération latest.json après build, upload via `gh release upload` avec `--clobber`, fallback gracieux si installer introuvable, artifact upload de secours
- `electron-builder.yml` : `output: dist` aligné avec le glob `dist/*.exe` dans le workflow, artifactName pattern correct
- `latest-json.spec.ts` : 9 tests couvrant SHA256 (correction + différentiation), channel par défaut/personnalisé, URLs custom owner/repo, erreur fichier inexistant, date ISO valide
- Alias `@scripts` configuré dans `tsconfig.json` ET `vitest.config.ts` → résolution correcte
- Tests passent (9/9), type-check OK

**Problèmes identifiés :**
- MEDIUM — `--channel` non validé à l'exécution (cast TypeScript `as "stable" | "beta" | "alpha"` ligne 107). Si `--channel foo` passé, le manifeste contiendrait `"channel": "foo"`. Ajouter une validation runtime (`if (!['stable','beta','alpha'].includes(channel)) throw`) recommandée mais pas bloquant (CLI usage interne CI)

### Review Findings — Phase F v2 (Projets corrigée)

**Verdict:** ✅ Approved

**Ce qui est BON — F-C1 `refreshSource()` :**
- Stocke `originalFileHash` (hash binaire du fichier original complet) dans `chapter.metadata` lors de l'import (ligne 604)
- Compare systématiquement le hash binaire actuel du fichier original contre `originalFileHash` stocké (lignes 235-247)
- Met à jour `originalFileHash` après chaque `refreshSource` réussi (lignes 360-361, 417-418)
- Également met à jour `sourceHash` (hash du .md normalisé) pour les vérifications futures
- Migration 009 présente en inline dans `connection.ts` (lignes 358-361) : `ALTER TABLE chapters ADD COLUMN metadata TEXT`

**Ce qui est BON — F-C2 `detectDuplicate()` :**
- Compare le hash binaire du fichier à importer contre `metadata.originalFileHash` stocké (lignes 489-502)
- Fonctionne pour TOUS les formats (TXT/MD/DOCX/EPUB) car la comparaison est binaire
- Fallback gracieux : si metadata manquant ou JSON invalide, ignore la comparaison par hash (lignes 499-501)
- Détection par titre ET/OU hash, retourne le type précis (`title` | `sha256` | `both`)

**Ce qui est BON — H2 HomeView suppression :**
- `deleteError` affiché dans le template (ligne 142 : `v-if="deleteError" class="error-msg"`)
- Erreur catchée dans `confirmDelete()` et affichée dans le dialogue modal (lignes 65-67)
- Bouton Annuler visible en permanence → l'utilisateur peut toujours revenir en arrière

**Tests Phase F v2 :**
- 17 tests au total (project-advanced.spec.ts) : 5 refreshSource (inchangé, replace, merge, not-found, default strategy) + 4 detectDuplicate (title+hash, hash only, différent, not-found) + 3 suppression projet + 5 validation Zod
- DB mockée pour éviter `node-sqlite3-wasm` → tests unitaires valides, nécessitent des tests d'intégration séparés pour la migration 009

**Problèmes identifiés :**
- MEDIUM — Stratégie `new-version` dans `refreshSource()` appelle `this.importSource()` qui crée TOUS les chapitres du fichier, mais ne retourne que `newChapters[0]`. Les autres chapitres créés restent orphelins pour l'appelant. Comportement intentionnel selon SDD §5.8 mais peut surprendre. Documenter dans les commentaires de code serait bien.

## Test Results

| Commande | Résultat |
|----------|----------|
| `npm run type-check --workspace=apps/desktop` | ✅ 0 erreur |
| `npm run test` | ✅ **336/336 passent** (21 suites, 0 régression) |

### Suites de tests (21)
| Suite | Tests |
|-------|-------|
| engines | 4 |
| editor | 13 |
| lexicon | 16 |
| export-dialog | 12 |
| history | 29 |
| prompts | 37 |
| workflow-view | 11 |
| import | 18 |
| project-stats | 7 |
| nt-tooltip | 4 |
| nt-empty-state | 5 |
| nt-badge | 5 |
| ui-components | 31 |
| tmx | 15 |
| batch | 24 |
| quality-advanced | 38 |
| project-advanced | 17 |
| audit | 13 |
| lexicon-advanced | 14 |
| performance | 14 |
| latest-json | 9 |
| **Total** | **336** |

## Security Findings
Toutes les phases ont passé la security review sans vulnérabilité CRITICAL ou HIGH.
- Zod validation sur tous les handlers IPC
- SQL paramétré 100%
- Zéro v-html, CSS tokens uniquement
- Sandbox Electron activé (sandbox:true, contextIsolation:true)
- Path traversal protégé (assertWithinProject)

## Lint Results
- Prettier : tous les fichiers conformes (auto-fix appliqué)
- ESLint : non configuré (pattern pré-existant)
- TypeScript : vue-tsc --noEmit 0 erreur

## Commit Message Draft
```
feat(sdd): audit SDD complet — 9 phases d'écarts (A-I), 336 tests, type-check OK

- C: test TMX (15 tests round-trip, import/export, schémas Zod)
- A: 6 composants UI design system (NtButton, NtInput, NtSelect, NtTextarea, NtCard, NtLogViewer)
- B: batch processing avancé (sélection multiple, maxConcurrentJobs, reprise crash, export lots agrégé)
- D: qualité avancée (calibration régression linéaire, détection hallucination, tolérances par langue)
- F: projets avancés (refreshSource 3 stratégies, detectDuplicate titre+hash, suppression HomeView)
- E: historique avancé (snapshots hybrides, compression zlib, rollback partiel par paragraphe, journal d'audit)
- H: lexique avancé (findConflicts O(n²), suggestTranslation IA avec fallback)
- G: performance (profiler métriques duration/tokens, export CSV échappé)
- I: CI (generate-latest-json SHA256, upload release latest.json)
- 336 tests (21 suites) ✅ — 0 régression, 0 erreur vue-tsc
```

## Current Status
- Phase 1-40 (Items 1-8 + SDD compliance) : ✅
- Phase 41 (Planner - Audit SDD) : ✅
- Phase 42 (Debater - Plan révisé) : ✅
- Phase 43 (Implementor - Phase C TMX) : ✅
- Phase 44 (Reviewer - Phase C) : ✅
- Phase 45 (Implementor - Phase A UI) : ✅
- Phase 46 (Reviewer - Phase A) : ✅
- Phase 47 (Implementor - Phase B Batch) : ✅
- Phase 48 (Reviewer - Phase B) : ✅
- Phase 49 (Implementor - Phase D Qualité) : ✅
- Phase 50 (Reviewer - Phase D) : ✅
- Phase 51 (Implementor - Phase F Projets v1) : ✅
- Phase 52 (Reviewer - Phase F v1) : ❌ Rejected
- Phase 53 (Implementor - Phase F v2 fix) : ✅
- Phase 54 (Implementor - Phase E Historique v1) : ✅
- Phase 55 (Reviewer - Phase E v1) : ❌ Rejected
- Phase 56 (Implementor - Phase E v2 fix) : ✅
- Phase 57 (Reviewer - Phase E v2) : ✅
- Phase 58 (Implementor - Phase H Lexique) : ✅
- Phase 59 (Reviewer - Phase H) : ✅
- Phase 60 (Implementor - Phase G Perf) : ✅
- Phase 61 (Reviewer - Phase G) : ✅
- Phase 62 (Implementor - Phase I CI) : ✅
- Phase 63 (Reviewer - Phase I + Phase F v2) : ✅

## Next Agent
implementor

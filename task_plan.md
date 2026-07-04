# Phase 0 — Validation automatisée du fix Ollama

## Goal
Valider automatiquement que le correctif Ollama (`net.fetch()`) fonctionne dans toutes les situations et qu'aucune régression n'est introduite. La Phase 0 n'est considérée comme terminée que si TOUTES les étapes passent sans erreur.

## Constraints
- 737 tests existants ne doivent pas être cassés
- Pas de nouvelles dépendances npm
- `net.fetch()` est toujours disponible dans Electron 31+ (pas de fallback)
- Chaque commit doit laisser l'app dans un état fonctionnel
- Tests unitaires : Vitest (déjà configuré)
- Tests E2E : Playwright (déjà configuré dans `playwright.config.ts`)
- `pnpm verify` commande unique de validation

## Plan

### Phase 1: Tests unitaires OllamaManager (expansion)
**Status**: `pending`
**File**: `apps/desktop/tests/unit/ollama-manager.spec.ts`
**Objectif**: 90% couverture OllamaManager

Tests à ajouter aux 11 existants :
1. ✅ Ollama disponible (existe)
2. ✅ Ollama indisponible (existe)
3. ✅ Erreur réseau (existe)
4. **Timeout réseau** — simuler AbortSignal.timeout avec AbortError
5. **Erreur HTTP** — mockJsonResponse avec status 4xx/5xx + res.ok=false
6. **JSON invalide** — isAvailable retourne false si JSON.parse échoue
7. **Réponse vide** — listModels retourne [] si models absent
8. **Streaming de réponse** — pullModel avec chunks NDJSON multi-lignes (existe partiellement)
9. **Liste des modèles** — détails parameter_size/quantization (existe)
10. **Test de connexion** — testModel retourne contenu (existe)
11. **testModel erreur HTTP** — 404 ou 500
12. **testModel réponse vide** — message.content undefined
13. **pullModel sans body** — reader null
14. **listModels HTTP error** — 500

### Phase 2: Tests unitaires OllamaProvider (expansion)
**Status**: `pending`
**File**: `apps/desktop/tests/unit/providers.spec.ts`
**Objectif**: 90% couverture OllamaProvider

Tests à ajouter aux 8 existants :
1. **Timeout réseau** — AbortError sur listModels
2. **Erreur HTTP** — 500 sur chat
3. **JSON invalide** — chat retourne error
4. **Réponse vide** — embeddings retourne [] si embedding absent
5. **Streaming multi-chunks** — 3+ chunks NDJSON
6. **streamChat erreur HTTP** — 500
7. **streamChat reader null** — pas de body
8. **embeddings erreur HTTP** — 500
9. **embeddings tableau vide** — []
10. **chat message.content undefined** — retourne ""

### Phase 3: Tests d'intégration IPC Ollama
**Status**: `pending`
**File**: `apps/desktop/tests/unit/ollama-ipc.spec.ts` (nouveau)
**Objectif**: 85% couverture handlers IPC Ollama

Tests :
1. **ollama:is-available** — réponse correcte (true/false)
2. **ollama:is-available** — propagation erreur
3. **ollama:is-available** — logs produits (console.log appelé)
4. **ollama:list-models** — réponse correcte
5. **ollama:list-models** — propagation erreur
6. **ollama:pull-model** — download + onProgress
7. **ollama:pull-model** — erreur propagation
8. **ollama:test-model** — succès → { success: true, response }
9. **ollama:test-model** — échec → { success: false, error }
10. **Validation Zod** — host invalide, modelName vide
11. **Absence d'exception non capturée**

### Phase 4: Vérification aucun fetch() natif dans Main Process
**Status**: `pending`
**Action**: Grep `src/main/` pour `fetch(` et `globalThis.fetch`
**Objectif**: 0 occurrence de fetch natif

### Phase 5: Tests E2E Ollama (Playwright)
**Status**: `pending`
**File**: `apps/desktop/tests/e2e/ollama.spec.ts` (nouveau)
**Objectif**: 5 scénarios

Cas 1: HomeView badge "Ollama disponible" si Ollama actif
Cas 2: HomeView badge "Non disponible" si Ollama arrêté (skip si pas de serveur)
Cas 3: Wizard détection auto + affichage modèles
Cas 4: Téléchargement modèle avec progression
Cas 5: Test modèle retour OK

**Note**: Les tests E2E nécessitent une instance Electron lancée + un serveur Ollama réel. Certains tests seront skippés si Ollama n'est pas disponible.

### Phase 6: Tests de non-régression
**Status**: `pending`
**File**: `apps/desktop/tests/unit/non-regression.spec.ts` (nouveau)
**Objectif**: Garantir que les fix précédents fonctionnent

Tests :
1. **Ouverture projet** — project:open existe et retourne un projet
2. **Création projet** — project:create fonctionne
3. **Menu Electron** — ipcMain.handle enregistré pour project:open-dialog
4. **Settings** — DEFAULT_SETTINGS fallback si IPC échoue
5. **Console** — setupLogForwarding utilise getMainWindow()
6. **Auto-update** — update:check handler existe
7. **Logs** — debug.log écrit dans APPDATA

### Phase 7: Couverture ciblée
**Status**: `pending`
**Objectif**: 90% OllamaManager, 90% OllamaProvider, 85% IPC handlers

Mesurer couverture avec `vitest run --coverage` et vérifier :
- OllamaManager ≥ 90%
- OllamaProvider ≥ 90%
- handlers/ollama.ts ≥ 85%
Si pas atteint, ajouter les tests manquants.

### Phase 8: Commande pnpm verify
**Status**: `pending`
**File**: `apps/desktop/package.json` (script verify)

Script qui exécute dans l'ordre :
1. `pnpm lint` — ESLint
2. `pnpm type-check` — vue-tsc
3. `pnpm test` — Vitest unit tests
4. `pnpm test:e2e` — Playwright E2E
5. `pnpm build` — electron-vite + electron-builder

Si une étape échoue, le script s'arrête.

### Phase 9: Rapport de validation finale
**Status**: `pending`
**File**: `docs/PHASE0_VALIDATION_REPORT.md`

Contenu :
- Nombre de tests exécutés
- Couverture obtenue (par fichier)
- Zones non couvertes
- Risques résiduels
- Recommandations avant Phase 0.1

## Files To Change
- `apps/desktop/tests/unit/ollama-manager.spec.ts` — expand
- `apps/desktop/tests/unit/providers.spec.ts` — expand
- `apps/desktop/tests/unit/ollama-ipc.spec.ts` — new
- `apps/desktop/tests/e2e/ollama.spec.ts` — new
- `apps/desktop/tests/unit/non-regression.spec.ts` — new
- `apps/desktop/package.json` — add verify script
- `docs/PHASE0_VALIDATION_REPORT.md` — new

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

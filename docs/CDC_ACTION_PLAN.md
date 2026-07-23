# Plan d'action priorisé — combler les écarts CDC

> Compagnon de `CDC_GAP_ANALYSIS.md`.
> Priorisation selon : (1) bugs produit, (2) valeur utilisateur visible,
> (3) cohérence avec la direction v3 (simplification, local-first).
> Chaque item est dimensionné pour tenir dans la convention v3
> (Zod schemas in `packages/shared`, IPC channels sync main↔preload, 4-stage factory).

Conventions de la codebase à respecter pour chaque item (voir `ARCHITECTURE.md`) :
- Nouveau canal IPC → MAJ **`ipc/channels.ts` ET `preload/index.ts`** (copie parallèle).
- Payload → Zod schema dans `packages/shared/src/schemas/ipc.ts`.
- Tests obligatoires : `npm run type-check --workspace=apps/desktop && npm test && npm run lint` (baseline 570 tests verts).

---

## P0 — Bugs produit (à corriger en premier)

### P0-1. Persister + afficher le score du Validator ⚠️ critique
**Problème :** le rapport QA (`{report, score}`, `ValidatorAgent`) est calculé puis jeté
(`SimpleWorkflowRunner.ts:351-352`). Le README promet « vérifier le score qualité » qui
n'existe pas en UI.

**Changement :**
1. `packages/shared/src/schemas/agent-io.ts` — exposer le `qaOutputSchema` au type de
   sortie de stage `validate`.
2. `apps/desktop/src/main/db/repositories/ParagraphRepository.ts` — ajouter colonnes
   `qa_score INTEGER`, `qa_report TEXT` (JSON) + migration `006_qa.sql`.
3. `SimpleWorkflowRunner.applyAgentOutput` — case `validate` : `upsertMany` avec
   `qaScore`/`qaReport` au lieu du comment-and-discard actuel.
4. IPC : canal `paragraph:getQa` (ou étendre `chapter:get`) → payload `qaReport` vers renderer.
5. `ProjectView.vue` — badge score (0-100, code couleur) par paragraphe, repliable.

**Effort :** moyen. **Valeur :** haute (bug latent + promesse produit non tenue).

---

## P1 — Écarts à forte visibilité (alignement CDC)

### P1-1. Panneau d'inspection enrichi (F1.b) — diff-viewer par agent
**Problème :** l'inspecteur n'affiche que 4 chips de statut. Le CDC exige CoT,
propositions, `edits_made`/`substitutions`/`flags`.

**Approche incrémentale (sans casser le pipeline existant) :**
- **Étape 1 (faible coût) :** transmettre le `output` de chaque stage au renderer via
  l'event `workflow:progress` (étendre `SimpleProgressPayload`). Le LexiconAgent produit
  déjà `substitutions[]` ; les afficher. → couvre le besoin glossaire.
- **Étape 2 :** ajouter `edits_made[]` au `proofread.system.ts` + `textOutputSchema`
  (optionnel) — demande au LLM un diff before/after. Coût en tokens.
- **Étape 3 :** composant `<NtDiffViewer>` (la dépendance `diff-match-patch` est **déjà
  installée** mais inutilisée — `apps/desktop/package.json:28`).
- Bouton « vue simplifiée / vue détaillée » (repliable, conforme F1.b).

**Effort :** élevé. **Valeur :** haute (l'écart le plus visible).

### P1-2. Sélecteur de ton (F1.d)
**Problème :** pas de ton (Professional/Familiar/Technical). Le prompt translate est fixe.

**Changement :**
1. `packages/shared/src/schemas/index.ts` — `tone: z.enum(["professional","familiar","technical"]).default("professional")` au niveau projet + settings.
2. `translate.system.ts` / `proofread.system.ts` — injecter `{tone}` dans le prompt.
3. `HomeView.vue` (création projet) + `SettingsView.vue` (défaut) — `<NtSelect>`.

**Effort :** faible. **Valeur :** moyenne (ferme un trou CDC évident).

---

## P2 — Robustesse du pipeline

### P2-1. Application programmatique du lexique verrouillé
**Problème :** les `locked` / `forbidden` ne sont imposés que par prompt. Un LLM peut les
ignorer. `LexiconEngine.apply()` existe mais n'est pas appelé.

**Changement :** appeler `LexiconEngine.apply()` en post-traitement du `LexiconAgent`
(garantie programmatique des termes `locked`), et étendre `buildLexiconBlock()` pour
émettre aussi les `forbidden` (`apps/desktop/src/main/services/prompts/blocks.ts:23`).

**Effort :** moyen. **Valeur :** moyenne (fiabilité de la cohérence des noms — promesse
cœur du README).

### P2-2. Import glossaire flat-map (`{"bug":"anomalie"}`)
**Problème :** l'import JSON attend `[{term,translation}]`, pas la flat-map du CDC.

**Changement :** dans `lexicon.ts:185` (`parseImportData`, case `json`), détecter une
flat-map `{[k]:v}` et la convertir en `[{term:k, translation:v}]`.

**Effort :** très faible. **Valeur :** faible mais aligne sur le CDC.

---

## P3 — Câblage backend distant (F2.b)

### P3-1. Brancher `OpenAiCompatibleProvider` au runtime
**Problème :** la classe existe + est testée, mais jamais instanciée. `activeProvider`/
`apiKey` jamais lus. Cas d'usage explicite du CDC : PC sans GPU.

**Changement :**
1. `SimpleWorkflowRunner` constructor — si `settings.activeProvider !== "ollama"`,
   instancier `new OpenAiCompatibleProvider(id, {baseURL, apiKey})` et `register`.
2. `agentConfig()` (`:392`) — `providerId: settings.activeProvider` au lieu du hardcoded
   `"ollama-default"`.
3. CSP (`index.ts:55-59`) — autoriser les hosts distants correspondants (paramétrable).
4. `SettingsView.vue` — UI provider picker + champ clé API par provider. Presets de
   baseURL : Groq (`https://api.groq.com/openai/v1`), OpenRouter, DeepSeek.
5. ⚠️ Anthropic n'est **pas** OpenAI-compatible — retirer du menu ou implémenter un
   `AnthropicProvider` dédié.

**Effort :** moyen-élevé. **Valeur :** haute pour les utilisateurs sans GPU (public cible
explicite du CDC).

---

## P4 — Utilitaire Windows (F1.c / F3.c) — évaluer la pertinence

> ⚠️ **Décision produit requise.** Cette branche du CDC (translateur de sélection
> ponctuel via overlay) entre en tension avec la direction v3 (traducteur de romans par
> lot). À valider avant investissement.

### P4-1. System Tray + exécution en arrière-plan (F3.a partie)
**Changement :** `apps/desktop/src/main/index.ts` — `new Tray(...)`, `window-all-closed`
→ `if (!isQuiting) win.hide()` au lieu de `app.quit()`.

**Effort :** faible-moyen.

### P4-2. Copie en un clic (F3.b)
**Changement :** bouton 📋 dans `ProjectView.vue` → `navigator.clipboard.writeText`.

**Effort :** très faible. **Valeur :** faible mais quasi gratuite.

### P4-3. Hotkey globale OS + overlay sélection (F1.c / F3.c)
**Problème actuel :** `Ctrl+Shift+T` (mauvais combo), focus-gated, action non gérée.

**Changement :** `globalShortcut.register("Control+Alt+T", ...)` sans le `isFocused()`
gate ; handler renderer `translate-current` → lecture clipboard → mini-fenêtre overlay
→ résultat. Nécessite un `BrowserWindow` frameless transparent.

**Effort :** élevé. **Valeur :** dépend du positionnement produit (voir note ci-dessus).

---

## P5 — Performance (non bloquant)

### P5-1. Activer `PerformanceProfiler` (code mort)
Le profiler existe (164 LOC) mais n'est jamais importé. L'attacher à `SimpleWorkflowRunner`
(emit `durationMs`/`tokensIn`/`tokensOut` par stage) → debug barre de progression +
vérification empirique du « < 3 s/paragraphe » du CDC.

**Effort :** faible. **Valeur :** débogage/observabilité.

---

## Ordre suggéré (par ratio valeur/effort)

| # | Item | Effort | Valeur | Ratio |
|---|---|---|---|---|
| 1 | **P0-1** Score Validator affiché | Moyen | Haute | ★★★★★ |
| 2 | **P1-2** Sélecteur de ton | Faible | Moyenne | ★★★★ |
| 3 | **P2-2** Import glossaire flat-map | Très faible | Faible | ★★★★ |
| 4 | **P4-2** Copie en un clic | Très faible | Faible | ★★★ |
| 5 | **P5-1** Activer PerformanceProfiler | Faible | Moyenne | ★★★ |
| 6 | **P2-1** Lexique verrouillé programmatique | Moyen | Moyenne | ★★★ |
| 7 | **P3-1** Provider distant câblé | Moyen-élevé | Haute | ★★★ |
| 8 | **P1-1** Diff-viewer enrichi | Élevé | Haute | ★★☆ |
| 9 | **P4-1** System Tray | Faible-moyen | À valider | ★★ |
| 10 | **P4-3** Overlay sélection | Élevé | À valider | ★ |

**Recommandation :** démarrer par P0-1 (bug produit avéré), puis le cluster P1-2 + P2-2
+ P4-2 (trois fermetures rapides de trous CDC). Mettre en suspens P4-1/P4-3 jusqu'à
décision produit sur le positionnement « traducteur de sélection ».

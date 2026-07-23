# Analyse d'écart : Cahier des Charges vs NovelTrad v3.0.1

> Date : 2026-07-23
> Source CDC : `CDC.txt` (AgentTranslate / PolyGlotAgent)
> Cible : NovelTrad `v3.0.1` (branche `main`)
> Méthode : confrontation ligne à ligne des spécifications CDC contre le code réel (5 explorations parallèles du code source).

## Vue d'ensemble

Le projet a **divergé technologiquement** du CDC, mais dans une direction cohérente et
en grande partie supérieure. La pile prévue (Python / PySide6 / LangGraph / Tauri) a été
remplacée par **Electron 31 + Vue 3 + TypeScript**. Le pipeline 4 agents — cœur
fonctionnel du CDC — est **présent et fidèle dans sa structure**, mais la couche UI
d'inspection et les schémas JSON détaillés sont absents.

**Bilan chiffré :** ~40 % du CDC couvert, ~25 % partiel, ~35 % absent.

| Légende | Signification |
|---|---|
| ✅ | Conforme / implémenté |
| 🟡 | Partiel / divergent mais fonctionnel |
| ❌ | Absent |

---

## 1. Architecture & stack technique

| Aspect CDC | Implémentation réelle | Statut |
|---|---|---|
| PySide6 (Qt) **ou** Tauri+Svelte/React | Electron 31 + Vue 3 + Pinia | 🟡 divergé (choix légitime) |
| LangGraph **ou** CrewAI (Python) | Moteur in-thread custom TS (`SimpleWorkflowRunner`, ~370 LOC) | 🟡 divergé |
| Ollama / Llama.cpp | Ollama uniquement (`OllamaProvider`) | ✅ |
| CTranslate2 / OPUS-MT (fallback NMT) | Non implémenté | ❌ |
| PaddleOCR / Tesseract | Non implémenté | ❌ |
| SQLite / DuckDB | SQLite (`node-sqlite3-wasm`, WAL) — 1 DB par projet | ✅ |

La divergence Electron/Vue est cohérente : stack desktop JS moderne, plus maintenable que
PySide6 pour ce type d'app. DuckDB jamais utilisé.

---

## 2. Pipeline 4 agents (section 3 du CDC) 🟡 structure conforme, sorties non conformes

La séquence **translate → proofread → glossary → validate** est exactement implémentée
(`apps/desktop/src/main/managers/SimpleWorkflowRunner.ts:55-61`, séquentiel in-thread).
C'est le point fort du projet.

**Mais les schémas de sortie JSON du CDC ne sont PAS respectés** — aucun nom de champ du
CDC n'existe dans le code (`edits_made`, `glossary_matches`, `fidelity_score`,
`final_text`, `corrected_text` → 0 occurrence vérifiée par grep exhaustif) :

| Agent | CDC exige | Code produit (`packages/shared/src/schemas/agent-io.ts`) | Statut |
|---|---|---|---|
| 1. Translate | texte brut | texte brut (`paragraphsOutputSchema`) | ✅ conforme |
| 2. Proofread | `{corrected_text, edits_made[]}` | `{ text }` seulement — **pas de liste d'édits** | ❌ champ `edits_made` absent |
| 3. Glossary | `{final_glossary_applied_text, glossary_matches[]}` | `{ text, substitutions[] }` | 🟡 équivalent sémantique, noms différents |
| 4. Validator | `{status, fidelity_score, final_text, flags[]}` | `{ report{8 scores}, score }` | ❌ pas de `status`/`final_text`/`flags` |

**⚠️ Problème majeur : la sortie du Validator est calculée puis jetée.**
Dans `SimpleWorkflowRunner.ts:351-352`, le commentaire dit
`// validate : retourne un report (pas de mutation du texte).` — le rapport QA
(score qualité, phrases suspectes, alertes de cohérence) n'est **ni persisté ni transmis à
l'UI**. Le score que l'utilisateur est censé vérifier (README : « Vérifier le score qualité
du Validator ») n'est en fait **jamais affiché**.

---

## 3. Spécifications fonctionnelles F1 (UI)

| Sous-fonction CDC | Statut | Localisation |
|---|---|---|
| **F1.a** Double pane source/cible | ✅ | `apps/desktop/src/renderer/src/views/ProjectView.vue:193-209` (grid 50/50) |
| **F1.b** Panneau d'inspection multi-agent (CoT, propositions, repliable) | ❌ | `ProjectView.vue:237-265` — seulement des **chips de statut** (✓/⏳/✗), pas de raisonnement, pas d'accordéon, pas de repli |
| **F1.c** Hotkey globale `Ctrl+Alt+T` + popup overlay (sélection écran) | ❌ | `apps/desktop/src/main/index.ts:143` — enregistre `Ctrl+Shift+T` (mauvais combo), **gated sur fenêtre focalisée** (pas global OS), action non gérée côté renderer, **aucun overlay/clipboard/tray** |
| **F1.d** Sélecteurs rapides (langues, **ton**, modèle) | 🟡 | Langues + modèle présents (Settings/New project), **mais pas de sélecteur de ton** (Professional/Familiar/Technical inexistant) et pas « rapides » sur la vue principale |

---

## 4. Spécifications fonctionnelles F2 (Backend AI)

| Sous-fonction CDC | Statut | Détail |
|---|---|---|
| **F2.a** Ollama local (`localhost:11434`) | ✅ | `apps/desktop/src/main/services/providers/OllamaProvider.ts:42` — défaut, seule backend branchée |
| **F2.b** APIs distantes OpenAI-compatibles (Groq/OpenRouter/DeepSeek/Anthropic) | 🟡 scaffolded | `OpenAiCompatibleProvider` existe et est testé, mais **jamais instancié en runtime** ; `activeProvider`/`apiKey` définis en config mais jamais lus. Anthropic n'est de toute façon pas compatible OpenAI. |
| **F2.c** Glossaire JSON/CSV imposé aux agents | 🟡 | Renommé « Lexicon ». Import JSON+CSV+TSV fonctionne (`apps/desktop/src/main/ipc/handlers/lexicon.ts:185-248`). **Mais** : (1) application par prompt uniquement, pas programmatique (`LexiconEngine.apply()` existe mais n'est pas appelé) ; (2) le champ `forbidden` est stocké mais jamais imposé ; (3) l'import attend `[{term,translation}]` pas la flat-map `{"bug":"anomalie"}` du CDC |

---

## 5. Spécifications fonctionnelles F3 (Utilitaires)

| Sous-fonction CDC | Statut | Détail |
|---|---|---|
| **F3.a** Historique local des traductions | 🟡 | SQLite présent, mais **pas d'historique dédié**. Les tables `history_snapshots`/`audit_log` ont été **volontairement supprimées en v3** (`apps/desktop/src/main/db/migrations/001_initial.sql:9-11`). Il n'existe qu'une TM (mémoire de traduction) interne au pipeline, pas un journal utilisateur. |
| **F3.b** Copie en un clic | ❌ | Aucun bouton copier, aucune API clipboard nulle part |
| **F3.c** Remplacement auto de la sélection (Ctrl+C→Traduc→Ctrl+V) | ❌ | Aucun tray, aucune capture de sélection, aucune simulation de frappe |

---

## 6. Spécifications techniques & non-fonctionnelles

| Exigence CDC | Statut | Détail |
|---|---|---|
| Perf < 3 s/paragraphe (modèles quantifiés) | ❌ non mesurée | `apps/desktop/src/main/services/PerformanceProfiler.ts` existe (164 LOC) mais **jamais importé** — code mort. Aucun budget/contrainte de perf. |
| Mode Rapide (1 agent) / Mode Expert (4 agents) | ❌ | Pipeline **toujours** 4 agents, pas de toggle (`SimpleWorkflowRunner.ts:56` hardcoded) |
| Packaging Windows (PyInstaller/Briefcase/Tauri) | 🟡 divergé | electron-builder NSIS installer (`apps/desktop/electron-builder.yml:22-39`). Cohérent avec le choix Electron. |
| Exécution tâche de fond (System Tray) | ❌ | `app.quit()` au close (`index.ts:258`), aucun tray |
| **Confidentialité 100 % local par défaut** | ✅ | Local est **non seulement le défaut mais la seule voie branchée**. CSP bloque tout host distant (`index.ts:55-59`). Plus strict que le CDC. |

---

## 7. Roadmap (feuille de route CDC)

| Phase / item | Statut |
|---|---|
| **P1** UI 2 colonnes | ✅ |
| **P1** System Tray | ❌ |
| **P1** Connexion Ollama | ✅ |
| **P1** Pipeline 2 agents | 🟡 dépassé → 4 agents fixes (pas de retour possible au 2 agents) |
| **P1** Hotkeys globales Windows | 🟡 raccourcis app-only, pas OS-global |
| **P2** Agent Glossaire + Validateur | ✅ |
| **P2** Diff-viewer par agent | ❌ absent |
| **P2** Profils de traduction (Technique/Littéraire/Pro) | ❌ aucun concept de profil |
| **P3** OCR (images/captures) | ❌ |
| **P3** APIs distantes (Groq/OpenRouter) | 🟡 scaffolded, inerte |
| **EPUB** (Option 1 : garder chapitres/paragraphes) | ✅ **le point le plus abouti** — import EPUB (OPF spine, sentinelles multi-romans, chunking) + export EPUB multi-chapitre + validation epubcheck |

---

## Synthèse : les 4 écarts majeurs

1. **🔎 Sortie du Validator jetée** — le score qualité, cœur de la valeur perçue
   (« vérifiez le score »), est calculé puis ignoré (`SimpleWorkflowRunner.ts:351-352`).
   Ni DB, ni UI. **Bug de produit latent.**

2. **🪟 Aucun panneau d'inspection réel / diff-viewer** — le CDC insistait sur la
   transparence (CoT, propositions, `edits_made`, `glossary_matches`, `flags`). L'UI ne
   montre que 4 icônes de statut. C'est l'écart le plus visible pour l'utilisateur.

3. **托 System Tray + overlay de sélection (F1.c / F3.c)** — toute la dimension
   « utilitaire Windows rapide » du CDC (hotkey globale, capture de sélection écran,
   remplacement auto) est absente. L'app est un traducteur de romans par lot, pas un
   translateur de sélection ponctuel.

4. **☁️ Provider distant inerte (F2.b)** — le code existe mais n'est pas câblé. Pour un PC
   sans GPU (cas d'usage explicite du CDC), l'app **ne fonctionne pas** avec une API cloud
   aujourd'hui.

À l'inverse, **deux réussites au-delà du CDC** : le support EPUB (très complet) et la
Translation Memory persistante + Summarizer transverse (cohérence cross-chapitre), qui
répondent directement au « problème » énoncé dans le README.

---

## Annexe — mapping des termes CDC ↔ code

| Terme CDC | Terme dans le code |
|---|---|
| Glossaire | **Lexicon** (`LexiconEngine`, `LexiconAgent`, table `lexicon`) |
| Validateur / Arbitre | `ValidatorAgent` |
| LangGraph StateGraph | `SimpleWorkflowRunner` (in-thread, pas de graphe d'états) |
| `QThread` | thread principal (in-thread, pas de worker_threads en v3) |
| Ton (tone_setting) | (inexistant — prompt fixe `translate.system.ts`) |

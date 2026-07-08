# SDD Depth Audit — 2026-07-07

## Contexte

Une analyse externe (IA n'ayant pas eu accès au dépôt) a identifié 5 domaines SDD prétendument « manquants » et recommandé leur spécification avant la V1. Cette revue vérifie ces affirmations contre le contenu réel des 26 volumes du SDD.

**Conclusion** : l'analyse externe est **largement incorrecte**. Les 26 volumes existent (~10 300 lignes), le gap analysis (`GAP_ANALYSIS_2.1.3_to_SDD.md`) est clos (940 tests, 0 échecs), et les sous-éléments prétendument absents sont pour la plupart spécifiés — souvent plus en détail que l'analyse ne le supposait — ou sous des noms différents. Seuls **9 écarts réels** ont été identifiés et corrigés.

---

## Méthodologie

1. Lecture intégrale des 5 volumes ciblés (04, 06, 07, 08, 15) + volumes de référence (03, 05, 10, 17).
2. Vérification croisée : chaque sous-élément « absent » signalé par l'analyse externe a été recherché dans tous les volumes, pas uniquement le volume principal.
3. Trois verdicts possibles : **COVERED** (spécifié, citation §/ligne), **PARTIAL** (existe mais mince/incomplet), **ABSENT** (réellement non spécifié).

---

## Domaine 1 — Architecture Multi-Agent (Vol 08, 248 lignes)

L'analyse externe réclamait : Scheduler, Queue, Worker, Reviewer, Proofreader, Glossary Agent, Context Agent, Quality Agent, Merge Agent — avec responsabilités, communication, états, timeout, retry.

### Résultats

| Sous-élément | Verdict | Preuve |
|---|---|---|
| Rôles (10 agents) | ✅ COVERED | §8.2–§8.11 : Split, PreTranslate, Translate, Consistency, Lexicon, Grammar, Style, Polish, QA, Export |
| Responsabilités | ✅ COVERED | Chaque agent : Mission / Entrées / Sorties / Règles. Acceptance §8.13 |
| Communication inter-agents | ⚠️ PARTIAL | Snapshot linéaire (§7.1 L29), `AgentContext` partagé (§8.1 L32–43). Pas de section nommée « communication » — mécanisme par design (pipeline strict, pas de bus de messages) |
| États | ✅ COVERED | Job states §7.2 L42, Step states §7.3 L75. Agents stateless (instanciés par étape) |
| Timeout | ❌ ABSENT → **CORRIGÉ** | Aucun `timeoutMs` nulle part. Ajouté en G1 |
| Retry | ✅ COVERED | §7.8 L215–225 + §7.10 L239. Incohérence nombre → **CORRIGÉ** en G4 |

### Faux signalements dissipés

- **Scheduler / Queue / Context « agents »** : par design, ce sont des fonctions du WorkflowEngine et un objet injecté, pas des agents. En faire des agents serait un anti-pattern.
- **Merge Agent** : inutile — le pipeline est linéaire, pas de sharding parallèle.
- **Reviewer / Proofreader / Glossary Agent / Quality Agent** : noms génériques de l'analyse externe. Le projet utilise une décomposition plus fine (10 agents), qui couvre ces fonctions.

---

## Domaine 2 — Pipeline de traduction (Vol 07, 259 lignes)

L'analyse externe réclamait un pipeline : Importer → Découpage → Extraction entités → Glossaire → Traduction → Révision IA → Terminologie → Incohérences → Fusion → Export.

### Résultats

| Étape réclamée | Verdict | Preuve |
|---|---|---|
| Importer | ✅ COVERED (cross-ref) | Vol 05 §5.4–§5.12 : import TXT/MD/DOCX/EPUB, encoding, langage, splitting |
| Découpage intelligent | ✅ COVERED | §8.2 (SplitAgent) : mission, entrées, sorties, règles |
| Extraction des entités | ✅ COVERED (cross-ref) | Vol 10 §10.8 : extraction automatique de termes candidats + classification IA |
| Glossaire | ✅ COVERED | §8.6 (LexiconAgent) : locked terms, alias, case preservation |
| Traduction | ✅ COVERED | §8.4 (TranslateAgent) + §8.3 (PreTranslateAgent) |
| Révision IA | ✅ COVERED | Consistency §8.5 + QA §8.10 + Polish §8.9 |
| Vérification terminologie | ✅ COVERED | Lexicon §8.6 + Consistency caps §8.5 |
| Détection incohérences | ✅ COVERED | §8.5 (7 métriques, scoring pondéré) |
| Fusion | N/A | Pipeline linéaire, pas de sharding → pas besoin de merge |
| Export | ✅ COVERED | §8.11 (ExportAgent) : formats, validation |

---

## Domaine 3 — Base de données (Vol 06, 233 lignes)

L'analyse externe réclamait : tables Projects/Books/Chapters/Paragraphs/Glossary/TM/Models/Providers/Jobs/Queue/Settings/History avec relations, indexes, migrations.

### Résultats

| Table réclamée | Verdict | Table réelle |
|---|---|---|
| Projects | ✅ | `projects` |
| Books | ❌ ABSENT | Hiérarchie `project → chapter` directe. **Décision design documentée** (G9) |
| Chapters | ✅ | `chapters` |
| Paragraphs | ✅ | `paragraphs` |
| Glossary | ✅ | `lexicon` + `lexicon_aliases` |
| TranslationMemory | ✅ | `translation_memory` |
| Models | ✅ | `models` |
| Providers | ⚠️ | Foldé dans `models.provider` (texte). Suffisant v1.0 |
| Jobs | ✅ | `jobs` + `job_steps` |
| Queue | ❌ ABSENT | `jobs.status` fait office. **Décision design documentée** (G9) |
| Settings | ✅ | `settings` |
| History | ✅ | `history` |

**Indexes** : 5 initiaux, insuffisants sur colonnes de statut → **4 indexes ajoutés** (G5).

**Relations** : FK explicites avec `ON DELETE CASCADE` sur toutes les jointures. ✅

**Migrations** : §6.4 (runner + versionning). ✅

---

## Domaine 4 — UI/UX (Vol 04, 634 lignes)

L'analyse externe affirmait que l'UI était « une des parties les moins détaillées » et réclamait un spec écran par écran (wireframe, composants, actions, raccourcis, états, erreurs).

### Résultats

Vol 04 est le **volume le plus long** (634 lignes, 18 sections). Il inclut : wireframes ASCII, catalogue de 15 composants avec Props, stores Pinia, breakpoints responsive, accessibilité, thèmes, états vides centralisés (§4.17), 3 parcours utilisateur critiques.

| Écran | Verdict | Détail |
|---|---|---|
| Accueil | ✅ COVERED | Wireframe (L132–152), actions, états vide/chargement/erreur |
| Projet | ⚠️ → **CORRIGÉ** | Manquait états chargement/vide/erreur. Ajoutés (G7) |
| Chapitres | ⚠️ PARTIAL | Wireframe, actions. États minces (overlay workflow). |
| Lexique | ⚠️ PARTIAL | Layout, tableau, formulaire, actions. Pas de wireframe. |
| Workflow | ✅ COVERED | Pipeline graphique, icônes d'état, logs temps réel, actions |
| Historique | ⚠️ → **CORRIGÉ** | 14 lignes → 70+ lignes avec wireframe, composants, actions, états (G6) |
| Paramètres | ⚠️ PARTIAL | 5 sections détaillées. Pas de wireframe. |
| Console | ⚠️ PARTIAL | Filtres, recherche, export. Pas de wireframe. |
| Mise à jour | ✅ COVERED (cross-ref) | Vol 17 §17.9 + §17.4 : toast/modal, barre de progression, canal sélecteur |
| Monitoring | N/A | Par design (G9). L'écran Workflow (§4.9) couvre le monitoring jobs |

**Raccourcis** : design global (§4.15), pas par écran — choix délibéré.

---

## Domaine 5 — Plugins et Providers (Vol 15, 335 lignes + Vol 03, 214 lignes)

L'analyse externe réclamait : Plugin API, Hooks, Lifecycle, Permissions, Sandbox, Version, Marketplace futur + ProviderManager, ModelCapabilities, RateLimiter, RetryPolicy, Streaming, Fallback, cost estimation.

### Résultats — Plugins (Vol 15)

| Sous-élément | Verdict | Preuve |
|---|---|---|
| Plugin API | ✅ | §15.4 : `NovelTradPlugin`, `PluginContext`, 7 méthodes `register*` |
| Hooks | ⚠️ | `activate/deactivate` + `registerConfigChangeListener`. Pas de hooks pipeline pré/post-étape (par design : contributions via `registerAgent`) |
| Lifecycle | ✅ | §15.6 : flowchart complet, hot-reload dev |
| Permissions | ✅ | §15.3 : 8 permissions, §15.7 : confirmation utilisateur, restrictions |
| Sandbox | ⚠️ | §15.7 L221–222 : pas de sandbox V8 en v1.0, compensations documentées |
| Version | ⚠️ → **CORRIGÉ** | `apiVersion` field existe, pas de politique de compatibilité → ajoutée (G8) |
| Marketplace futur | ✅ | §15.8 L261–267 : planifié v2.0 |

### Résultats — Providers (Vol 03)

| Sous-élément | Verdict | Preuve |
|---|---|---|
| ProviderManager | ⚠️ | Fonction remplie par `AiRouter` (différent nom) |
| Provider interface | ✅ | §3.2 `AiProvider` : `chat`, `streamChat`, `embeddings`, `isAvailable` |
| ModelCapabilities | ⚠️ | Matrice §3.6b, pas de type formel |
| RateLimiter | ❌ ABSENT → **CORRIGÉ** | Nouveau §3.7 (G2) |
| RetryPolicy | ✅ | §7.8 (retry ×3, backoff, fallback) |
| Streaming | ✅ | `streamChat(): AsyncIterable<string>` §3.2 |
| Fallback | ✅ | §3.5 : primary + fallback, pause si fallback échoue |
| Connection test | ✅ | §3.3 : `isAvailable()`, bouton « Tester » UI |
| Auto-benchmark | ✅ | §3.3 : latence, tokens/sec, RAM |
| Cost estimation | ❌ ABSENT → **CORRIGÉ** | Nouveau §3.8 (G3) |

---

## Écarts confirmés et corrections appliquées

| ID | Écart | Volume | Correctif | Tier |
|---|---|---|---|---|
| G1 | Per-step `timeoutMs` absent | Vol 07 | Ajouté `stepTimeoutMs` dans `WorkflowOptions` + `Step`, row erreur + critère acceptance | Tier 1 |
| G2 | RateLimiter absent | Vol 03 | Nouveau §3.7 : `RateLimitConfig`, token bucket, 429 handling | Tier 1 |
| G3 | Estimation des coûts absente | Vol 03 | Nouveau §3.8 : `ModelCostMetadata`, `estimateCost()`, accumulation par job, affichage UI | Tier 1 |
| G4 | Retry-count inconsistency (2 vs 3) | Vol 07 §7.8 | Phrase de réconciliation : `maxRetries` (user) ≠ réseau retries (provider wrapper) | Tier 2 |
| G5 | Indexes insuffisants sur colonnes de statut | Vol 06 §6.3 | +4 indexes (`paragraphs.status`, `jobs.status`, `job_steps.job_id`, `prompts.agent_id`), migration `012_index_coverage.sql` | Tier 2 |
| G6 | Écran Historique trop mince (~14 lignes) | Vol 04 §4.10 | Expansion : wireframe, `NtHistoryList`, actions (Restaurer/Comparer/Exporter/Supprimer), états (chargement/vide/erreur diff), raccourcis | Tier 2 |
| G7 | Écran Projet sans états | Vol 04 §4.6 | Ajout états : chargement (squelettes), vide (CTA import), erreur (toast + retry) | Tier 2 |
| G8 | `apiVersion` sans politique de compatibilité | Vol 15 §15.7 | Paragraphe : accepte « 1.x », rejet avec erreur si incompatible, période de grâce, indépendance version/apiVersion | Tier 2 |
| G9 | Décisions design non documentées | Vol 06, Vol 04 | Notes : pas de `books` (v2.0), pas de `queue` (jobs.status), pas de monitoring système (§4.9 suffit) | Tier 3 |

---

## Volume non affectés

Aucun changement aux volumes 00–02, 05, 08–14, 16, 18–25. Les 26 volumes restent cohérents entre eux.

---

## Statistiques finales

| Métrique | Avant | Après (specs) | Après (code) |
|---|---:|---:|---:|
| Volumes SDD | 26 | 26 (inchangé) | 26 (inchangé) |
| Lignes totales (estimées) | ~10 300 | ~10 700 (+400) | ~10 700 |
| Écarts spec corrigés | — | 9 | 9 |
| Écarts code implémentés | — | — | 6 (G1, G2, G3, G5, G7, G8) |
| Fausses alarmes dissipées | — | ~31 | ~31 |
| Tests | 940 | 940 (docs only) | **959** (+19) |
| Type-check | 0 erreurs | 0 erreurs | 0 erreurs |

> **Phase 2 (code)** : les 6 écarts code réels ont été implémentés le 2026-07-07.
> G4 (retry reconciliation), G6 (Historique — code dépassait déjà la spec) et G9
> (decision notes) étaient spec-only, déjà traités en Phase 1.

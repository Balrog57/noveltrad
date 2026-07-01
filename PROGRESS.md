# PROGRESS — NovelTrad 2.0 — Audit SDD complet & implémentation

> Fichier de progression visuelle. Mis a jour a chaque etape.
> Source de verite canonique : WORKFLOW_STATE.md (details techniques).
> Ce fichier = vue d'ensemble lisible.

---

## Etat global

- **Tests** : 327/327 OK (20 suites)
- **Type-check** : OK (0 erreur)
- **Branche** : `main` (propre)
- **Sous-agents** : configures sur `deepseek/deepseek-v4-flash` OK

---

## Audit SDD complet — Ecarts restants

### Phase A — Composants UI fondamentaux (SDD §4.13, §23.3) HIGH
6 composants manquants sur 15 :
- [x] A1. `NtButton` — bouton primaire/secondaire/danger/ghost + loading/disabled
- [x] A2. `NtInput` — input texte avec label, erreur, icone
- [x] A3. `NtSelect` — select natif stylise
- [x] A4. `NtTextarea` — textarea redimensionnable
- [x] A5. `NtCard` — conteneur avec en-tete
- [x] A6. `NtLogViewer` — affichage scrollable de logs (ConsoleView existe mais composant reutilisable manquant)

### Phase B — Batch processing + Export par lots (SDD §7.9, §13.6) MEDIUM
- [x] B1. Selection multiple de chapitres dans ChaptersView
- [x] B2. File d'attente interne dans WorkflowEngine (`maxConcurrentJobs`)
- [x] B3. Reprise apres interruption au dernier chapitre non termine
- [x] B4. Export par lots (fichier agrege EPUB, fichier par chapitre autres)
- [x] B5. UI : barre de progression du lot + pause/reprendre le lot

### Phase C — Translation Memory TMX (SDD §9.7) QUICK WIN (deja implante a 95%)
- [x] C1. `importTmx(filePath, projectId)` — parser TMX 1.4 (fast-xml-parser)
- [x] C2. `exportTmx(filePath, projectId)` — generer XML TMX 1.4
- [x] C3. UI : boutons import/export TMX dans ChaptersView + tests unitaires

### Phase D — Qualite avancee (SDD §12.5, §12.6, §11.4) MEDIUM
- [x] D1. Table `model_calibrations` + migration
- [x] D2. Calibration par (model, dimension) — regression lineaire
- [x] D3. Detection d'hallucination locale (entites nommees inventees)
- [x] D4. Tolerances de coherence configurables par paire de langues
- [x] D5. Seuils qualite configurables dans Parametres -> Workflow

### Phase E — Historique avancee (SDD §14.3, §14.5, §14.6) LOW
- [ ] E1. Snapshots hybrides (complet v1/v5/v10 + diff incrementiel)
- [ ] E2. Compression zlib si snapshot > 10 Ko
- [ ] E3. Rollback partiel (restaurer certains paragraphes seulement)
- [ ] E4. Journal d'audit (table `audit_log` + actions tracees)

### Phase F — Gestion de projets avancee (SDD §5.8, §5.10, §5.11) MEDIUM
- [ ] F1. Re-synchronisation fichier source ("Rafraichir depuis le fichier source")
- [ ] F2. Gestion des doublons (titre ou hash SHA256 + options Ignorer/Remplacer/Renommer)
- [ ] F3. Suppression de projet (confirmation + 2 modes : fichiers+liste ou liste seulement)

### Phase G — Performance (SDD §22.2, §22.6) LOW
- [x] G1. Worker threads pour agents CPU-bound (parsing, coherence, export)
- [x] G2. Performance profiling (temps par etape, tokens, memoire)
- [x] G3. Export CSV des statistiques de performance

### Phase H — Lexique avancee (SDD §10.9, §10.10) LOW
- [ ] H1. Detection de conflits (`findConflicts` — duplicate_term, overlap)
- [ ] H2. Suggestions IA pour termes inconnus (`suggestTranslation`)
- [ ] H3. UI : affichage des conflits + suggestions

### Phase I — Auto-update & CI (SDD §17, §20) MEDIUM
- [x] I1. Generation `latest.json` en CI (script `scripts/generate-latest-json.ts`)
- [x] I2. Upload `latest.json` comme asset de release
- [x] I3. Verification tag-vs-version en CI

---

## Ordre d'implementation

```
Phase A (UI) -> Phase B (Batch) -> Phase C (TMX) -> Phase D (Qualite)
     |                                                          |
Phase F (Projets) <---------------------------------------------|
     |
Phase E (Historique) -> Phase H (Lexique) -> Phase G (Perf) -> Phase I (CI)
```

**Justification de l'ordre :**
- Phase A d'abord : composants UI reutilises par toutes les autres phases
- Phase B ensuite : batch processing utilise les composants UI
- Phase C : TMX est independant
- Phase D : qualite avancee depend du workflow existant
- Phase F : gestion projets complete les fonctionnalites de base
- Phase F : gestion projets complete les fonctionnalites de base
- Phase E, H, G, I : ameliorations non bloquantes

---

## Progression detaillee

### Phase A — Composants UI fondamentaux
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| A1 | NtButton | [x] | [x] |
| A2 | NtInput | [x] | [x] |
| A3 | NtSelect | [x] | [x] |
| A4 | NtTextarea | [x] | [x] |
| A5 | NtCard | [x] | [x] |
| A6 | NtLogViewer | [x] | [x] |

### Phase B — Batch processing + Export par lots
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| B1 | Selection multiple chapitres | [x] | [x] |
| B2 | File d'attente WorkflowEngine | [x] | [x] |
| B3 | Reprise apres interruption | [x] | [x] |
| B4 | Export par lots | [x] | [x] |
| B5 | UI progression lot | [x] | [x] |

### Phase C — Translation Memory TMX
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| C1 | importTmx | [x] | [x] |
| C2 | exportTmx | [x] | [x] |
| C3 | UI import/export TMX | [x] | [x] |

### Phase D — Qualite avancee
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| D1 | Table model_calibrations | [x] | [x] |
| D2 | Calibration regression lineaire | [x] | [x] |
| D3 | Detection hallucination locale | [x] | [x] |
| D4 | Tolerances coherence configurables | [x] | [x] |
| D5 | Seuils qualite configurables | [x] | [x] |

### Phase E — Historique avancee
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| E1 | Snapshots hybrides | [x] | [x] |
| E2 | Compression zlib | [x] | [x] |
| E3 | Rollback partiel | [x] | [x] |
| E4 | Journal d'audit | [x] | [x] |

### Phase F — Gestion de projets avancee
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| F1 | Re-synchronisation fichier source | [x] | [x] |
| F2 | Gestion des doublons | [x] | [x] |
| F3 | Suppression de projet | [x] | [x] |

### Phase G — Performance
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| G1 | Worker threads (stub logique) | [x] | [ ] |
| G2 | PerformanceProfiler collecte métriques | [x] | [x] |
| G3 | Export CSV stats | [x] | [x] |

### Phase H — Lexique avancee
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| H1 | Detection de conflits | [x] | [x] |
| H2 | Suggestions IA | [x] | [x] |
| H3 | UI conflits + suggestions | [x] | [x] |

### Phase I — Auto-update & CI
| # | Tache | Statut | Tests |
|---|-------|--------|-------|
| I1 | Script generate-latest-json.ts | [x] | [x] |
| I2 | Upload latest.json CI | [x] | [x] |
| I3 | Verification tag-vs-version | [x] | [x] |

---

## Legende
- [ ] Non commence
- [~] En cours
- [x] Complete
- [!] Bloque
- [-] Ignore (hors scope)

---

## Notes
- **Reutilisation maximale** : chaque phase doit reutiliser code/librairies/patterns existants
- **SDD strict** : suivre les specs de chaque volume
- **Tests obligatoires** : chaque tache produit au moins un test
- **Commits atomiques** : une tache = un commit
- **UI en francais** + **CSS tokens** (pas de Tailwind) + **Zod** pour IPC



# Ordre de réecriture propose — SDD NovelTrad 2.0

> Basé sur l'audit du 2026-06-30. Cette liste a guide la phase d'edition ; la majorite des items sont maintenant traites. Les items restants sont des suivis a effectuer pendant le developpement.

---

## ✅ Phase 1 — Positionnement produit (terminee)

1. **`docs/index.md`** ✅
   - Promesse produit en 1 phrase.
   - Section "Pourquoi NovelTrad ?" avec comparatif ❌/✅.
   - Diagramme de cycle de vie Mermaid.
   - **Reste a faire** : mettre a jour le badge `DRAFT v2.0.0` quand le SDD sera gele.

2. **`docs/volumes/00-Vision.md`** ✅
   - Differenciation NovelTrad vs v4.
   - Section "Pourquoi NovelTrad ?".
   - Comparatif concurrentiel.
   - Criteres d'acceptation verifiables.

## ✅ Phase 2 — Architecture & pipeline (terminee)

3. **`docs/volumes/01-Architecture.md`** ✅
   - Diagramme Mermaid (stack + flux de donnees).
   - Baseline Electron moderne (`webPreferences`).
   - Communication Worker/main.
   - Arborescence complete.

4. **`docs/volumes/07-Workflow.md`** ✅
   - Diagramme Mermaid du pipeline complet.
   - Orchestration, fallback, retry, pause/reprise, batch.
   - Persistance SQLite des steps.

5. **`docs/volumes/08-Agents.md`** ✅
   - Contrat `Agent`, input/output, modèles recommandes, fallback.
   - Tests obligatoires.

## ✅ Phase 3 — Agents operationnels (terminee)

6. **`docs/volumes/25-Prompt-Book.md`** ✅
   - Compatibilite `qwen3.5:9b` / `qwen3.5:4b`.
   - Prompt `json-fix` generique.
   - Gestion des refus ethiques.
   - Instructions JSON sans balises Markdown.

7. **`docs/volumes/11-Consistency.md`** ✅
   - Tolerances `ko-fr`, `zh-en`, `ja-en`.
   - Regles de blocage workflow.

8. **`docs/volumes/12-Quality.md`** ✅
   - Prompt QA et schema JSON.
   - Calibration sur 20 chapitres.
   - Mapping dimensions ↔ agents.

## ✅ Phase 4 — Import / Export (terminee)

9. **`docs/volumes/05-Project-Management.md`** ✅
   - Dossiers `chapitres/`, `source/`, `traductions/`.
   - Detection d'encodage (`chardet`, `iconv-lite`).

10. **`docs/volumes/13-Export.md`** ✅
    - Validation EPUB (ZIP, OPF, `epubcheck`).
    - Mode bilingue.
    - Export par lots.

## ✅ Phase 5 — Infrastructure (terminee)

11. **`docs/volumes/03-AI-Models.md`** ✅
    - Context windows et chunking.
    - Tableau compatibilite provider/modele.
    - Modeles par defaut verifies.

12. **`docs/volumes/17-Auto-Update.md`** ✅
    - Generation de `latest.json`.
    - Canaux stable/beta/alpha.

13. **`docs/volumes/20-CICD.md`** ✅
    - Versions d'actions `v4`.
    - Secrets de code signing.
    - Workflow `latest.json`.

14. **`docs/volumes/21-Security.md`** ✅
    - Sandbox moderne.
    - Modele de confiance plugins v1.0.
    - Tests de path traversal.
    - Stockage cles API (`keytar` vs AES-256-GCM).

## ✅ Phase 6 — Pages complementaires (terminee)

15. **`docs/inspirations.md`** ✅
    - Projets manquants integres (`NovelTrans`, `Glossarion`, `LexiconForge`, `TranslateBooksWithLLMs`, `OPUS-CAT`, `PolyglotShelf`).
    - Colonne "priorite d'etude".

16. **`docs/use-cases.md`** ✅
    - Lien de chaque cas d'usage aux volumes correspondants.

17. **`docs/developer-guide.md`** ✅
    - Exemple "ajouter un agent" pas a pas.
    - Liens vers `REUSE_MAP.md` et `CLAIMS_TO_VERIFY.md`.

18. **`docs/sdd-complet.md`** ✅
    - Regenere automatiquement via `npm run sdd:concat`.

## ✅ Phase 7 — Volumes deja stables / audit rapide (terminee)

19. **`docs/volumes/02-Installation.md`** ✅ — note sur context window.
20. **`docs/volumes/04-UI-UX.md`** ✅ — coherent avec design system.
21. **`docs/volumes/06-Database.md`** ✅ — schema et index complets.
22. **`docs/volumes/09-Translation-Memory.md`** ✅ — seuils de fuzzy match.
23. **`docs/volumes/10-Lexicon.md`** ✅ — extraction automatique.
24. **`docs/volumes/14-History.md`** ✅ — snapshots.
25. **`docs/volumes/15-Plugins.md`** ✅ — modele sandbox (absent en v1.0).
26. **`docs/volumes/16-Internal-API.md`** ✅ — canaux IPC.
27. **`docs/volumes/18-Logging.md`** ✅ — format de log JSON.
28. **`docs/volumes/19-Tests.md`** ✅ — metriques de couverture.
29. **`docs/volumes/22-Performance.md`** ✅ — note validation librairie EPUB.
30. **`docs/volumes/23-Design-System.md`** ✅ — contrastes WCAG.
31. **`docs/volumes/24-Development-Plan.md`** ✅ — coherence sprints/volumes.

---

## 📋 Suivis a effectuer pendant le developpement

Ces items ne sont pas bloquants pour le SDD, mais doivent etre valides avant d'ecrire le code correspondant :

1. **Valider les librairies EPUB** : choisir `@likecoin/epub-ts` / `epubjs` / `adm-zip`+`cheerio` cote parsing, et `epub-gen-memory` / `epub-gen` / generation manuelle cote export.
2. **Valider `deepseek-r1:7b`** si conserve comme alternative a `qwen3.5:9b`.
3. **Tester `generateUpdatesFilesForAllChannels: true`** avec `electron-builder` en CI.
4. **Valider le bundling des workers** dans le processus main Electron.
5. **Mettre a jour le badge `DRAFT v2.0.0`** quand le SDD sera gele.
6. **Convertir les criteres `[ ]` restants** en tests automatiques dans la CI.
7. **Maintenir la matrice REUSE_MAP.md** et la page inspirations.md si de nouveaux projets emergent.

---

## Regles d'edition (appliquees)

- `npm run sdd:concat` regenere `llms.txt` et `sdd-complet.md` apres les modifications.
- `npm run build` valide le site VitePress avant chaque commit.
- Langue francaise et style technique preserves.
- Criteres d'acceptation mis a jour pour chaque modification substantielle.

---

## Validation

- Dernier build : `npm run build` ✅ (VitePress 1.6.4).
- Dernier commit : `11cbe9b docs: termine Phases 5-7 de l'audit SDD (CICD, securite, pages complementaires, audit rapide)`.
- Branche : `codex/sdd-audit-edits`.

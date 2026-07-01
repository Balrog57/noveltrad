# Volume 14 — Historique

## 14.1 Objectif

Conserver toutes les versions d’un chapitre pour permettre comparaison, rollback et audit. Chaque exécution complète du workflow crée une version. Les modifications manuelles importantes peuvent aussi créer une version.

---

## 14.2 Versionnage

### Quand créer une version

- À la fin d’un workflow complet.
- Lors d’une modification manuelle significative (optionnel, configurable).
- Lors d’un rollback (pour tracer l’opération).

### Numérotation

- Versions entières croissantes par chapitre (`v1`, `v2`, `v3`).
- La version `v0` est la version initiale (source importée, traduction vide).

### Interface

```typescript
interface HistoryVersion {
  id: string
  chapterId: string
  version: number
  sourceSnapshot: Paragraph[]
  translatedSnapshot: Paragraph[]
  qualityScore?: number
  createdAt: string
  triggeredBy: 'workflow' | 'manual' | 'rollback'
}
```

---

## 14.3 Stockage des snapshots

### Stratégie hybride

- **Snapshot complet** pour les versions 1, 5, 10, puis tous les 10.
- **Diff incrémental** pour les versions intermédiaires.

Cela réduit la taille tout en permettant la restauration rapide.

### Tables

```sql
CREATE TABLE history (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  source_snapshot_id TEXT,
  translated_snapshot_id TEXT,
  quality_score REAL,
  triggered_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE history_snapshots (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL,
  type TEXT NOT NULL, -- source | translated
  base_snapshot_id TEXT,
  diff TEXT, -- JSON patch si incrémental, NULL si complet
  full_data TEXT, -- JSON complet si snapshot de base
  created_at TEXT NOT NULL
);
```

### Compression

- Les snapshots JSON sont compressés avec `zlib` si la taille dépasse 10 Ko.
- Champ `is_compressed` pour indiquer la compression.

---

## 14.4 Algorithme de diff

### Diff au niveau paragraphe

```typescript
function diffParagraphs(old: Paragraph[], current: Paragraph[]): DiffResult {
  const changes: ParagraphChange[] = []
  const maxLen = Math.max(old.length, current.length)

  for (let i = 0; i < maxLen; i++) {
    const oldP = old[i]
    const newP = current[i]
    if (!oldP && newP) {
      changes.push({ type: 'added', index: i, text: newP.translatedText })
    } else if (oldP && !newP) {
      changes.push({ type: 'removed', index: i, text: oldP.translatedText })
    } else if (oldP.translatedText !== newP.translatedText) {
      changes.push({ type: 'modified', index: i, before: oldP.translatedText, after: newP.translatedText })
    }
  }

  return { changes }
}
```

### Diff au niveau ligne

- Utilisation de la librairie `diff-match-patch` pour le diff textuel.
- Affichage des ajouts/suppressions/modifications ligne par ligne.

```typescript
import DiffMatchPatch from 'diff-match-patch'

function lineDiff(before: string, after: string): DiffLine[] {
  const dmp = new DiffMatchPatch()
  const diffs = dmp.diff_main(before, after)
  dmp.diff_cleanupSemantic(diffs)
  return diffsToLines(diffs)
}
```

---

## 14.5 Rollback

### Processus

1. L’utilisateur sélectionne une version.
2. Affichage d’un aperçu du diff.
3. Confirmation.
4. Remplacement des paragraphes actuels par le snapshot traduit.
5. Création d’une nouvelle version `vN+1` avec `triggeredBy: 'rollback'`.

### Rollback partiel

- Possibilité de restaurer uniquement certains paragraphes modifiés.
- Utilisation du diff pour sélectionner les changements à appliquer.

---

## 14.6 Journal d’audit

Chaque action est tracée :

```typescript
interface AuditEntry {
  id: string
  projectId: string
  chapterId?: string
  action: string
  userId?: string
  agentId?: string
  modelId?: string
  durationMs?: number
  tokensIn?: number
  tokensOut?: number
  createdAt: string
}
```

Actions tracées :
- `project:created`, `project:opened`, `project:deleted`
- `chapter:imported`, `chapter:translated`, `chapter:exported`, `chapter:rolled_back`
- `workflow:started`, `workflow:step_completed`, `workflow:step_failed`
- `lexicon:entry_added`, `lexicon:entry_modified`

---

## 14.7 UI de l’historique

### Liste des versions

- Numéro, date, qualité, déclencheur.
- Coloration selon le déclencheur.

### Diff viewer

- Mode côte à côte ou unifié.
- Niveau paragraphe par défaut.
- Zoom au niveau ligne.
- Bouton “Restaurer cette version”.

---

## ✅ Critères d’acceptation de l’historique

- [ ] Chaque workflow terminé crée une version.
- [ ] Le diff entre deux versions est affiché au niveau paragraphe et ligne.
- [ ] Le rollback restaure une version précédente et crée une trace.
- [ ] Les snapshots sont stockés de manière compacte.
- [ ] Le journal d’audit est consultable dans la Console.
- [ ] Les modifications manuelles peuvent créer une version.

---

## 📚 Références Context7

- Librairie recommandée : `diff-match-patch` (Google).

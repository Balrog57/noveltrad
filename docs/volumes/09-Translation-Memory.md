# Volume 9 — Translation Memory

## 9.1 Objectif

La Translation Memory (TM) stocke chaque phrase/source déjà traduite et la réutilise automatiquement pour garantir la cohérence, accélérer le traitement et réduire les appels IA. Elle sert aussi de base pour le RAG (Retrieval-Augmented Generation) interne : les traductions précédentes et les entrées du lexique sont injectées dans le contexte des agents.

---

## 9.2 Stockage

Table `translation_memory` (voir Volume 6).

Champs clés :
- `source_text`
- `target_text`
- `source_language`
- `target_language`
- `usage_count`
- `last_used_at`
- `created_at`

### Segmentation

La TM travaille au niveau de la **phrase** plutôt que du paragraphe. Les paragraphes sont découpés en phrases avant stockage.

```typescript
function segmentSentences(text: string, language: string): string[] {
  // Pour le chinois : découpage par ponctuation chinoise (。！？；)
  // Pour le français/anglais : découpage par . ! ? ; suivi d’un espace
  const regex = language === 'zh'
    ? /[。！？；]+/
    : /(?<=[.!?;])\s+/
  return text.split(regex).map(s => s.trim()).filter(Boolean)
}
```

---

## 9.3 Recherche

### Exact match

```sql
SELECT target_text FROM translation_memory
WHERE project_id = ? AND source_language = ? AND target_language = ? AND source_text = ?
```

Normalisation avant recherche :
- Suppression des espaces multiples.
- Minuscules (sauf langues sans casse comme le chinois).
- Suppression des marques de ponctuation extrêmes.

### Fuzzy match

#### Algorithme en deux passes

1. **Candidats rapides** : requête SQL avec trigrammes ou sous-chaîne.
2. **Scoring précis** : Levenshtein normalisé ou embeddings.

```typescript
interface TranslationMemoryMatch {
  sourceText: string
  targetText: string
  similarity: number
  usageCount: number
}
```

#### Levenshtein normalisé

```typescript
function normalizedLevenshtein(a: string, b: string): number {
  const distance = levenshtein(a, b)
  const maxLen = Math.max(a.length, b.length)
  return maxLen === 0 ? 1 : 1 - distance / maxLen
}
```

#### Seuils

| Similarité | Usage |
|------------|-------|
| ≥ 0.95 | Remplace automatiquement la phrase source par la traduction. |
| 0.85–0.95 | Propose la traduction comme suggestion à l’agent. |
| < 0.85 | Ignoré. |

### Recherche par embeddings (RAG v1.5)

Optionnel en v1.0, activé par défaut en v1.5.

```typescript
class EmbeddingIndex {
  constructor(private db: Database, private provider: AiProvider) {}

  async index(projectId: string): Promise<void> {
    const rows = this.db.prepare(
      'SELECT id, source_text FROM translation_memory WHERE project_id = ? AND embedding IS NULL'
    ).all(projectId)

    for (const row of rows) {
      const embedding = await this.provider.embeddings([row.source_text])
      this.db.prepare('UPDATE translation_memory SET embedding = ? WHERE id = ?')
        .run(JSON.stringify(embedding[0]), row.id)
    }
  }

  async search(projectId: string, query: string, limit = 5): Promise<TranslationMemoryMatch[]> {
    const queryEmbedding = await this.provider.embeddings([query])
    const candidates = this.db.prepare(
      'SELECT id, source_text, target_text, embedding FROM translation_memory WHERE project_id = ?'
    ).all(projectId)

    return candidates
      .map(row => ({
        sourceText: row.source_text,
        targetText: row.target_text,
        similarity: cosineSimilarity(queryEmbedding[0], JSON.parse(row.embedding))
      }))
      .filter(m => m.similarity > 0.75)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit)
  }
}
```

#### Similarité cosinus

```typescript
function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0, normA = 0, normB = 0
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i]
    normA += a[i] * a[i]
    normB += b[i] * b[i]
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB))
}
```

---

## 9.4 Priorité

Ordre de priorité :
1. Exact match du projet.
2. Fuzzy match fort (> 0.95) du projet.
3. Exact match global (hors projet).
4. Fuzzy match (> 0.85) global.
5. Match par embeddings (> 0.80).

---

## 9.5 Apprentissage

- À chaque traduction validée, les phrases sont découpées et stockées.
- `usage_count` est incrémenté à chaque réutilisation.
- L’utilisateur peut importer un TMX ou un CSV.
- Lorsqu’un utilisateur modifie manuellement une traduction, la TM est mise à jour.

---

## 9.6 Engine

```typescript
class TranslationMemoryEngine {
  constructor(private db: Database, private embeddings?: EmbeddingIndex) {}

  exactMatch(text: string, projectId: string): string | null
  fuzzyMatches(text: string, projectId: string, limit?: number): TranslationMemoryMatch[]
  semanticMatches(text: string, projectId: string, limit?: number): Promise<TranslationMemoryMatch[]>
  store(source: string, target: string, projectId: string): void
  updateFromManualEdit(source: string, newTarget: string, projectId: string): void
  importTmx(filePath: string, projectId: string): Promise<number>
  exportTmx(filePath: string, projectId: string): Promise<void>
}
```

### Méthode d’aide aux agents

```typescript
function buildMemoryBlock(matches: TranslationMemoryMatch[]): string {
  if (matches.length === 0) return ''
  const lines = matches.map(m =>
    `- "${m.sourceText}" → "${m.targetText}" (similarity ${m.similarity.toFixed(2)})`
  )
  return `--- TRANSLATION MEMORY ---\n${lines.join('\n')}\n--- END TRANSLATION MEMORY ---`
}
```

---

## 9.7 Format TMX

### Import

```typescript
async function importTmx(filePath: string, projectId: string): Promise<number> {
  const xml = await readFile(filePath, 'utf-8')
  // Parser avec fast-xml-parser ou xml2js
  // Insérer chaque <tu> dans translation_memory
}
```

### Export

```typescript
async function exportTmx(filePath: string, projectId: string): Promise<void> {
  const rows = this.db.prepare('SELECT * FROM translation_memory WHERE project_id = ?').all(projectId)
  // Générer XML TMX 1.4
  // Écrire dans filePath
}
```

---

## 9.8 RAG interne

La TM et le lexique forment la base de connaissances du RAG.

```text
Avant la traduction d’un chapitre :
1. Récupérer les entrées du lexique pertinentes (termes présents dans le texte).
2. Récupérer les fuzzy/semantic matches du texte source.
3. Injecter les deux blocs dans le prompt de traduction.
```

Voir Volume 25 pour le format `{memoryBlock}` et `{lexiconBlock}`.

---

## ✅ Critères d’acceptation de la TM

- [ ] Un exact match retourne la traduction sans appel IA.
- [ ] Un fuzzy match fort fournit un candidat au traducteur/agent.
- [ ] Les nouvelles traductions validées enrichissent la TM.
- [ ] L’import/export TMX fonctionne.
- [ ] La priorité projet est respectée avant la mémoire globale.
- [ ] Les embeddings optionnels améliorent la recherche sémantique.
- [ ] L’indexation des embeddings peut être relancée manuellement.

---

## 📚 Références Context7

- `/ollama/ollama-js` — API embeddings via Ollama.

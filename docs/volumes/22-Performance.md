# Volume 22 — Performances

## 22.1 Cache

| Type | Emplacement | Invalidation | Durée de vie |
|------|-------------|--------------|--------------|
| Réponses IA | `cache/ai/` | TTL configurable (défaut 7 jours) | Fichier texte + hash |
| Embeddings | `cache/embeddings/` | Sur changement modèle | SQLite |
| Parse source | `cache/parse/` | Sur changement fichier | Hash du fichier |
| TM | SQLite | Immédiat | Persistant |
| Export | `cache/export/` | Sur changement chapitre | TTL 1 jour |

### Cache IA

```typescript
interface AiCacheEntry {
  key: string // hash du prompt + modèle + température
  response: string
  createdAt: string
  ttlDays: number
}

function getCachedResponse(key: string): string | null {
  const entry = db.prepare('SELECT response, created_at FROM ai_cache WHERE key = ?').get(key)
  if (!entry) return null
  const ageDays = (Date.now() - new Date(entry.created_at).getTime()) / 86400000
  if (ageDays > entry.ttlDays) {
    db.prepare('DELETE FROM ai_cache WHERE key = ?').run(key)
    return null
  }
  return entry.response
}
```

---

## 22.2 Parallélisme

### Concurrence Ollama

- Un seul job IA actif par défaut sur Ollama local pour éviter la surcharge GPU/CPU.
- Configurable via `maxConcurrentJobs` (défaut 1).

### Worker threads

- Agents CPU-bound (parsing, cohérence, export) tournent dans `Worker` threads.
- Communication via `parentPort.postMessage`.
- Pas de partage d’objets complexes ; passage de messages JSON.

```typescript
const worker = new Worker(path.join(__dirname, 'AgentWorker.js'))
worker.postMessage({ stage: 'consistency', input })
worker.once('message', (output) => resolve(output))
```

### Promise.all

- Appels indépendants groupés : extraction de chapitres, vérifications lexique, etc.

---

## 22.3 Streaming

- Les téléchargements de modèles Ollama sont streamés.
- Les fichiers texte sont lus par chunks.
- Les logs sont écrits de manière asynchrone.

---

## 22.4 Optimisation mémoire

### Traitement paragraphe par paragraphe

- Les gros chapitres sont découpés et traités par batch.
- Taille maximale d’un batch : 4000 tokens (configurable).

### Pas de chargement entier d’un EPUB en mémoire

- Lecture via @likecoin/epub-ts/node par section (librairie à valider avant implémentation ; alternative : pubjs ou dm-zip + cheerio).
- Extraction incrémentale des chapitres.

### Nettoyage des caches

- Limite de taille : 1 Go par défaut.
- Suppression LRU quand la limite est atteinte.

---

## 22.5 Benchmarks cibles

| Opération | Cible | Méthode de test |
|-----------|-------|-----------------|
| Parsing 10 000 mots | < 1 s | Fichier de référence |
| Traduction d’un chapitre court | < 5 min | Chapitre 2 000 mots, modèle 7B |
| Export Markdown | < 1 s | Chapitre 5 000 mots |
| Export DOCX | < 3 s | Chapitre 5 000 mots |
| Export EPUB | < 5 s | Roman 50 000 mots |
| Ouverture projet | < 2 s | Projet 100 chapitres |

---

## 22.6 Profiling

### Collecte automatique

- Temps par étape workflow.
- Tokens consommés par appel IA.
- Mémoire utilisée par le main process.
- Taille des fichiers parsés.

### Export CSV

```typescript
interface PerformanceReport {
  jobId: string
  stage: string
  durationMs: number
  tokensIn: number
  tokensOut: number
  memoryPeakMB: number
}
```

### UI

- Onglet “Performances” dans Paramètres (v2.0).
- Affichage temps moyen par étape.

---

## 22.7 Gestion des OOM

### Limites

- Taille max d’un fichier source : 50 Mo (configurable).
- Nombre max de paragraphes en mémoire : 10 000.
- Taille max d’un batch IA : 8 000 tokens.

### Stratégie

- Si une erreur OOM est détectée, réduire la taille du batch et relancer.
- Libérer les caches temporaires après chaque job.

---

## ✅ Critères d’acceptation performances

- [ ] Les caches sont persistés et invalidés correctement.
- [ ] Le workflow local Ollama ne surcharge pas la machine.
- [ ] Les fichiers volumineux sont traités sans OOM.
- [ ] Le temps de parsing reste sous 1 s pour 10 000 mots.
- [ ] L’UI reste réactive pendant un workflow.
- [ ] Les benchmarks cibles sont mesurés et affichés.
- [ ] Les performances par étape sont collectées et exportables.

---

## 📚 Références Context7

- `/websites/node_js` — Worker threads, streams, `fs/promises`.

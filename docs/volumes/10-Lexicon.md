# Volume 10 — Lexique

## 10.1 Objectif

Le lexique garantit la cohérence des termes propres à l’univers du roman. C’est le cœur de la qualité de traduction. Il doit être facile à enrichir, capable de détecter automatiquement les termes candidats, et strict sur les termes verrouillés.

---

## 10.2 Catégories

| Catégorie | Exemple source | Exemple traduction |
|-----------|----------------|--------------------|
| Personnage | Lin Ming | Lin Ming |
| Secte | Heavenly Palace | Palais Céleste |
| Objet | Spirit Stones | Pierres Spirituelles |
| Compétence | Dragon Fist | Poing du Dragon |
| Cultivation | Qi Condensation | Condensation du Qi |
| Lieu | Azure Sky Continent | Continent du Ciel Azur |
| Titre | Sword Saint | Saint de l’Épée |

---

## 10.3 Entité

```typescript
interface LexiconEntry {
  id: string
  term: string
  translation: string
  category: LexiconCategory
  gender?: 'male' | 'female' | 'neutral' | 'unknown'
  aliases: string[]
  description?: string
  notes?: string
  pronunciation?: string
  priority: number
  locked: boolean
}
```

### Règles métier

- `term` est unique par projet (après normalisation).
- `translation` est la forme canonique en langue cible.
- `aliases` permettent de résoudre des variantes vers l’entrée principale.
- `locked=true` signifie que l’agent Lexique doit corriger toute traduction alternative.
- `priority` détermine l’ordre d’application quand deux entrées entrent en conflit.

---

## 10.4 Alias

Un personnage peut avoir plusieurs noms : “Lin Ming”, “Young Master Lin”, “That boy”. Chaque alias pointe vers l’entrée principale.

### Normalisation des alias

```typescript
function normalizeTerm(term: string): string {
  return term.toLowerCase().trim().replace(/\s+/g, ' ')
}
```

---

## 10.5 Verrouillage

- `locked = true` : le terme ne doit jamais être traduit autrement.
- L’agent Lexicon vérifie d’abord les entrées verrouillées.
- Une substitution sur un terme verrouillé génère un warning de sévérité `high`.

## 10.5b Termes interdits (forbidden)

Inspiré de [NovelTrans](https://github.com/YuBing-link/noveltrans) et [Glossarion](https://github.com/Shirochi-stack/Glossarion).

- Champ optionnel `forbidden: string[]` sur une entrée lexicale.
- Liste les traductions qu’il est interdit d’utiliser pour ce terme.
- L’agent Lexicon signale un warning `high` si une forme interdite apparaît dans le texte traduit.
- Exemple : le personnage "Lin Ming" peut avoir `forbidden: ["Lin Min", "Linming"]` pour forcer la forme canonique.

---

## 10.6 Prononciation

Champ optionnel `pronunciation` pour noter la romanisation (pinyin, romaji, etc.).

---

## 10.7 Import / Export

Formats supportés :
- CSV
- JSON
- TSV

Exemple JSON :

```json
[
  {
    "term": "Lin Ming",
    "translation": "Lin Ming",
    "category": "character",
    "aliases": ["Young Master Lin"],
    "locked": true
  }
]
```

---

## 10.8 Extraction automatique de termes candidats

### Objectif

Proposer à l’utilisateur des termes récurrents dans le texte source qui n’existent pas encore dans le lexique.

### Algorithme

```typescript
function extractCandidateTerms(text: string, language: string): CandidateTerm[] {
  const candidates: Map<string, number> = new Map()

  // Pour le chinois : extraire les groupes de 2 à 6 caractères
  if (language === 'zh') {
    for (let len = 2; len <= 6; len++) {
      for (let i = 0; i <= text.length - len; i++) {
        const term = text.slice(i, i + len)
        if (isCommonTerm(term)) continue
        candidates.set(term, (candidates.get(term) || 0) + 1)
      }
    }
  }

  // Pour le français/anglais : extraire les n-grams de mots
  else {
    const words = tokenizeWords(text)
    for (let len = 1; len <= 4; len++) {
      for (let i = 0; i <= words.length - len; i++) {
        const term = words.slice(i, i + len).join(' ')
        if (isCommonTerm(term)) continue
        candidates.set(term, (candidates.get(term) || 0) + 1)
      }
    }
  }

  return Array.from(candidates.entries())
    .filter(([_, count]) => count >= 3)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 50)
    .map(([term, count]) => ({ term, occurrences: count }))
}
```

### Filtrage

- Supprimer les termes déjà dans le lexique.
- Supprimer les termes communs (stop-words, nombres, ponctuation).
- Privilégier les termes avec une capitalisation inhabituelle en anglais.
- Pour le chinois, privilégier les termes avec des caractères récurrents dans un rayon court.

### IA comme second filtre

```text
You are a literary term extractor. Given the following candidate terms from a {sourceLanguage} web novel,
identify which ones are likely to be proper nouns (characters, places, sects, skills, items, techniques).
Return a JSON array of objects: { "term": "...", "category": "character|place|sect|skill|item|other" }.
Candidates: {candidates}
```

---

## 10.9 Détection des conflits

### Types de conflits

| Conflit | Exemple | Résolution |
|---------|---------|------------|
| Même terme, traductions différentes | “Lin Ming” → “Lin Ming” et “Lin Min” | Garder la plus récente ou demander à l’utilisateur. |
| Alias en conflit avec terme principal | Alias “Lin” pointe vers Lin Ming, mais un autre personnage s’appelle Lin Feng | Refuser la création ou avertir. |
| Terme inclus dans un autre | “Azure Sky Continent” et “Azure Sky” | Appliquer le terme le plus long d’abord. |

### Algorithme de détection

```typescript
function findConflicts(entries: LexiconEntry[]): LexiconConflict[] {
  const conflicts: LexiconConflict[] = []
  for (let i = 0; i < entries.length; i++) {
    for (let j = i + 1; j < entries.length; j++) {
      const a = normalizeTerm(entries[i].term)
      const b = normalizeTerm(entries[j].term)
      if (a === b) {
        conflicts.push({ type: 'duplicate_term', entries: [entries[i], entries[j]] })
      }
      if (a.includes(b) || b.includes(a)) {
        conflicts.push({ type: 'overlap', entries: [entries[i], entries[j]] })
      }
    }
  }
  return conflicts
}
```

---

## 10.10 Suggestions IA

L’agent Lexique peut demander au modèle de suggérer des traductions pour un terme inconnu.

```text
You are a translator of {sourceLanguage} web novels into {targetLanguage}.
Given the term "{term}" and its context below, suggest a natural translation.

Context:
{context}

Return JSON:
{
  "translation": "...",
  "category": "character|place|sect|skill|item|other",
  "explanation": "..."
}
```

---

## 10.11 LexiconEngine

```typescript
class LexiconEngine {
  constructor(private repository: LexiconRepository)

  apply(text: string, projectId: string): LexiconApplyResult
  detectUnknownTerms(text: string, projectId: string): CandidateTerm[]
  suggestTranslation(term: string, context: string, projectId: string): Promise<LexiconSuggestion>
  findConflicts(projectId: string): LexiconConflict[]
  import(path: string, projectId: string, format: 'csv' | 'json'): Promise<number>
  export(path: string, projectId: string, format: 'csv' | 'json'): Promise<void>
}
```

### Méthode `apply`

1. Trie les entrées par longueur décroissante (pour gérer les inclusions).
2. Pour chaque entrée, recherche toutes les occurrences dans le texte.
3. Applique la substitution en préservant la casse contextuelle.
4. Retourne le texte corrigé + la liste des substitutions.

```typescript
interface LexiconApplyResult {
  text: string
  substitutions: Substitution[]
}

interface Substitution {
  before: string
  after: string
  start: number
  end: number
  locked: boolean
}
```

---

## ✅ Critères d’acceptation du lexique

- [ ] CRUD complet via UI.
- [ ] Les alias sont résolus vers l’entrée principale.
- [ ] Un terme verrouillé n’est jamais modifié par les agents.
- [ ] Import/export CSV et JSON fonctionnent.
- [ ] L’agent Lexique signale les substitutions effectuées.
- [ ] L’extraction automatique propose des candidats pertinents.
- [ ] Les conflits sont détectés et signalés.
- [ ] Les suggestions IA respectent le contexte.

---

## 📚 Références Context7

- `/ollama/ollama-js` — Appels IA pour suggestions et extraction.

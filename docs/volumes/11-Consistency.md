# Volume 11 — Vérification de cohérence

## 11.1 Objectif

Comparatif systématique entre le texte source et le texte traduit pour détecter tout écart structurel ou sémantique. L’agent Cohérence fournit un rapport exploitable par l’agent QA et par l’utilisateur.

---

## 11.2 Métriques comparées

| Métrique | Source | Traduction | Tolérance |
|----------|--------|------------|-----------|
| Paragraphes | 254 | 253 | 0 — tout écart est un warning |
| Phrases | 1 210 | 1 205 | ±2 % |
| Dialogues | 38 | 36 | 0 |
| Caractères/mots | 15 432 | 11 200 | ±30 % selon paire de langues |
| Noms propres (lexique) | 65 occ. | 64 occ. | 0 si verrouillé |
| Chiffres | 12 | 12 | 0 |
| Balises Markdown | identique | identique | 0 |
| Balises HTML | identique | identique | 0 |

---

## 11.3 Algorithmes de comparaison

### Paragraphes

```typescript
function compareParagraphs(source: string[], target: string[]): Metric {
  const diff = source.length - target.length
  return {
    name: 'paragraphs',
    source: source.length,
    target: target.length,
    ok: diff === 0,
    warnings: diff !== 0
      ? [{ severity: 'high', message: `${Math.abs(diff)} paragraphe(s) ${diff > 0 ? 'manquant(s)' : 'en trop'}` }]
      : []
  }
}
```

### Phrases

```typescript
function compareSentences(source: string[], target: string[], langPair: LangPair): Metric {
  const sourceCount = countSentences(join(source), langPair.source)
  const targetCount = countSentences(join(target), langPair.target)
  const ratio = targetCount / sourceCount
  const ok = ratio >= 0.98 && ratio <= 1.02

  return {
    name: 'sentences',
    source: sourceCount,
    target: targetCount,
    ok,
    warnings: ok ? [] : [{ severity: 'medium', message: `Écart de ${Math.round((1 - ratio) * 100)} % de phrases` }]
  }
}
```

### Dialogues

```typescript
function compareDialogues(source: string[], target: string[], langPair: LangPair): Metric {
  const sourceDialogues = countDialogues(join(source), langPair.source)
  const targetDialogues = countDialogues(join(target), langPair.target)
  const diff = sourceDialogues - targetDialogues

  return {
    name: 'dialogues',
    source: sourceDialogues,
    target: targetDialogues,
    ok: diff === 0,
    warnings: diff !== 0
      ? [{ severity: 'medium', message: `${Math.abs(diff)} réplique(s) de dialogue ${diff > 0 ? 'manquante(s)' : 'en trop'}` }]
      : []
  }
}
```

### Nombres, dates, unités

```typescript
function compareNumbers(source: string, target: string): Metric {
  const sourceNumbers = extractNumbers(source)
  const targetNumbers = extractNumbers(target)
  const missing = sourceNumbers.filter(n => !targetNumbers.includes(n))
  const extra = targetNumbers.filter(n => !sourceNumbers.includes(n))

  return {
    name: 'numbers',
    source: sourceNumbers.length,
    target: targetNumbers.length,
    ok: missing.length === 0 && extra.length === 0,
    warnings: [
      ...missing.map(n => ({ severity: 'high', message: `Nombre manquant : ${n}` })),
      ...extra.map(n => ({ severity: 'medium', message: `Nombre ajouté : ${n}` }))
    ]
  }
}
```

### Noms propres du lexique

```typescript
function compareNamedEntities(source: string, target: string, lexicon: LexiconEntry[]): Metric {
  const warnings: Warning[] = []

  for (const entry of lexicon) {
    const sourceCount = countOccurrences(source, [entry.term, ...entry.aliases])
    const targetCount = countOccurrences(target, [entry.translation, ...entry.aliases.map(a => translateAlias(a, entry))])
    if (entry.locked && sourceCount !== targetCount) {
      warnings.push({ severity: 'high', message: `${entry.term} : ${sourceCount} occurrence(s) source, ${targetCount} cible` })
    }
  }

  return { name: 'named_entities', source: 0, target: 0, ok: warnings.length === 0, warnings }
}
```

### Balises Markdown / HTML

```typescript
function compareMarkup(source: string, target: string): Metric {
  const sourceTags = extractTags(source)
  const targetTags = extractTags(target)
  const diff = diffTags(sourceTags, targetTags)

  return {
    name: 'markup',
    source: sourceTags.length,
    target: targetTags.length,
    ok: diff.length === 0,
    warnings: diff.map(d => ({ severity: 'medium', message: d }))
  }
}
```

---

## 11.4 Gestion des faux positifs

### Tolérances configurables

```typescript
interface ConsistencyTolerance {
  sentenceRatioMin: number
  sentenceRatioMax: number
  lengthRatioMin: number
  lengthRatioMax: number
  ignoreNumbersInDialogues: boolean
  ignorePunctuationMismatch: boolean
}
```

### Exemples de faux positifs

| Situation | Faux positif | Solution |
|-----------|--------------|----------|
| Traduction plus concise en japonais → français | Écart de caractères important | Tolérance par paire de langues. |
| Un chapitre sans dialogue | `dialogues = 0` | Ne pas générer de warning si source = cible = 0. |
| Nombre transformé en tournure littéraire | Nombre manquant | Tolérance si le nombre est proche textuellement. |
| Style Markdown différent (`**` vs `_`) | Warning balise | Normaliser les balises équivalentes. |

### Calibration par paire de langues

```typescript
const defaultTolerances: Record<LangPair, ConsistencyTolerance> = {
  'zh-fr': { sentenceRatioMin: 0.95, sentenceRatioMax: 1.05, lengthRatioMin: 0.5, lengthRatioMax: 1.5, ignoreNumbersInDialogues: false, ignorePunctuationMismatch: true },
  'ja-fr': { sentenceRatioMin: 0.95, sentenceRatioMax: 1.05, lengthRatioMin: 0.6, lengthRatioMax: 1.4, ignoreNumbersInDialogues: false, ignorePunctuationMismatch: true },
  'ko-fr': { sentenceRatioMin: 0.95, sentenceRatioMax: 1.05, lengthRatioMin: 0.55, lengthRatioMax: 1.45, ignoreNumbersInDialogues: false, ignorePunctuationMismatch: true },
  'en-fr': { sentenceRatioMin: 0.98, sentenceRatioMax: 1.02, lengthRatioMin: 0.8, lengthRatioMax: 1.2, ignoreNumbersInDialogues: false, ignorePunctuationMismatch: false },
  'zh-en': { sentenceRatioMin: 0.95, sentenceRatioMax: 1.05, lengthRatioMin: 0.5, lengthRatioMax: 1.5, ignoreNumbersInDialogues: false, ignorePunctuationMismatch: true },
  'ja-en': { sentenceRatioMin: 0.95, sentenceRatioMax: 1.05, lengthRatioMin: 0.6, lengthRatioMax: 1.4, ignoreNumbersInDialogues: false, ignorePunctuationMismatch: true }
}
```

> Les ratios de longueur tiennent compte de la différence de densité informationnelle : le chinois/japonais compact nécessite généralement une expansion en français/anglais, tandis que l’anglais → français reste plus proche.

---

## 11.5 Score global

```typescript
interface ConsistencyReport {
  metrics: Metric[]
  warnings: Warning[]
  globalScore: number // 0-100
}
```

### Formule

1. Chaque métrique reçoit un score 0–100.
2. Score global = moyenne pondérée.
3. Pénalités :
   - Écart de paragraphe : plafonne à 50.
   - Nom propre verrouillé manquant : plafonne à 70.
   - Nombre manquant : plafonne à 80.

```typescript
function computeGlobalScore(metrics: Metric[]): number {
  const weights = {
    paragraphs: 30,
    sentences: 15,
    dialogues: 15,
    length: 10,
    named_entities: 15,
    numbers: 10,
    markup: 5
  }

  let score = weightedAverage(metrics, weights)
  if (hasIssue(metrics, 'paragraphs')) score = Math.min(score, 50)
  if (hasIssue(metrics, 'named_entities', 'high')) score = Math.min(score, 70)
  if (hasIssue(metrics, 'numbers', 'high')) score = Math.min(score, 80)

  return Math.round(score)
}
```

---

## 11.6 Impact sur le workflow

Le `ConsistencyReport` détermine si le workflow continue ou se met en pause :

| Situation | Comportement | Action utilisateur |
|---|---|---|
| `globalScore` ≥ 90 et aucun warning `high` | Passe à l’étape `lexicon`. | Aucune. |
| Warning `high` (paragraphe manquant, nom propre locked manquant, nombre manquant) | Workflow en pause. | Corriger le lexique, relancer `retryStep`, ou forcer la continuation avec un avertissement. |
| Warning `medium` uniquement (dialogues, phrases, markup) | Continue avec warning visible ; score transmis au QA. | Peut corriger manuellement ou ignorer si toléré. |
| `globalScore` < 70 | Workflow en pause avant l’étape `lexicon`. | Relancer `translate` ou ajuster le lexique. |

### Règles de décision

```typescript
function decideNextStep(report: ConsistencyReport): 'continue' | 'pause' {
  const hasHigh = report.warnings.some(w => w.severity === 'high')
  const hasMedium = report.warnings.some(w => w.severity === 'medium')

  if (hasHigh) return 'pause'
  if (report.globalScore < 70) return 'pause'
  if (hasMedium) return 'continue' // avec flag d’avertissement
  return 'continue'
}
```

---

## 11.7 UI du rapport

```text
Avant
254 paragraphes
15 432 caractères
38 dialogues
Xiao Yan : 65 occurrences

Après
253 paragraphes  ⚠ Un paragraphe perdu
11 200 caractères
36 dialogues     ⚠ 2 dialogues manquants
Xiao Yan : 64 occurrences ⚠ Nom propre manquant
```

---

## ✅ Critères d’acceptation de la cohérence

- [ ] Un test unitaire calcule les 7 métriques (paragraphs, sentences, dialogues, length, named_entities, numbers, markup) sur un chapitre de référence.
- [ ] Un écart de paragraphe génère un warning `high` et plafonne le `globalScore` à 50.
- [ ] Un écart de dialogue génère un warning `medium` (ou `high` si l’utilisateur a configuré `dialogueErrorAsHigh`).
- [ ] Les noms propres `locked` du lexique sont comptés en source et en cible ; une différence génère un warning `high`.
- [ ] Le `ConsistencyReport` (score + warnings) est persisté dans `job_steps.output_snapshot` et `job_steps.score`.
- [ ] Les tolérances `zh-fr`, `ja-fr`, `ko-fr`, `en-fr`, `zh-en`, `ja-en` sont configurables via `settings`.
- [ ] Les faux positifs courants (sans dialogue, nombre transformé en tournure, balises équivalentes) sont filtrés.
- [ ] Un warning `high` met le workflow en pause ; un warning `medium` laisse le workflow continuer avec un flag visible.

---

## 📚 Références Context7

- Aucune librairie externe requise ; implémentation locale avec regex et algorithmes de distance.

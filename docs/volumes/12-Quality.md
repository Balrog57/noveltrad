# Volume 12 — Contrôle qualité

## 12.1 Objectif

Attribuer une note objective à une traduction selon plusieurs dimensions, et permettre de décider si le chapitre est acceptable ou doit être relancé.

---

## 12.2 Dimensions

| Dimension | Poids | Description | Méthode |
|-----------|-------|-------------|---------|
| Cohérence | 25 % | Préservation du sens et de la structure | Rapport agent Cohérence |
| Grammaire | 15 % | Accords, ponctuation, conjugaison | Règles locales + IA |
| Fluidité | 20 % | Lisibilité naturelle | IA |
| Style | 15 % | Adaptation au genre, suppression du litéralisme | IA |
| Lexique | 15 % | Respect du lexique | Règles locales |
| Hallucinations | 5 % | Absence d’ajouts non justifiés | IA |
| Longueur | 3 % | Proportionnalité source/cible | Règles locales |
| Dialogue | 2 % | Qualité des répliques | IA |

---

## 12.3 Méthodes de scoring

### Règles locales (rapides, sans IA)

#### Cohérence

- Score = `ConsistencyReport.globalScore`.

#### Grammaire locale

- Regex pour les fautes fréquentes en français :
  - `il sont` → `il est`
  - `j'ai allé` → `je suis allé`
  - espace avant `?`, `!`, `:` manquante.
  - Guillemets anglais `"` au lieu de `« »`.

```typescript
const frenchGrammarRules = [
  { name: 'accord_il_est', pattern: /\bil\s+sont\b/gi, penalty: 10 },
  { name: 'espace_ponctuation_haute', pattern: /[a-zA-ZÀ-ÿ][?!:;]/g, penalty: 2 },
  { name: 'guillemets_anglais', pattern: /"[^"]+"/g, penalty: 1 }
]
```

#### Lexique

- Compte les substitutions effectuées par l’agent Lexique.
- Pénalise les termes verrouillés non appliqués.

#### Longueur

- Ratio caractères source/cible.
- Tolérance par paire de langues (même logique que Volume 11).

### IA (lente, précise)

- Fluidité, Style, Hallucinations, Dialogue sont évalués par un appel LLM avec prompt structuré.
- Le modèle retourne un JSON conforme à un schéma strict.

```typescript
interface QualityResult {
  consistency: number
  grammar: number
  fluidity: number
  style: number
  lexicon: number
  hallucination: number
  length: number
  dialogue: number
  globalScore: number
  comments: string
}
```

---

## 12.4 Prompt QA

Le prompt complet est dans le Volume 25 (Agent 8 — QA). Voici la version intégrée utilisée par le système :

```text
You are a quality evaluator for literary translations.
Rate the following translation on the 8 dimensions below.
Use a strict 0-100 scale. Provide a brief justification for each score.

Dimensions:
- consistency (faithfulness to source, no omissions)
- grammar (correct {targetLanguage} grammar and spelling)
- fluency (natural reading flow)
- style (appropriate tone, no literalisms)
- lexicon (respect of terminology)
- hallucination (no unjustified additions)
- length (reasonable proportion to source)
- dialogue (natural character speech)

Source:
{sourceText}

Translation:
{translatedText}

Return only the JSON object. Do not wrap it in Markdown code fences. Do not add any text before or after the JSON.

Return a JSON object:
{
  "consistency": 98,
  "grammar": 96,
  "fluency": 94,
  "style": 90,
  "lexicon": 100,
  "hallucination": 95,
  "length": 88,
  "dialogue": 92,
  "globalScore": 96,
  "comments": "Minor fluency issues in dialogue."
}
```

### Consignes supplémentaires

- Évaluer chaque dimension sur une échelle stricte 0–100.
- Justifier brièvement chaque score dans le champ `comments` global.
- Ne pas être indulgent : une traduction littérale mérite un score `style` faible.
- Si une dimension n’est pas applicable (pas de dialogue), noter `100` et l’indiquer dans `comments`.

### Schéma JSON

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["consistency", "grammar", "fluency", "style", "lexicon", "hallucination", "length", "dialogue", "globalScore", "comments"],
  "properties": {
    "consistency": { "type": "number", "minimum": 0, "maximum": 100 },
    "grammar": { "type": "number", "minimum": 0, "maximum": 100 },
    "fluency": { "type": "number", "minimum": 0, "maximum": 100 },
    "style": { "type": "number", "minimum": 0, "maximum": 100 },
    "lexicon": { "type": "number", "minimum": 0, "maximum": 100 },
    "hallucination": { "type": "number", "minimum": 0, "maximum": 100 },
    "length": { "type": "number", "minimum": 0, "maximum": 100 },
    "dialogue": { "type": "number", "minimum": 0, "maximum": 100 },
    "globalScore": { "type": "number", "minimum": 0, "maximum": 100 },
    "comments": { "type": "string", "maxLength": 500 }
  },
  "additionalProperties": false
}
```

---

### Mapping dimensions ↔ agents

| Dimension | Agent responsable | Source du score |
|---|---|---|
| Cohérence | `ConsistencyAgent` (Volume 11) | `ConsistencyReport.globalScore` |
| Grammaire | `GrammarAgent` + règles locales | Nombre et poids des corrections détectées |
| Fluidité | `StyleAgent` / `PolishAgent` | Évaluation IA sur le texte final |
| Style | `StyleAgent` / `PolishAgent` | Évaluation IA sur le ton et le littéralisme |
| Lexique | `LexiconAgent` | Taux de substitutions validées / termes locked respectés |
| Hallucinations | `ConsistencyAgent` + `QAAgent` | Entités nommées inventées détectées localement + score IA |
| Longueur | `ConsistencyAgent` | Ratio caractères source/cible |
| Dialogue | `QAAgent` | Évaluation IA des répliques |

---

## 12.5 Calibration

### Problème

Les modèles ont des biais de notation. Certains modèles notent systématiquement 90+, d’autres sont plus sévères. La calibration garantit que le score NovelTrad est comparable d’un modèle à l’autre et aligné sur le jugement humain.

### Jeu de référence

Constituer un corpus de **20 chapitres** couvrant :

- 5 chapitres de web novel chinoise (xianxia/xuanhuan).
- 5 chapitres de web novel japonaise / coréenne.
- 5 chapitres de fan-fiction.
- 5 extraits d’œuvres du domaine public en anglais traduites en français.

Chaque chapitre est annoté manuellement sur les 8 dimensions (0–100) par au moins 2 relecteurs. Les scores médians forment les **scores cibles**.

### Méthode d’ajustement

1. Lancer l’agent QA sur chaque chapitre du jeu de référence avec le modèle courant.
2. Pour chaque dimension, calculer la régression linéaire entre scores IA (`x`) et scores cibles (`y`) : `y = slope * x + offset`.
3. Stocker les coefficients `{ slope, offset }` par `(model, dimension)` dans la table `model_calibrations`.
4. Appliquer la calibration à chaque score brut avant le calcul du `globalScore`.

```typescript
interface ModelCalibration {
  model: string
  dimension: string
  slope: number
  offset: number
  sampleCount: number
  updatedAt: string
}

function calibrateScore(raw: number, model: string, dimension: string): number {
  const calibration = loadCalibration(model, dimension)
  return Math.min(100, Math.max(0, Math.round(raw * calibration.slope + calibration.offset)))
}
```

### Versionnement

- Recalibrer obligatoirement quand le modèle qualité change (`qwen3.5:9b` → autre).
- Recalibrer périodiquement tous les 100 chapitres traduits pour détecter un drift.
- Conserver l’historique des calibrations pour permettre le rollback.

---

## 12.6 Détection d’hallucination

### Approche locale

- Comparer les entités nommées du source et de la cible.
- Vérifier qu’aucun nom propre n’a été inventé.
- Vérifier qu’aucun chapitre ou personnage n’est mentionné sans être dans le source.

### Approche IA

```text
Identify any unjustified additions in the translation that do not appear in the source.
Return a JSON array: [{ "added_text": "...", "severity": "low|medium|high" }].
```

---

## 12.7 Seuils

| Seuil | Action |
|-------|--------|
| ≥ 90 | Acceptable, passe à Export. |
| 70–89 | Warning, proposition de relance de l’étape la plus faible. |
| < 70 | Blocage, workflow en pause. |

Le seuil est configurable dans Paramètres → Workflow.

---

## 12.8 UI du score

```text
Qualité
96 / 100

✓ Cohérence     98 %
✓ Grammaire     96 %
✓ Fluidité      94 %
✓ Style         90 %
✓ Lexique      100 %
✓ Hallucinations 95 %
✓ Longueur      88 %
✓ Dialogue      92 %
```

---

## ✅ Critères d’acceptation qualité

- [ ] L’agent QA retourne un JSON valide contre le schéma de la section 12.4.
- [ ] Les 8 dimensions (`consistency`, `grammar`, `fluency`, `style`, `lexicon`, `hallucination`, `length`, `dialogue`) sont présentes et dans l’intervalle 0–100.
- [ ] Le `globalScore` est calculé avec les poids de la section 12.2 et arrondi à l’entier.
- [ ] Le seuil de rejet est configurable dans Paramètres → Workflow (défaut < 70 = pause, 70–89 = warning, ≥ 90 = export).
- [ ] Un `globalScore` < 70 met automatiquement le workflow en pause et propose de relancer l’étape la plus faible.
- [ ] Le scoring grammaire local détecte au moins 5 fautes fréquentes en français avec pénalité.
- [ ] La calibration est stockée dans `model_calibrations` et appliquée avant le calcul du score global.
- [ ] Le jeu de référence contient 20 chapitres annotés manuellement couvrant 4 profils de source.
- [ ] Les hallucinations sont détectées localement (entités nommées) et par IA (prompt QA).

---

## 📚 Références Context7

- `/ollama/ollama-js` — Appels IA pour scoring.

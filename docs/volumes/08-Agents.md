# Volume 8 — Les agents

## 8.1 Contrat commun

Chaque agent est une classe autonome qui implémente l’interface `Agent`. Le moteur de workflow ne connaît que cette interface : il peut donc injecter des agents natifs ou des agents provenant de plugins.

```typescript
interface Agent {
  readonly id: string
  readonly name: string
  readonly stage: WorkflowStage
  readonly inputSchema: JSONSchema
  readonly outputSchema: JSONSchema
  readonly defaultModel?: string

  execute(input: AgentInput, context: AgentContext): Promise<AgentOutput>
}

interface AgentInput {
  projectId: string
  chapterId?: string
  paragraphs?: Paragraph[]
  text?: string
  previousOutput?: string
  lexicon?: LexiconEntry[]
  memoryMatches?: TranslationMemoryMatch[]
  consistencyReport?: ConsistencyReport
  qualityReport?: QualityReport
  options?: Record<string, unknown>
}

interface AgentContext {
  jobId: string
  stepId: string
  projectId: string
  sourceLanguage: string
  targetLanguage: string
  aiRouter: AiRouter
  lexiconEngine: LexiconEngine
  tmEngine: TranslationMemoryEngine
  logger: Logger
  emitProgress: (percent: number, message: string) => void
}

interface AgentOutput {
  text?: string
  paragraphs?: Paragraph[]
  report?: Report
  score?: number
  substitutions?: Substitution[]
  corrections?: Correction[]
  metadata?: Record<string, unknown>
}
```

## 8.2 Agent 0 — Découpage (Split)

**Mission.** Découper un fichier source en paragraphes numérotés.

**Entrées.** `text` (contenu brut du chapitre).

**Sorties.** `paragraphs` avec `indexInChapter`, `sourceText`, `translatedText` vide.

**Règles.**
- Séparer par doubles sauts de ligne.
- Préserver les balises Markdown/HTML.
- Ne jamais fusionner deux dialogues distincts.

## 8.3 Agent 1 — Pré-traduction

**Mission.** Produire une traduction littérale rapide utilisée comme brouillon.

**Entrées.** `paragraphs` source.

**Sorties.** `paragraphs` avec `preTranslatedText`.

**Prompt.** Voir Volume 25 (`prompts/pre-translate.system.txt`).

**Validation.**
- Aucun paragraphe perdu.
- Aucun paragraphe vide inattendu.
- Nombre de lignes == nombre de paragraphes source.

**Modèle recommandé.** Petit modèle rapide Ollama (`qwen3.5:4b`, `llama3.2:3b`).

## 8.4 Agent 2 — Traduction IA

**Mission.** Produire une traduction naturelle, fidèle et fluide.

**Entrées.** `paragraphs` source + `preTranslatedText` optionnel + lexique + mémoire.

**Sorties.** `paragraphs` avec `translatedText`.

**Prompt.** Voir Volume 25 (`prompts/translate.system.txt`).

**Validation.**
- Nombre de paragraphes inchangé.
- Les termes verrouillés du lexique sont présents.
- Les balises Markdown/HTML sont préservées.

**Modèle recommandé.** `qwen3.5:9b` ou `deepseek-r1:7b`.

## 8.5 Agent 3 — Cohérence

**Mission.** Comparer source et traduction pour détecter écarts et incohérences.

**Entrées.** `paragraphs` source + traduits.

**Sorties.** `report` de type `ConsistencyReport`.

**Contrôles.**
- Nombre de paragraphes.
- Nombre de phrases.
- Nombre de dialogues.
- Noms propres du lexique et alias.
- Chiffres, dates, unités.
- Balises Markdown/HTML.
- Ponctuation ouvrante/fermante.

**Règle de scoring.** Un écart de paragraphe plafonne le score à 50. Un écart de dialogue ou nom propre verrouillé plafonne à 70.

## 8.6 Agent 4 — Lexique

**Mission.** Appliquer impérativement les termes du lexique.

**Entrées.** `text` + lexique.

**Sorties.** `text` corrigé + `substitutions`.

**Règles.**
- Un terme marqué `locked` ne peut jamais être traduit autrement.
- Les alias se résolvent vers l’entrée principale.
- La casse est préservée selon le contexte (début de phrase, milieu).

## 8.7 Agent 5 — Grammaire

**Mission.** Corriger accords, ponctuation, conjugaison.

**Entrées.** `text` traduit.

**Sorties.** `text` corrigé + `corrections`.

**Exemples de corrections.**
- Accord sujet/verbe.
- Accords participes passés avec `avoir`/`être`.
- Espaces insécables avant ponctuation haute en français.
- Guillemets français (`« »`).

## 8.8 Agent 6 — Style

**Mission.** Supprimer répétitions, tournures lourdes, litéralisme excessif.

**Entrées.** `text` traduit.

**Sorties.** `text` réécrit.

**Consignes.**
- Garder le sens.
- Préserver le style du genre (xianxia, romance, etc.).
- Éviter les anglicismes non justifiés.

## 8.9 Agent 7 — Polish

**Mission.** Relire comme un éditeur pour obtenir un texte fluide et naturel.

**Objectif.** *“On ne doit plus sentir que c’est une traduction.”*

**Entrées.** `text` réécrit.

**Sorties.** `text` final.

**Focus.**
- Rythme des phrases.
- Cohérence des répliques.
- Ouvertures et cliffhangers.
- Suppression des tics de langage artificiels.

## 8.10 Agent 8 — QA

**Mission.** Attribuer un score qualité global et par dimension.

**Entrées.** `paragraphs` source + traduits + `consistencyReport`.

**Sorties.** `report` de type `QualityReport`.

**Dimensions.**
- Cohérence (25 %)
- Grammaire (15 %)
- Fluidité (20 %)
- Style (15 %)
- Lexique (15 %)
- Hallucinations (5 %)
- Longueur (3 %)
- Dialogue (2 %)

**Format de sortie.** JSON strict avec `json_schema` ou `response_format`.

## 8.11 Agent 9 — Export

**Mission.** Réécrire le fichier final dans le format demandé.

**Entrées.** `paragraphs` traduits + format cible + métadonnées.

**Sorties.** Chemin du fichier exporté dans `output.metadata.exportPath`.

**Validation.**
- Le fichier est créé.
- Sa taille est non nulle.
- Pour EPUB : validation via `epubcheck` si disponible.

## 8.12 Registre des agents

Les agents natifs sont enregistrés dans la table `agents` au premier lancement.

```sql
INSERT INTO agents (id, name, stage, enabled, config_schema) VALUES
('split', 'Découpage', 'split', 1, '{"maxParagraphLength": {"type": "integer"}}'),
('pre_translate', 'Pré-traduction', 'pre_translate', 1, '{"model": {"type": "string"}}'),
('translate', 'Traduction IA', 'translate', 1, '{"model": {"type": "string"}}'),
('consistency', 'Cohérence', 'consistency', 1, '{}'),
('lexicon', 'Lexique', 'lexicon', 1, '{}'),
('grammar', 'Grammaire', 'grammar', 1, '{"language": {"type": "string"}}'),
('style', 'Style', 'style', 1, '{"tone": {"type": "string"}}'),
('polish', 'Polish', 'polish', 1, '{}'),
('qa', 'QA', 'qa', 1, '{}'),
('export', 'Export', 'export', 1, '{"format": {"type": "string"}}');
```

## 8.13 Tests d’un agent

Chaque agent doit avoir au minimum :

1. **Test unitaire nominal.** Input fixe → sortie attendue.
2. **Test de validation.** Sortie conforme au JSON Schema.
3. **Test de préservation.** Nombre de paragraphes/texte structuré conservé.
4. **Test d’erreur.** Comportement quand le provider est injoignable.
5. **Test de cas limite.** Texte très court, très long, lexique vide.

## ✅ Critères d’acceptation des agents

- [ ] Chaque agent natif implémente l’interface `Agent` (`id`, `name`, `stage`, `inputSchema`, `outputSchema`, `execute`) et est inséré dans la table `agents` au premier lancement.
- [ ] Les entrées/sorties de chaque agent sont validées avec Zod ou JSON Schema avant et après exécution.
- [ ] Les agents `split`, `pre_translate`, `translate`, `export` conservent le nombre de paragraphes source dans leurs sorties (assertion unitaire).
- [ ] L’agent `consistency` retourne un `ConsistencyReport` avec `metrics`, `warnings` et `globalScore` plafonné selon les règles métier (paragraphe manquant → 50 max, nom propre locked manquant → 70 max).
- [ ] L’agent `lexicon` applique les termes `locked`, résout les alias, et retourne la liste des `substitutions` avec sévérité.
- [ ] L’agent `qa` retourne un `QualityReport` avec un score 0–100 par dimension et un `globalScore` pondéré.
- [ ] Chaque agent dispose d’au moins 5 tests unitaires : nominal, validation, préservation, erreur réseau, cas limite.
- [ ] Chaque agent à sortie JSON a un prompt `json-fix` de secours et une stratégie de fallback documentée.

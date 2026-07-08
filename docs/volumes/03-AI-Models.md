# Volume 3 — Gestion des modèles IA

## 3.1 Providers supportés

| Provider | Type | Configuration |
|----------|------|---------------|
| Ollama | Local | `host` (défaut `http://localhost:11434`) |
| OpenAI | Cloud | `apiKey`, `baseURL` optionnel |
| Anthropic | Cloud | `apiKey`, `baseURL` optionnel |
| Gemini | Cloud | `apiKey` |
| OpenRouter | Cloud/aggregate | `apiKey`, `baseURL` |
| LM Studio | Local OpenAI-compatible | `baseURL` (ex. `http://localhost:1234/v1`) |
| Custom OpenAI-compatible | Local/cloud | `baseURL`, `apiKey` optionnel |

## 3.2 Modèle unifié

Tous les providers exposent une interface `AiProvider` commune. L’implémentation masque les différences d’API.

```typescript
export interface AiProvider {
  readonly id: string
  readonly name: string
  readonly host?: string
  readonly apiKey?: string

  listModels(): Promise<string[]>
  chat(messages: ChatMessage[], options?: ChatOptions): Promise<string>
  streamChat(messages: ChatMessage[], options?: ChatOptions): AsyncIterable<string>
  embeddings(texts: string[]): Promise<number[][]>
  isAvailable(): Promise<boolean>
}
```

### Exemple Ollama

```typescript
import { Ollama } from 'ollama'

class OllamaProvider implements AiProvider {
  private client: Ollama

  constructor(public readonly host = 'http://localhost:11434') {
    this.client = new Ollama({ host })
  }

  async listModels(): Promise<string[]> {
    const response = await this.client.list()
    return response.models.map(m => m.name)
  }

  async chat(messages: ChatMessage[]): Promise<string> {
    const response = await this.client.chat({
      model: this.model,
      messages,
      stream: false
    })
    return response.message.content
  }
}
```

**Référence** (Context7: `/ollama/ollama-js`) : `ollama.list()` retourne `response.models[].name` ; `ollama.chat({ model, messages, stream: false })` retourne la réponse complète.

### Exemple OpenAI-compatible

```typescript
import OpenAI from 'openai'

class OpenAiCompatibleProvider implements AiProvider {
  private client: OpenAI

  constructor(public readonly baseURL: string, public readonly apiKey?: string) {
    this.client = new OpenAI({ baseURL, apiKey })
  }

  async chat(messages: ChatMessage[]): Promise<string> {
    const completion = await this.client.chat.completions.create({
      model: this.model,
      messages,
      stream: false
    })
    return completion.choices[0].message.content ?? ''
  }
}
```

## 3.3 Vérifications

### Connexion

- `provider.isAvailable()` retourne `true` si l’endpoint répond.
- Pour Ollama : `GET /api/tags`.
- Pour OpenAI-compatible : `GET /models` ou appel test.

### Modèle présent

- Ollama : `listModels()` inclut le nom exact.
- Cloud : considéré présent si le provider répond.

### Téléchargement

- Ollama : `ollama.pull({ model, stream: true })`.
- Cloud : non applicable.

### Benchmark

Un mini-test mesure :

1. **Latence** : temps pour générer 100 tokens.
2. **Vitesse** : tokens/seconde.
3. **Mémoire** : usage RAM estimé via Ollama (`/api/ps`) ou système.

```typescript
interface ModelBenchmark {
  model: string
  provider: string
  latencyMs: number
  tokensPerSecond: number
  memoryMB?: number
  score: number // 0-100
}
```

## 3.4 Configuration UI

```text
IA
────────────────

Provider
• Ollama        ● OpenAI        ○ Anthropic
○ Gemini        ○ OpenRouter    ○ LM Studio

Adresse
[ http://localhost:11434          ]

Modèle
[ ▼ qwen3.5:9b                    ]

Clé API
[ ******************************** ]

                [ Tester ]
                ✓ Connecté — 12 tok/s

[ Sauvegarder ]
```

## 3.5 Priorité et fallback

L’utilisateur définit un provider principal et optionnellement un provider de fallback.

- Si le principal est indisponible → fallback.
- Si le fallback échoue → workflow en pause, notification utilisateur.
- Les modèles peuvent être marqués “rapide” vs “qualité” et utilisés pour des étapes différentes.

## 3.6 Modèles recommandés par étape

| Étape workflow | Type de modèle | Exemple | Contexte estimé |
|----------------|----------------|---------|-----------------|
| Pré-traduction | Rapide, multilingue | `qwen3.5:4b` | 128K+ |
| Traduction | Qualité, contexte long | `qwen3.5:9b` | 128K+ |
| Cohérence | Analyse comparative | `qwen3.5:9b` | 128K+ |
| Lexique | Respect strict d’instructions | `qwen3.5:9b` | 128K+ |
| Grammaire | Correction | `qwen3.5:9b` | 128K+ |
| Style | Réécriture créative | `qwen3.5:9b` ou modèle plus grand selon disponibilité | 128K+ |
| Polish | Édition finale | `qwen3.5:9b` ou modèle plus grand selon disponibilité | 128K+ |
| QA | Évaluation structurée | `qwen3.5:9b` avec JSON mode | 128K+ |

> **Note sur les modèles `qwen3.5:27b` et `qwen3.6:35b`.** Ces tags étaient mentionnés dans une version antérieure du SDD. Ils doivent être vérifiés sur [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5) au moment de l’implémentation. En l’absence de confirmation, `qwen3.5:9b` reste le modèle qualité par défaut recommandé.

## 3.6b Gestion des context windows

### Principe

Chaque modèle a une fenêtre contextuelle (nombre de tokens disponibles pour le prompt + la réponse). NovelTrad doit s’assurer que le prompt injecté reste en dessous de cette limite, en gardant une marge de sécurité.

### Limites par défaut

| Modèle | Context window annoncé | Marge NovelTrad | Usage max recommandé |
|---|---|---|---|
| `qwen3.5:4b` | 128K | 80 % | ~100K tokens |
| `qwen3.5:9b` | 128K | 80 % | ~100K tokens |
| `llama3.2:3b` | 128K | 80 % | ~100K tokens |
| `deepseek-r1:7b` | 128K | 80 % | ~100K tokens |

### Stratégie de chunking

1. **Estimation** : compter les tokens du prompt avec `tiktoken` (OpenAI-compatible) ou une approximation par caractères (1 token ≈ 4 caractères pour les langues latines, ≈ 1 caractère pour le chinois).
2. **Découpage** : si le prompt dépasse 50 % de la fenêtre contextuelle, découper le chapitre en segments cohérents (par scène ou par lot de paragraphes).
3. **Réassemblage** : traduire chaque segment puis fusionner en préservant la numérotation des paragraphes.
4. **Mémoire entre segments** : injecter le lexique complet mais une TM réduite aux matchs du segment courant.

### Tableau de compatibilité provider / modèle

| Provider | `listModels()` | Téléchargement | Streaming | Embeddings | Fallback |
|---|---|---|---|---|---|
| Ollama | ✅ `/api/tags` | ✅ `ollama.pull` | ✅ | ✅ | ✅ |
| OpenAI | ✅ `/models` | ❌ | ✅ | ✅ | ✅ |
| Anthropic | ✅ `/models` | ❌ | ✅ | ❌ | ✅ |
| Gemini | ✅ `/models` | ❌ | ✅ | ❌ | ✅ |
| OpenRouter | ✅ `/models` | ❌ | ✅ | ❌ | ✅ |
| LM Studio | ✅ `/models` | ❌ | ✅ | ✅ | ✅ |
| Custom OpenAI | ✅ `/models` | ❌ | ✅ | selon endpoint | ✅ |

## 3.7 Limitation de débit (rate limiting)

Les providers cloud (OpenAI, Anthropic, Gemini, OpenRouter) imposent des limites de requêtes et de tokens par minute. Ollama (local) est exempté.

### Configuration par provider

```typescript
interface RateLimitConfig {
  requestsPerMinute?: number  // défaut : illimité
  tokensPerMinute?: number    // défaut : illimité
}
```

Chaque entrée `models` (Vol 06) peut stocker un `rate_limit_config TEXT` (JSON) contenant ces deux champs. La valeur `null` ou absente signifie « pas de limite » (par défaut pour Ollama).

### Comportement dans l’AiRouter

- Avant chaque dispatch vers un provider cloud, l’AiRouter vérifie le token bucket.
- Si la limite est atteinte, la requête est mise en file d’attente jusqu’à la fenêtre de temps suivante.
- En cas de réponse HTTP **429 Too Many Requests** : respecter l’en-tête `Retry-After`, backoff exponentiel (1 s → 2 s → 4 s), puis fallback vers le provider secondaire (§3.5).
- Le throttling est **invisible pour l’utilisateur** — seule une notification dans les logs (niveau `warn`) est émise.

### Priorité

Ollama n’est jamais throttlé. Pour les providers cloud, si `RateLimitConfig` n’est pas configuré, l’AiRouter n’applique aucune limitation proactive — il réagit uniquement aux 429 reçus.

## 3.8 Estimation des coûts

Pour les providers cloud facturant au token, NovelTrad estime le coût des traductions et l’affiche à l’utilisateur.

### Métadonnées coût par modèle

```typescript
interface ModelCostMetadata {
  costPerInputToken?: number   // USD par 1K tokens (ex. 0.00003 pour GPT-4)
  costPerOutputToken?: number  // USD par 1K tokens
  currency?: string             // défaut “USD”
}
```

Ces champs sont `null` pour les modèles locaux (Ollama, LM Studio). Ils sont stockés dans le JSON `metadata` de la table `models` (Vol 06).

### Calcul

L’AiRouter expose une méthode :

```typescript
class AiRouter {
  estimateCost(
    modelId: string,
    inputTokens: number,
    outputTokens: number
  ): number | null // null = modèle local ou coût non configuré
}
```

Le comptage des tokens utilise le mécanisme existant (§3.6b, tiktoken ou approximation ~4 caractères/token). Chaque étape de job accumule les tokens via `Step.tokensIn` / `Step.tokensOut` (Vol 07 §7.3).

### Accumulation par job

La table `jobs` (Vol 06) expose un champ optionnel `cost_usd REAL` (migration `012_index_coverage.sql`, voir Vol 06 §6.4). À la fin de chaque étape, le WorkflowEngine accumule : `job.cost_usd += estimateCost(...)`.

### Affichage

L’écran Workflow (Vol 04 §4.9) affiche le coût estimé cumulé en temps réel dans le détail du job actif. L’écran Projet (Vol 04 §4.6) affiche le coût total du projet dans les statistiques.

## ✅ Critères d’acceptation de la gestion des modèles

- [ ] Tous les providers listés (Ollama, OpenAI, Anthropic, Gemini, OpenRouter, LM Studio, Custom) sont configurables via l’UI avec validation Zod.
- [ ] Le bouton “Tester” appelle `provider.isAvailable()` et affiche latence, tokens/seconde, mémoire utilisée.
- [ ] Ollama peut télécharger un modèle manquant avec barre de progression via `ollama.pull({ model, stream: true })`.
- [ ] Le fallback entre providers fonctionne automatiquement après 3 échecs consécutifs ou timeout.
- [ ] Les modèles configurés sont persistés dans SQLite (`Models` table) avec flags `is_default` / `is_fallback`.
- [ ] Le chunking automatique s’active quand le prompt dépasse 50 % de la fenêtre contextuelle du modèle.
- [ ] Le tableau de compatibilité provider / modèle est respecté (`listModels`, streaming, embeddings, fallback).
- [ ] Le rate limiting respecte les limites configurées et honore les réponses 429 (Retry-After).
- [ ] Le coût estimé est affiché dans l’écran Workflow et accumulé par job.

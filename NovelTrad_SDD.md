# TBL fork — périmètre NovelTrad

Ce dépôt reste un fork direct de `hydropix/TranslateBooksWithLLMs`. Toutes les
fonctionnalités, l'interface, le branding, l'attribution, les formats et les
tests du projet amont sont conservés. Ce document ne spécifie que les deux
écarts fonctionnels du fork.

## 1. Providers supplémentaires

Ajouter les providers natifs suivants dans les mêmes points d'extension que les
providers TBL existants :

| Identifiant | Fournisseur | Clé | API |
|---|---|---|---|
| `anthropic` | Anthropic / Claude | `ANTHROPIC_API_KEY` | Anthropic Messages API |
| `xai` | xAI / Grok | `XAI_API_KEY` | OpenAI-compatible |
| `nexum` | Nexum Router | `NEXUM_API_KEY` | OpenAI-compatible |
| `opencode` | OpenCode Zen | `OPENCODE_API_KEY` | OpenAI-compatible Chat Completions |
| `opencodego` | OpenCode Go | `OPENCODE_GO_API_KEY` (fallback `OPENCODE_API_KEY`) | OpenAI-compatible Chat Completions |

Chaque provider doit fonctionner depuis la CLI, l'interface web, les tests de
connexion, le chargement des modèles, les parcours glossaire/style et la
reprise. Les clés multiples séparées par des virgules, la rotation sur 429,
les erreurs normalisées, la validation d'endpoint et la non-persistance des
secrets suivent les règles déjà présentes dans TBL.

Endpoints par défaut :

- Anthropic : `https://api.anthropic.com/v1` avec `POST /messages` et `GET /models`.
- xAI : `https://api.x.ai/v1` avec `POST /chat/completions` et `GET /models`.
- Nexum : `https://dialagram.me/router/v1` avec le contrat OpenAI-compatible.
- OpenCode Zen : `https://opencode.ai/zen/v1` avec `POST /chat/completions` et `GET /models`.
- OpenCode Go : `https://opencode.ai/zen/go/v1` avec le même contrat. Une clé Go
  vide retombe sur `OPENCODE_API_KEY`.

Seuls les modèles Chat Completions sont routés (DeepSeek, Kimi, GLM, MiniMax,
MiMo, Hy3). GPT (`/responses`), Claude (`/messages`) et Gemini via Zen/Go sont
hors périmètre.

Les listes de modèles doivent être récupérées quand l'API le permet et
disposer d'une liste de repli courte et documentée.

## 2. Raffinement en quatre passes

La traduction simple reste inchangée. Quand l'utilisateur active « Raffiner »,
le pipeline complet est :

1. **Traduction** — passe TBL existante.
2. **Contexte** — analyse de chaque bloc avec le bloc précédent et le bloc
   suivant ; sortie : suggestions de cohérence, terminologie et continuité.
3. **Correction** — correction orthographique, grammaticale, ponctuation et
   fluidité du brouillon ; sortie : texte corrigé.
4. **Final** — génération du texte définitif à partir de la traduction initiale,
   des suggestions de la passe 2 et du texte corrigé de la passe 3.

Les passes sont strictement ordonnées et utilisent le même provider et le même
modèle. Les placeholders, balises, timecodes et structures de format doivent
être préservés. `--refine-only` exécute les passes 2 à 4 sur un fichier déjà
traduit. Les sorties intermédiaires restent internes aux checkpoints et ne
changent pas le parcours utilisateur existant.

Chaque passe est reprenable indépendamment au niveau du bloc. Une interruption
ou une erreur conserve les artefacts déjà produits et reprend à la passe et au
bloc courants sans rejouer le travail terminé. Après épuisement des tentatives,
le job reste resumable et signale explicitement la passe et le bloc en échec.

La progression web expose quatre phases pour Traduire + Raffiner et trois
phases pour Raffiner seul, tout en conservant les champs historiques nécessaires
aux consommateurs existants.

## 3. Critères d'acceptation

- Le fork est basé sur l'amont TBL 1.5.6 sans autre changement historique.
- Les cinq providers sont utilisables depuis CLI et interface web avec une
  réponse `LLMResponse` normale, une liste de modèles et des erreurs testées.
- Les parcours EPUB, TXT, DOCX et SRT produisent une sortie valide en traduction
  simple et en multipasse.
- Les tests prouvent l'ordre 1→2→3→4, les blocs voisins, la reprise par passe,
  `--refine-only`, la conservation des placeholders et l'absence de régression
  sur les fonctionnalités TBL héritées.

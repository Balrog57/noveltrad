# llms.txt

Le fichier [`llms.txt`](./llms.txt) est un standard ouvert défini par [llmstxt.org](https://llmstxt.org/) qui fournit un résumé structuré de la documentation pour les agents IA.

Ce fichier concatène l'intégralité des volumes du SDD NovelTrad 2.0 dans un format lisible par les LLMs. Il peut être utilisé par :

- **OpenCode / Claude Code / Cursor** pour contextualiser automatiquement les agents de code
- **ChatGPT / Claude / DeepSeek** pour comprendre l'architecture du projet
- **Tout agent IA** qui implémente le protocole `llms.txt`

## Contenu

Le fichier inclut :

- L'architecture complète du projet
- Les 25 volumes du SDD
- Les exemples d'entrée/sortie des agents
- Les prompts système versionnés
- Le plan de développement

## Accès direct

- **Fichier brut** : [llms.txt](/noveltrad/llms.txt) (à la racine du site, accessible par les crawlers)
- **Source** : disponible dans [`docs/llms.txt`](https://github.com/Balrog57/noveltrad/blob/main/docs/llms.txt)

## Pour les agents IA

Pour ingérer ce SDD en un seul contexte :

```
@https://balrog57.github.io/noveltrad/llms.txt
```

Ou en local :

```
curl https://balrog57.github.io/noveltrad/llms.txt
```

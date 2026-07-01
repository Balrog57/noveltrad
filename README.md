# 📖 NovelTrad 2.0

*Le traducteur de romans multi-agent qui parle chinois, pense en IA, et écrit en français.*

[![Version](https://img.shields.io/badge/version-2.0.1-blue?style=flat-square)](https://github.com/Balrog57/noveltrad/releases)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-145%20passing-brightgreen?style=flat-square)](https://github.com/Balrog57/noveltrad/actions)
[![Node](https://img.shields.io/badge/node-%3E%3D22-339933?style=flat-square&logo=node.js&logoColor=white)]()
[![Electron](https://img.shields.io/badge/Electron-31-47848F?style=flat-square&logo=electron&logoColor=white)]()
[![Vue](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js&logoColor=white)]()
[![Ollama](https://img.shields.io/badge/Ollama-local-blueviolet?style=flat-square)]()

> **TL;DR** — Importez un roman chinois → 10 agents IA le traduisent → exportez un EPUB français. 100% local, aucune donnée dans le cloud.

---

## ✨ Fonctionnalités

- 🤖 **10 agents IA spécialisés** — Split, pré-traduction, traduction, cohérence, lexique, grammaire, style, polish, QA, export. Un pipeline complet, pas une simple traduction mot-à-mot.
- 🧠 **Translation Memory persistante** — Chaque phrase traduite est réutilisée. La cohérence s'améliore chapitre après chapitre, les coûts IA diminuent.
- 📚 **Lexique dynamique verrouillé** — Noms de personnages, lieux, techniques. Verrouillez une traduction, elle ne change plus jamais. Alias et termes interdits supportés.
- 🏠 **100% local** — Fonctionne avec [Ollama](https://ollama.com). Aucune donnée source ou traduite ne quitte votre machine.
- 📦 **Export natif** — EPUB, DOCX, Markdown, TXT, HTML. Mode bilingue inclus.
- 🔄 **Auto-update** — Mises à jour automatiques via GitHub Releases.

## 🎯 Pourquoi l'utiliser ?

**Le problème** : Traduire un web novel chinois de 500 chapitres avec un LLM, c'est perdre la cohérence des noms au chapitre 10 et obtenir 500 styles différents.

**La solution** : NovelTrad orchestre 10 agents IA qui travaillent ensemble, alimentés par une mémoire de traduction et un lexique verrouillé. Le chapitre 500 a le même style et les mêmes noms que le chapitre 1.

```
Chapitre source → 10 agents IA → EPUB français publiable
                    ↑                    ↑
            TM + Lexique           QA score ≥ 90
```

## 🛠 Quick Start

### Prérequis

- **Node.js** ≥ 22
- **[Ollama](https://ollama.com)** en cours d'exécution (`ollama serve`)

### Installation

```bash
git clone https://github.com/Balrog57/noveltrad.git
cd noveltrad
npm install
ollama pull qwen3.5:9b    # Modèle recommandé
npm run dev                # 🎉 L'app s'ouvre
```

### Workflow en 30 secondes

1. **Nouveau projet** → Choisir langue source (zh) / cible (fr)
2. **Importer** un fichier TXT / DOCX / EPUB
3. **Cliquer "Traduire"** → Les 10 agents travaillent séquentiellement
4. **Vérifier** le score QA et le rapport de cohérence
5. **Exporter** en EPUB

## 📖 Documentation

La documentation complète (25 volumes SDD, guides, inspirations) est disponible sur GitHub Pages :

➡️ **[https://balrog57.github.io/noveltrad/](https://balrog57.github.io/noveltrad/)**

```bash
npm run docs:dev     # Serveur local (port 5174)
npm run docs:build   # Build statique
```

### Contenu de la doc

| Section | Contenu |
|---------|---------|
| **25 volumes** | Vision, architecture, UI, DB, workflow, agents, TM, lexique, export, sécurité, CI/CD... |
| **Guide développeur** | Ajouter un agent, brancher un provider, modifier le pipeline |
| **Cas d'usage** | Web novels, fan-fictions, batch EPUB, mode local, QA assistée |
| **Inspirations** | Comparatif avec OmegaT, Sugoi, honya, TransAgents, NovelTrans... |

## 🏗 Architecture

```
noveltrad/
├── .github/workflows/       # CI (ci.yml) + Release (release.yml) + Pages (pages.yml)
├── docs/                    # VitePress — 25 volumes SDD + guides
├── apps/desktop/
│   ├── src/main/            # Electron : IPC, managers, services, agents, DB
│   ├── src/preload/         # contextBridge (novelTradAPI)
│   ├── src/renderer/        # Vue 3 : views, stores, components
│   └── tests/               # Vitest (145) + Playwright E2E
└── packages/shared/         # Types + schemas Zod
```

### Pipeline de traduction

```
Source → Split → Pré-trad → Traduire → Cohérence → Lexique
    → Grammaire → Style → Polish → QA → Export EPUB
```

Chaque étape est :
- **Persistée** dans SQLite (jobs, steps, snapshots)
- **Relançable** individuellement (`retryStep`, `retryFrom`)
- **Observable** en temps réel (progression IPC)

## 🧪 Tests

```bash
npm test                                    # 145 tests unitaires (Vitest)
npm run test:e2e --workspace=apps/desktop   # Playwright + Electron
npm run type-check --workspace=apps/desktop # vue-tsc --noEmit
```

## 🚀 Release & Auto-update

```bash
# Bump version dans apps/desktop/package.json
git tag v2.0.2
git push --tags
# GitHub Actions build → publish → auto-update notifie les utilisateurs
```

| Canal | Tag pattern | Usage |
|-------|-------------|-------|
| `latest` | `v2.0.2` | Stable |
| `beta` | `v2.1.0-beta` | Pré-release |
| `alpha` | `v2.1.0-alpha` | Dev |

## 📦 Formats supportés

| Direction | Formats |
|-----------|---------|
| **Import** | TXT, Markdown, DOCX, EPUB, TMX |
| **Export** | EPUB, DOCX, Markdown, TXT, HTML (mode bilingue) |
| **Lexique** | CSV, JSON, TSV |

## 🛡 Stack technique

| Domaine | Choix |
|---------|-------|
| Desktop | Electron 31 + electron-builder + electron-updater |
| UI | Vue 3 (Composition API) + Pinia + Vue Router |
| Bundler | electron-vite (Vite 5) |
| Langage | TypeScript strict |
| Validation | Zod |
| Base de données | node-sqlite3-wasm (WAL mode, migrations inline) |
| IA | Ollama (local), AiRouter multi-provider |
| Tests | Vitest + Playwright |
| CI/CD | GitHub Actions |
| Docs | VitePress + GitHub Pages |

## 🤝 Contribuer

Les PR sont les bienvenues !

1. Fork le projet
2. Crée une branche (`git checkout -b feature/ma-feature`)
3. Vérifie : `npm test && npm run type-check --workspace=apps/desktop`
4. Ouvre une PR

Le [guide développeur](https://balrog57.github.io/noveltrad/developer-guide) détaille comment ajouter un agent, brancher un provider IA, ou modifier le pipeline.

## 🗺 Roadmap

- [ ] Agent Summarizer (cohérence long-terme)
- [ ] Mode bilingue côte-à-côte dans l'éditeur
- [ ] Fine-tuning local via la Translation Memory
- [ ] File d'attente QA pour les paragraphes suspects

## 📜 Licence

MIT © Balrog57

---

> Si ce projet vous aide, n'hésitez pas à mettre une ⭐ — ça motive pour la suite !
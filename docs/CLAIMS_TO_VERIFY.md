# Claims techniques a verifier — Audit SDD NovelTrad 2.0

> Date de l'audit : 2026-06-30  
> Methode : verification web (documentation officielle, pages de bibliotheques) en l'absence de connecteur /context7 natif.  
> Statut : ✅ confirmé | ⚠️ partiel / a nuancer | ❌ a corriger | 🔲 non verifie

---

## Electron — securite & sandbox

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `contextIsolation` est `true` par defaut depuis Electron 12 | `01-Architecture.md`, `21-Security.md` | ✅ | [electronjs.org/docs/latest/tutorial/context-isolation](https://www.electronjs.org/docs/latest/tutorial/context-isolation) | La doc officielle confirme que le context isolation est active par defaut depuis Electron 12. |
| `nodeIntegration` doit etre `false` | `01-Architecture.md`, `21-Security.md` | ✅ | [electronjs.org/docs/latest/tutorial/security](https://www.electronjs.org/docs/latest/tutorial/security) | Recommandation de securite officielle. |
| `app.enableSandbox()` avant `app.whenReady()` | `01-Architecture.md` (version initiale) | ❌ → ✅ corrige | [electronjs.org/docs/latest/tutorial/sandbox](https://www.electronjs.org/docs/latest/tutorial/sandbox) | `enableSandbox()` n'est pas une API standard documentee. Reformule dans `01-Architecture.md` et `21-Security.md` en baseline `webPreferences` moderne (`sandbox: true`, `contextIsolation: true`, `nodeIntegration: false`). |
| CSP via `session.defaultSession.webRequest.onHeadersReceived` | `01-Architecture.md`, `21-Security.md` | ✅ | [electronjs.org/docs/latest/tutorial/security#content-security-policy](https://www.electronjs.org/docs/latest/tutorial/security#content-security-policy) | Mecanisme valide, bien que la CSP puisse aussi etre definie via balise `<meta>` ou en-tete serveur. |
| `preload.js` expose les API via `contextBridge` | `01-Architecture.md`, `16-Internal-API.md` | ✅ | [electronjs.org/docs/latest/tutorial/context-isolation#context-bridge](https://www.electronjs.org/docs/latest/tutorial/context-isolation#context-bridge) | Pattern canonique. |
| Workers Electron doivent etre des fichiers separes et bien bundles | `01-Architecture.md`, `22-Performance.md` | 🔲 | — | A valider au moment du build Electron (config Vite/Webpack pour `new Worker()`). |

## Ollama & modeles

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| API `ollama.list()` retourne `response.models[].name` | `02-Installation.md`, `03-AI-Models.md` | ✅ | [github.com/ollama/ollama-js](https://github.com/ollama/ollama-js) | L'API `list()` retourne bien une liste de modeles avec `name`. |
| `ollama.pull({ model, stream: true })` retourne un flux | `02-Installation.md` | ✅ | [github.com/ollama/ollama-js](https://github.com/ollama/ollama-js) | L'option `stream` est supportee. |
| Modeles recommandes `qwen3.5:9b` et `qwen3.5:4b` | `00-Vision.md`, `02-Installation.md`, `03-AI-Models.md`, etc. | ✅ | [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5) | Les tags `qwen3.5:9b` et `qwen3.5:4b` sont listes. A noter : les noms de modeles evoluent rapidement ; prevoir une verification via `listModels()` au runtime. |
| `deepseek-r1:7b` comme modele qualite | `03-AI-Models.md`, `08-Agents.md` | 🔲 | — | Non verifie en ligne dans cette passe ; verifier sur [ollama.com/library/deepseek-r1](https://ollama.com/library/deepseek-r1) au moment de l'implementation. |
| `llama3.2:3b` comme modele leger | `01-Architecture.md`, `02-Installation.md` | ✅ | [ollama.com/library/llama3.2](https://ollama.com/library/llama3.2) | Existe avec tag `3b`. |
| Contexte 128K / 256K pour `qwen3.5` | `02-Installation.md`, `03-AI-Models.md` | ⚠️ | [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5) | La fiche du modele doit etre consultee pour la valeur exacte. Le SDD utilise maintenant 128K comme context window annonce avec marge de securite 80 %. |

## SQLite / better-sqlite3

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `better-sqlite3` est precompilee pour Electron | `01-Architecture.md`, `06-Database.md` | ⚠️ | [github.com/WiseLibs/better-sqlite3](https://github.com/WiseLibs/better-sqlite3) | better-sqlite3 fournit des binaires precompiles mais necessite parfois un rebuild (`electron-rebuild`) selon la version d'Electron/Node. A documenter au moment du build. |
| WAL mode active | `06-Database.md` | ✅ | [sqlite.org/wal.html](https://sqlite.org/wal.html) | SQLite supporte WAL nativement ; better-sqlite3 expose `pragma journal_mode = WAL`. |

## Node.js / worker_threads

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| Worker threads executent les agents longs | `01-Architecture.md`, `22-Performance.md` | ✅ | [nodejs.org/docs/latest/api/worker_threads.html](https://nodejs.org/docs/latest/api/worker_threads.html) | API stable. Attention : les workers Electron doivent etre des fichiers separes et bien bundles. |

## VitePress

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `themeConfig.search = { provider: "local" }` active la recherche locale | `index.md` | ✅ | [vitepress.dev/reference/default-theme-search](https://vitepress.dev/reference/default-theme-search) | Recherche locale Minisearch integree. Deja configure. |
| VitePress 1.3+ supporte le build | `package.json` | ✅ | `package.json` local | `vitepress: ^1.3.0` ; build teste avec 1.6.4. |

## Electron-builder / electron-updater

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `generateUpdatesFilesForAllChannels: true` genere `latest.yml`, `beta.yml`, `alpha.yml` | `17-Auto-Update.md` | ⚠️ | [electron.build/app/pkg/publish/everything](https://www.electron.build/app/pkg/publish/everything.html) | La cle existe mais le comportement exact depend du provider et des canaux semver. A tester en CI. |
| `releaseType: draft` empeche `electron-updater` de trouver la release | `17-Auto-Update.md` | ✅ | Comportement documente | Les drafts ne sont pas listes publiquement par l'API GitHub sans authentification. |
| `autoUpdater.channel = channel` et `autoUpdater.allowDowngrade` | `17-Auto-Update.md` | ✅ | [electron.build/app/updates](https://www.electron.build/app/updates.html) | API documentee. |
| Code signing via `CSC_LINK` / `APPLE_ID` / notarytool | `20-CICD.md` | ✅ | [electron.build](https://www.electron.build) | Configuration standard documentee. |

## GitHub Actions

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `actions/checkout@v5`, `actions/setup-node@v6`, `actions/upload-artifact@v5`, `actions/cache@v5` | `20-CICD.md` (version initiale) | ❌ → ✅ corrige | [github.com/actions](https://github.com/actions) | Les versions indiquees (`v5`, `v6`) n'existaient pas a ce jour. Corrige en `v4` pour `checkout`, `setup-node`, `upload-artifact`, `cache`. |
| `concurrency.group` annule les anciens runs | `20-CICD.md` | ✅ | [docs.github.com/actions](https://docs.github.com/en/actions) | Syntaxe valide. |

## Parsing & librairies

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `mammoth.convertToHtml({ path })` | `05-Project-Management.md` | ✅ | [github.com/mwilliamson/mammoth.js](https://github.com/mwilliamson/mammoth.js) | API valide. |
| `@likecoin/epub-ts` pour parsing EPUB | `05-Project-Management.md`, `22-Performance.md` | ⚠️ | Recherche rapide | Package peu telecharge/maintenu ; a valider ou remplacer par `epubjs`, `node-epub`, ou `adm-zip` + `cheerio`/`jsdom`. |
| `epub-gen-memory` pour generation EPUB | `13-Export.md` | ⚠️ | [npmjs.com/package/epub-gen-memory](https://www.npmjs.com/package/epub-gen-memory) | Package existant mais peu telecharge. Alternative : `epub-gen` plus ancien, ou generation manuelle avec `archiver` + `jsdom`. |
| `docx` (dolanmiu/docx) pour DOCX | `13-Export.md` | ✅ | [github.com/dolanmiu/docx](https://github.com/dolanmiu/docx) | Package majeur et maintenu. |
| `franc` pour detection de langue | `05-Project-Management.md` | ✅ | [github.com/wooorm/franc](https://github.com/wooorm/franc) | API `franc(text)` retourne ISO 639-3. |
| `chardet` / `iconv-lite` pour detection/conversion d'encodage | `05-Project-Management.md` | ✅ | npm registry | Librairies standards et maintenues. |
| `epubcheck` pour validation EPUB | `13-Export.md` | ✅ | [github.com/w3c/epubcheck](https://github.com/w3c/epubcheck) | Outil Java de reference du W3C. |

## Vue 3 / Pinia

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `<script setup lang="ts">` | `01-Architecture.md`, `04-UI-UX.md` | ✅ | [vuejs.org](https://vuejs.org) | Pattern recommande. |
| Pinia remplace Vuex | `01-Architecture.md` | ✅ | [pinia.vuejs.org](https://pinia.vuejs.org) | Pinia est le store officiel Vue. |

## Securite

| Claim | Fichier | Statut | Source verifiee | Note |
|---|---|---|---|---|
| `keytar` stocke les cles dans le keyring OS | `21-Security.md` | ✅ | [github.com/atom/node-keytar](https://github.com/atom/node-keytar) | Librairie standard pour Credential Locker / Keychain / libsecret. |
| AES-256-GCM via Node.js `crypto` | `21-Security.md` | ✅ | [nodejs.org/api/crypto.html](https://nodejs.org/api/crypto.html) | API native stable pour le chiffrement fallback. |
| `path.resolve` + verification de prefixe contre path traversal | `21-Security.md` | ✅ | Pattern de securite standard | A completer par des tests sur symlinks et encodages URL. |

---

## Synthèse des claims corriges pendant l'edition

1. **GitHub Actions versions** (`20-CICD.md`) : remplace `v5`/`v6` par `v4` pour `checkout`, `setup-node`, `upload-artifact`, `cache`.
2. **`app.enableSandbox()`** (`01-Architecture.md` et `21-Security.md`) : reformule en baseline Electron moderne via `webPreferences` explicites (`sandbox: true`, `contextIsolation: true`, `nodeIntegration: false`).
3. **Modeles `qwen3.5:27b` / `qwen3.6:35b`** : retires au profit de `qwen3.5:9b` comme modele qualite par defaut.
4. **Context window** : precise avec marge de securite 80 % et chunking automatique (`03-AI-Models.md`, `02-Installation.md`).

## Claims a verifier avant l'implementation

1. **Librairies EPUB** : valider ou remplacer `@likecoin/epub-ts` (parsing) et `epub-gen-memory` (generation).
2. **`deepseek-r1:7b`** : verifier sa disponibilite et ses performances si retenu comme alternative.
3. **`generateUpdatesFilesForAllChannels: true`** : tester le comportement reel en CI avec `electron-builder`.
4. **Workers Electron** : valider le bundling des fichiers worker dans le processus main.

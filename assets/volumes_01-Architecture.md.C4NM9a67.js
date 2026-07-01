import{_ as a,o as n,c as e,a2 as i}from"./chunks/framework.L3mmv3XT.js";const k=JSON.parse('{"title":"Volume 1 — Architecture","description":"","frontmatter":{},"headers":[],"relativePath":"volumes/01-Architecture.md","filePath":"volumes/01-Architecture.md","lastUpdated":1782934788000}'),t={name:"volumes/01-Architecture.md"};function l(p,s,r,o,c,d){return n(),e("div",null,[...s[0]||(s[0]=[i(`<h1 id="volume-1-—-architecture" tabindex="-1">Volume 1 — Architecture <a class="header-anchor" href="#volume-1-—-architecture" aria-label="Permalink to &quot;Volume 1 — Architecture&quot;">​</a></h1><h2 id="_1-1-choix-techniques" tabindex="-1">1.1 Choix techniques <a class="header-anchor" href="#_1-1-choix-techniques" aria-label="Permalink to &quot;1.1 Choix techniques&quot;">​</a></h2><h3 id="electron" tabindex="-1">Electron <a class="header-anchor" href="#electron" aria-label="Permalink to &quot;Electron&quot;">​</a></h3><p><strong>Rationale.</strong> Electron fournit un shell desktop cross-platform, un accès natif au système de fichiers, et un écosystème mature pour l’auto-update via <code>electron-builder</code>/<code>electron-updater</code>.</p><p><strong>Security baseline</strong> (Context7: <code>/electron/electron</code>):</p><ul><li><code>contextIsolation</code> reste à <code>true</code> (défaut depuis Electron 12).</li><li><code>nodeIntegration</code> à <code>false</code>.</li><li>APIs exposées via <code>contextBridge.exposeInMainWorld()</code> dans un preload script.</li><li>Sandbox activé par défaut dès Electron 20 ; <code>nodeIntegration: false</code>, <code>contextIsolation: true</code>, <code>webSecurity: true</code>.</li><li>Content Security Policy stricte via <code>session.defaultSession.webRequest.onHeadersReceived</code>.</li></ul><div class="language-javascript vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">javascript</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">// preload.js</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">const</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> { </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">contextBridge</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">ipcRenderer</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> } </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> require</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;electron&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">)</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">contextBridge.</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">exposeInMainWorld</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;novelTradAPI&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, {</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">  openProject</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: (</span><span style="--shiki-light:#E36209;--shiki-dark:#FFAB70;">path</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">) </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> ipcRenderer.</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">invoke</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;project:open&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, path),</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">  onLog</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: (</span><span style="--shiki-light:#E36209;--shiki-dark:#FFAB70;">callback</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">) </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> ipcRenderer.</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">on</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;log&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, (</span><span style="--shiki-light:#E36209;--shiki-dark:#FFAB70;">_event</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#E36209;--shiki-dark:#FFAB70;">value</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">) </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=&gt;</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> callback</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(value))</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">})</span></span></code></pre></div><h3 id="vue-3-typescript-vite" tabindex="-1">Vue 3 + TypeScript + Vite <a class="header-anchor" href="#vue-3-typescript-vite" aria-label="Permalink to &quot;Vue 3 + TypeScript + Vite&quot;">​</a></h3><p><strong>Rationale.</strong> Vue 3 offre le Composition API, une réactivité performante et une intégration TypeScript naturelle. Vite fournit un serveur de développement rapide et un bundling optimisé.</p><p><strong>Patterns retenus</strong> (Context7: <code>/websites/vuejs_guide</code>, <code>/vitejs/vite</code>):</p><ul><li><code>&lt;script setup lang=&quot;ts&quot;&gt;</code> par défaut.</li><li>Composants métier sous <code>src/renderer/components/</code>.</li><li>Stores Pinia sous <code>src/renderer/stores/</code>.</li><li>Services métier sous <code>src/main/services/</code> (processus main Electron).</li><li>Types partagés sous <code>src/shared/types/</code>.</li></ul><h3 id="pinia" tabindex="-1">Pinia <a class="header-anchor" href="#pinia" aria-label="Permalink to &quot;Pinia&quot;">​</a></h3><p><strong>Rationale.</strong> Pinia remplace Vuex, est modulaire, type-safe et accepte des plugins (persistance, logs).</p><p><strong>Patterns retenus</strong> (Context7: <code>/vuejs/pinia</code>):</p><ul><li>Un store par domaine : <code>useProjectStore</code>, <code>useWorkflowStore</code>, <code>useModelStore</code>, <code>useLexiconStore</code>.</li><li>Actions asynchrones retournant des promesses.</li><li>Getters pour les dérivations.</li><li>Plugin de persistence éventuel pour les préférences globales.</li></ul><h3 id="sqlite" tabindex="-1">SQLite <a class="header-anchor" href="#sqlite" aria-label="Permalink to &quot;SQLite&quot;">​</a></h3><p><strong>Rationale.</strong> Base relationnelle embarquée, zero-config, portable dans le dossier projet.</p><ul><li>Librairie : <code>better-sqlite3</code> (synchrone, performante, précompilée pour Electron).</li><li>Schéma versionné avec migrations.</li><li>Repositories pour isoler les requêtes SQL du reste du code.</li></ul><h3 id="node-js-only" tabindex="-1">Node.js only <a class="header-anchor" href="#node-js-only" aria-label="Permalink to &quot;Node.js only&quot;">​</a></h3><p><strong>Rationale.</strong> Un seul runtime supprime la dépendance Python, simplifie l’installation et le packaging.</p><ul><li>Les appels IA passent par HTTP à Ollama ou aux API compatibles OpenAI.</li><li>Le pré-traduction est assuré par un modèle Ollama léger (ex. <code>qwen3.5:4b</code>, <code>qwen3.5:2b</code>, <code>llama3.2:3b</code>, ou un modèle spécifique choisi par l’utilisateur).</li><li>Les worker threads Node.js (<code>worker_threads</code>) exécutent les agents longs pour ne pas bloquer le main process.</li></ul><h2 id="_1-2-architecture-globale" tabindex="-1">1.2 Architecture globale <a class="header-anchor" href="#_1-2-architecture-globale" aria-label="Permalink to &quot;1.2 Architecture globale&quot;">​</a></h2><div class="language-mermaid vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">mermaid</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">flowchart TD</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    subgraph Renderer[&quot;Renderer Process&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        R1[Vue 3 + Components]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        R2[Pinia Stores]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        R3[Views + Composables]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    end</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    subgraph Main[&quot;Electron Main Process&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        M1[Window Manager]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        M2[IPC Router]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        M3[Managers]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        M4[Worker Threads]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    end</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    subgraph Services[&quot;Services / Managers&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S1[ProjectManager]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S2[ModelManager]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S3[WorkflowEngine]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S4[ExportEngine]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S5[LexiconEngine]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S6[TranslationMemory]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S7[QualityChecker]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S8[ConsistencyChecker]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S9[PluginSystem]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        S10[UpdateManager]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    end</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    subgraph AI[&quot;External / Local AI&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A1[Ollama]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A2[OpenAI]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A3[Anthropic]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A4[Gemini]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A5[OpenRouter]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A6[LM Studio]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    end</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    Renderer --&gt;|contextBridge / IPC| Main</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    Main --&gt;|fs / http / worker_threads| Services</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    Services --&gt;|HTTP / REST / Ollama API| AI</span></span></code></pre></div><h3 id="flux-d-un-clic-traduire-le-chapitre" tabindex="-1">Flux d’un clic “Traduire le chapitre” <a class="header-anchor" href="#flux-d-un-clic-traduire-le-chapitre" aria-label="Permalink to &quot;Flux d’un clic “Traduire le chapitre”&quot;">​</a></h3><ol><li><strong>Renderer</strong> : appelle <code>novelTradAPI.runWorkflow(chapterId)</code>.</li><li><strong>IPC Router</strong> : valide le message et route vers <code>WorkflowEngine</code>.</li><li><strong>WorkflowEngine</strong> : crée un <code>Job</code> dans SQLite, publie des événements.</li><li><strong>AgentRunner</strong> (Worker Thread) : exécute chaque agent séquentiellement.</li><li><strong>LexiconEngine / TranslationMemory</strong> : injectés comme contexte.</li><li><strong>QualityChecker / ConsistencyChecker</strong> : évaluent le résultat.</li><li><strong>ExportEngine</strong> : écrit le fichier final.</li><li><strong>Historique</strong> : sauvegarde une version.</li><li><strong>Événements</strong> : retournés au renderer via <code>webContents.send(&#39;job:event&#39;, payload)</code>.</li></ol><h2 id="_1-3-arborescence-du-projet" tabindex="-1">1.3 Arborescence du projet <a class="header-anchor" href="#_1-3-arborescence-du-projet" aria-label="Permalink to &quot;1.3 Arborescence du projet&quot;">​</a></h2><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>noveltrad2/</span></span>
<span class="line"><span>├── apps/</span></span>
<span class="line"><span>│   └── desktop/</span></span>
<span class="line"><span>│       ├── electron-builder.yml</span></span>
<span class="line"><span>│       ├── package.json</span></span>
<span class="line"><span>│       ├── resources/</span></span>
<span class="line"><span>│       │   ├── icon.ico</span></span>
<span class="line"><span>│       │   ├── icon.png</span></span>
<span class="line"><span>│       │   └── splash.html</span></span>
<span class="line"><span>│       ├── src/</span></span>
<span class="line"><span>│       │   ├── main/</span></span>
<span class="line"><span>│       │   │   ├── index.ts              # entry point Electron main</span></span>
<span class="line"><span>│       │   │   ├── ipc/</span></span>
<span class="line"><span>│       │   │   │   ├── channels.ts       # IPC channel registry</span></span>
<span class="line"><span>│       │   │   │   ├── router.ts         # validation + dispatch</span></span>
<span class="line"><span>│       │   │   │   └── handlers/         # per-domain handlers</span></span>
<span class="line"><span>│       │   │   ├── managers/</span></span>
<span class="line"><span>│       │   │   │   ├── ProjectManager.ts</span></span>
<span class="line"><span>│       │   │   │   ├── ModelManager.ts</span></span>
<span class="line"><span>│       │   │   │   ├── WorkflowEngine.ts</span></span>
<span class="line"><span>│       │   │   │   ├── UpdateManager.ts</span></span>
<span class="line"><span>│       │   │   │   └── FileManager.ts</span></span>
<span class="line"><span>│       │   │   ├── services/</span></span>
<span class="line"><span>│       │   │   │   ├── AiRouter.ts</span></span>
<span class="line"><span>│       │   │   │   ├── LexiconEngine.ts</span></span>
<span class="line"><span>│       │   │   │   ├── TranslationMemory.ts</span></span>
<span class="line"><span>│       │   │   │   ├── ConsistencyChecker.ts</span></span>
<span class="line"><span>│       │   │   │   ├── QualityChecker.ts</span></span>
<span class="line"><span>│       │   │   │   ├── ExportEngine.ts</span></span>
<span class="line"><span>│       │   │   │   └── PluginHost.ts</span></span>
<span class="line"><span>│       │   │   ├── workers/</span></span>
<span class="line"><span>│       │   │   │   └── AgentWorker.ts</span></span>
<span class="line"><span>│       │   │   └── utils/</span></span>
<span class="line"><span>│       │   │       ├── logger.ts</span></span>
<span class="line"><span>│       │   │       ├── paths.ts</span></span>
<span class="line"><span>│       │   │       └── errors.ts</span></span>
<span class="line"><span>│       │   ├── preload/</span></span>
<span class="line"><span>│       │   │   └── index.ts</span></span>
<span class="line"><span>│       │   └── renderer/</span></span>
<span class="line"><span>│       │       ├── index.html</span></span>
<span class="line"><span>│       │       ├── src/</span></span>
<span class="line"><span>│       │       │   ├── main.ts</span></span>
<span class="line"><span>│       │       │   ├── App.vue</span></span>
<span class="line"><span>│       │       │   ├── router/</span></span>
<span class="line"><span>│       │       │   ├── stores/</span></span>
<span class="line"><span>│       │       │   ├── views/</span></span>
<span class="line"><span>│       │       │   ├── components/</span></span>
<span class="line"><span>│       │       │   ├── composables/</span></span>
<span class="line"><span>│       │       │   ├── services/</span></span>
<span class="line"><span>│       │       │   │   └── ipc.ts</span></span>
<span class="line"><span>│       │       │   └── types/</span></span>
<span class="line"><span>│       │       └── package.json</span></span>
<span class="line"><span>│       └── tests/</span></span>
<span class="line"><span>│           ├── e2e/</span></span>
<span class="line"><span>│           └── unit/</span></span>
<span class="line"><span>├── packages/</span></span>
<span class="line"><span>│   ├── shared/                           # types + schemas partagés</span></span>
<span class="line"><span>│   │   ├── src/</span></span>
<span class="line"><span>│   │   │   ├── types/</span></span>
<span class="line"><span>│   │   │   ├── schemas/</span></span>
<span class="line"><span>│   │   │   └── constants.ts</span></span>
<span class="line"><span>│   │   └── package.json</span></span>
<span class="line"><span>│   └── agent-contracts/                  # définitions des agents</span></span>
<span class="line"><span>│       ├── src/</span></span>
<span class="line"><span>│       │   ├── contracts/</span></span>
<span class="line"><span>│       │   ├── prompts/</span></span>
<span class="line"><span>│       │   └── tests/</span></span>
<span class="line"><span>│       └── package.json</span></span>
<span class="line"><span>├── docs/                                 # ce SDD (dépôt NovelTrad-Documentation séparé)</span></span>
<span class="line"><span>│   ├── volumes/</span></span>
<span class="line"><span>│   ├── examples/</span></span>
<span class="line"><span>│   ├── assets/</span></span>
<span class="line"><span>│   └── .vitepress/</span></span>
<span class="line"><span>├── scripts/</span></span>
<span class="line"><span>│   ├── setup-dev.js</span></span>
<span class="line"><span>│   └── build.js</span></span>
<span class="line"><span>├── tests/</span></span>
<span class="line"><span>│   └── fixtures/</span></span>
<span class="line"><span>└── package.json</span></span></code></pre></div><h2 id="_1-4-design-patterns" tabindex="-1">1.4 Design Patterns <a class="header-anchor" href="#_1-4-design-patterns" aria-label="Permalink to &quot;1.4 Design Patterns&quot;">​</a></h2><table tabindex="0"><thead><tr><th>Pattern</th><th>Usage</th></tr></thead><tbody><tr><td><strong>Repository</strong></td><td>Isoler SQL dans <code>repositories/*.ts</code> (Projects, Chapters, Lexicon, etc.).</td></tr><tr><td><strong>Factory</strong></td><td>Créer les instances d’agent selon le type d’étape (<code>AgentFactory</code>).</td></tr><tr><td><strong>Observer</strong></td><td>Événements workflow publiés via EventEmitter et WebSocket-like IPC.</td></tr><tr><td><strong>Command</strong></td><td>Chaque étape workflow = commande avec <code>execute()</code>, <code>undo()</code>, <code>retry()</code>.</td></tr><tr><td><strong>Strategy</strong></td><td>Choisir le provider IA (Ollama, OpenAI, etc.) via <code>ModelStrategy</code>.</td></tr><tr><td><strong>Dependency Injection</strong></td><td>Managers injectés dans le moteur via un <code>Container</code> simple (pas de framework lourd).</td></tr></tbody></table><h2 id="_1-5-gestion-des-erreurs" tabindex="-1">1.5 Gestion des erreurs <a class="header-anchor" href="#_1-5-gestion-des-erreurs" aria-label="Permalink to &quot;1.5 Gestion des erreurs&quot;">​</a></h2><ul><li>Toute erreur métier hérite de <code>NovelTradError</code>.</li><li>Erreurs propagées au renderer via <code>{ type: &#39;error&#39;, code, message, details }</code>.</li><li>Retry avec backoff exponentiel sur les appels réseau.</li><li>Circuit breaker pour Ollama : si 3 échecs consécutifs, on marque le provider comme indisponible.</li></ul><h2 id="_1-6-gestion-memoire-et-multi-thread" tabindex="-1">1.6 Gestion mémoire et multi-thread <a class="header-anchor" href="#_1-6-gestion-memoire-et-multi-thread" aria-label="Permalink to &quot;1.6 Gestion mémoire et multi-thread&quot;">​</a></h2><ul><li>Le main process ne fait pas de traitement LLM direct.</li><li>Les agents tournent dans <code>Worker</code> threads via <code>new Worker(path)</code>.</li><li>Les gros fichiers sont streamés, jamais chargés entièrement en RAM.</li><li>Limite de concurrence configurable : <code>maxConcurrentJobs</code> (défaut 1 modèle Ollama local).</li></ul><h2 id="✅-criteres-d-acceptation-de-l-architecture" tabindex="-1">✅ Critères d’acceptation de l’architecture <a class="header-anchor" href="#✅-criteres-d-acceptation-de-l-architecture" aria-label="Permalink to &quot;✅ Critères d’acceptation de l’architecture&quot;">​</a></h2><ul><li>[ ] L’arborescence est créée et compilable (<code>npm run build</code>).</li><li>[ ] Un preload script sécurisé expose uniquement les API nécessaires au renderer.</li><li>[ ] Le main process ne contient pas de logique UI.</li><li>[ ] Chaque manager/service a une interface TypeScript et un test unitaire.</li><li>[ ] Le workflow s’exécute dans un worker thread sans bloquer l’UI.</li></ul>`,35)])])}const u=a(t,[["render",l]]);export{k as __pageData,u as default};

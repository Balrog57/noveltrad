import{_ as a,o as n,c as i,a2 as e}from"./chunks/framework.L3mmv3XT.js";const o=JSON.parse('{"title":"Diagramme de séquence — Lancer un workflow","description":"","frontmatter":{},"headers":[],"relativePath":"assets/diagrams/sequence.md","filePath":"assets/diagrams/sequence.md","lastUpdated":1782934788000}'),t={name:"assets/diagrams/sequence.md"};function l(p,s,r,E,h,k){return n(),i("div",null,[...s[0]||(s[0]=[e(`<h1 id="diagramme-de-sequence-—-lancer-un-workflow" tabindex="-1">Diagramme de séquence — Lancer un workflow <a class="header-anchor" href="#diagramme-de-sequence-—-lancer-un-workflow" aria-label="Permalink to &quot;Diagramme de séquence — Lancer un workflow&quot;">​</a></h1><div class="language-mermaid vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">mermaid</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">sequenceDiagram</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    participant U as Utilisateur</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    participant R as Renderer</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    participant M as Main Process</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    participant W as WorkflowEngine</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    participant A as AgentRunner</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    participant O as Ollama</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    U-&gt;&gt;R: Clique &quot;Traduire le chapitre&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    R-&gt;&gt;M: workflow:start(chapterId)</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    M-&gt;&gt;W: createJob()</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    W-&gt;&gt;M: workflow:started</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    M-&gt;&gt;R: workflow:started</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    loop Pour chaque étape</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        W-&gt;&gt;A: runStep()</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A-&gt;&gt;O: chat()</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        O--&gt;&gt;A: response</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        A--&gt;&gt;W: output</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        W-&gt;&gt;M: workflow:step-completed</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        M-&gt;&gt;R: workflow:step-completed</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    end</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    W-&gt;&gt;M: workflow:completed</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    M-&gt;&gt;R: workflow:completed</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    R-&gt;&gt;U: Affiche score + export</span></span></code></pre></div>`,2)])])}const d=a(t,[["render",l]]);export{o as __pageData,d as default};

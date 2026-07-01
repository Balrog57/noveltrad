import{_ as a,o as i,c as t,a2 as n}from"./chunks/framework.L3mmv3XT.js";const d=JSON.parse('{"title":"Diagramme du workflow","description":"","frontmatter":{},"headers":[],"relativePath":"assets/diagrams/workflow.md","filePath":"assets/diagrams/workflow.md","lastUpdated":1782934788000}'),e={name:"assets/diagrams/workflow.md"};function l(p,s,o,r,E,h){return i(),t("div",null,[...s[0]||(s[0]=[n(`<h1 id="diagramme-du-workflow" tabindex="-1">Diagramme du workflow <a class="header-anchor" href="#diagramme-du-workflow" aria-label="Permalink to &quot;Diagramme du workflow&quot;">​</a></h1><div class="language-mermaid vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">mermaid</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">flowchart TD</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    A[&quot;Chapitre source&quot;] --&gt; B[&quot;Découpage&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    B --&gt; C[&quot;Pré-traduction&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    C --&gt; D[&quot;Traduction IA&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    D --&gt; E[&quot;Cohérence&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    E --&gt;|OK| F[&quot;Lexique&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    E --&gt;|KO| P[&quot;Pause / Retry&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    F --&gt; G[&quot;Grammaire&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    G --&gt; H[&quot;Style&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    H --&gt; I[&quot;Polish&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    I --&gt; J[&quot;QA&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    J --&gt;|score &gt;= 90| K[&quot;Export&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    J --&gt;|score 70-89| L[&quot;Relance étape faible&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    J --&gt;|score &lt; 70| P</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    K --&gt; M[&quot;Chapitre publiable&quot;]</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    L --&gt; D</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">    P --&gt; D</span></span></code></pre></div>`,2)])])}const u=a(e,[["render",l]]);export{d as __pageData,u as default};

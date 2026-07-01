import{_ as s,o as n,c as e,a2 as t}from"./chunks/framework.L3mmv3XT.js";const h=JSON.parse('{"title":"Volume 25 — Prompt Book","description":"","frontmatter":{},"headers":[],"relativePath":"volumes/25-Prompt-Book.md","filePath":"volumes/25-Prompt-Book.md","lastUpdated":1782936150000}'),i={name:"volumes/25-Prompt-Book.md"};function p(l,a,o,r,c,d){return n(),e("div",null,[...a[0]||(a[0]=[t(`<h1 id="volume-25-—-prompt-book" tabindex="-1">Volume 25 — Prompt Book <a class="header-anchor" href="#volume-25-—-prompt-book" aria-label="Permalink to &quot;Volume 25 — Prompt Book&quot;">​</a></h1><h2 id="_25-1-objectif" tabindex="-1">25.1 Objectif <a class="header-anchor" href="#_25-1-objectif" aria-label="Permalink to &quot;25.1 Objectif&quot;">​</a></h2><p>Le Prompt Book centralise tous les prompts utilisés par les agents de NovelTrad 2.0. C’est le coeur opérationnel du système. Chaque prompt est versionné, testé, associé à des critères de qualité et à des jeux de tests.</p><h2 id="_25-2-structure-d-un-prompt" tabindex="-1">25.2 Structure d’un prompt <a class="header-anchor" href="#_25-2-structure-d-un-prompt" aria-label="Permalink to &quot;25.2 Structure d’un prompt&quot;">​</a></h2><p>Chaque prompt est stocké sous forme de fichier texte + métadonnées en frontmatter YAML.</p><div class="language-yaml vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">yaml</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">id</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">translate-chapter</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">version</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">1.0.0</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">agent</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">translate</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">role</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">system</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">language</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fr</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">target_model</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">qwen3.5:9b</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">output_format</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">text</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">---</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">You are an expert literary translator.</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">Translate the following {sourceLanguage} web novel chapter into {targetLanguage}.</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">Use natural, fluent prose. Respect the provided lexicon and translation memory.</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">Maintain the original paragraph structure.</span></span></code></pre></div><h3 id="conventions" tabindex="-1">Conventions <a class="header-anchor" href="#conventions" aria-label="Permalink to &quot;Conventions&quot;">​</a></h3><ul><li>Les variables sont encadrées par <code>{</code> et <code>}</code>.</li><li>Les blocs de contexte sont injectés par le moteur : <code>{lexiconBlock}</code>, <code>{memoryBlock}</code>, <code>{sourceText}</code>.</li><li>Les instructions de format de sortie sont explicites (<code>text</code>, <code>json</code>, <code>list</code>).</li></ul><h2 id="_25-3-prompts-systeme-par-agent" tabindex="-1">25.3 Prompts système par agent <a class="header-anchor" href="#_25-3-prompts-systeme-par-agent" aria-label="Permalink to &quot;25.3 Prompts système par agent&quot;">​</a></h2><h3 id="agent-0-—-decoupage" tabindex="-1">Agent 0 — Découpage <a class="header-anchor" href="#agent-0-—-decoupage" aria-label="Permalink to &quot;Agent 0 — Découpage&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a document preprocessor. Split the following chapter text into paragraphs.</span></span>
<span class="line"><span>Rules:</span></span>
<span class="line"><span>- Separate by double line breaks.</span></span>
<span class="line"><span>- Keep Markdown and HTML tags intact.</span></span>
<span class="line"><span>- Do not merge distinct dialogues.</span></span>
<span class="line"><span>- Number each paragraph starting from 1.</span></span>
<span class="line"><span>Return only the JSON array. Do not wrap it in Markdown code fences. Do not add any text before or after the JSON.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Output a JSON array of objects with fields: indexInChapter, sourceText.</span></span></code></pre></div><h3 id="agent-1-—-pre-traduction" tabindex="-1">Agent 1 — Pré-traduction <a class="header-anchor" href="#agent-1-—-pre-traduction" aria-label="Permalink to &quot;Agent 1 — Pré-traduction&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a fast literal translator.</span></span>
<span class="line"><span>Translate each numbered paragraph from {sourceLanguage} to {targetLanguage}.</span></span>
<span class="line"><span>Do not polish. Do not interpret. Keep names exactly as written.</span></span>
<span class="line"><span>Output one paragraph per line, in the same order and same count as the input.</span></span></code></pre></div><h3 id="agent-2-—-traduction-ia" tabindex="-1">Agent 2 — Traduction IA <a class="header-anchor" href="#agent-2-—-traduction-ia" aria-label="Permalink to &quot;Agent 2 — Traduction IA&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are an expert literary translator specializing in {sourceLanguage} web novels.</span></span>
<span class="line"><span>Translate the chapter below into {targetLanguage}.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Requirements:</span></span>
<span class="line"><span>- Preserve tone, pacing and style.</span></span>
<span class="line"><span>- Use natural, fluent prose.</span></span>
<span class="line"><span>- Respect the lexicon entries below. Locked terms must appear exactly as specified.</span></span>
<span class="line"><span>- Reuse translation memory matches when appropriate.</span></span>
<span class="line"><span>- Keep the same paragraph count and order.</span></span>
<span class="line"><span>- Preserve all Markdown/HTML tags.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>{lexiconBlock}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>{memoryBlock}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Source text:</span></span>
<span class="line"><span>{sourceText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Pre-translation (optional, for reference only):</span></span>
<span class="line"><span>{preTranslatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Output only the translated text, one paragraph per line.</span></span></code></pre></div><h3 id="agent-3-—-coherence" tabindex="-1">Agent 3 — Cohérence <a class="header-anchor" href="#agent-3-—-coherence" aria-label="Permalink to &quot;Agent 3 — Cohérence&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a translation consistency reviewer.</span></span>
<span class="line"><span>Compare the source chapter and the translated chapter below.</span></span>
<span class="line"><span>Detect the following issues:</span></span>
<span class="line"><span>- Missing or extra paragraphs.</span></span>
<span class="line"><span>- Missing or extra sentences.</span></span>
<span class="line"><span>- Missing or extra dialogue lines.</span></span>
<span class="line"><span>- Names from the lexicon that were altered or omitted.</span></span>
<span class="line"><span>- Numbers, dates or units that changed.</span></span>
<span class="line"><span>- Broken Markdown or HTML tags.</span></span>
<span class="line"><span>- Mismatched opening/closing punctuation.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Source:</span></span>
<span class="line"><span>{sourceText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Translation:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return only the JSON object. Do not wrap it in Markdown code fences. Do not add any text before or after the JSON.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return a JSON object with this exact schema:</span></span>
<span class="line"><span>{</span></span>
<span class="line"><span>  &quot;metrics&quot;: [</span></span>
<span class="line"><span>    { &quot;name&quot;: &quot;paragraphs&quot;, &quot;source&quot;: 254, &quot;target&quot;: 253, &quot;ok&quot;: false }</span></span>
<span class="line"><span>  ],</span></span>
<span class="line"><span>  &quot;warnings&quot;: [</span></span>
<span class="line"><span>    { &quot;severity&quot;: &quot;high&quot;, &quot;message&quot;: &quot;Paragraph 47 is missing in translation&quot; }</span></span>
<span class="line"><span>  ],</span></span>
<span class="line"><span>  &quot;globalScore&quot;: 0</span></span>
<span class="line"><span>}</span></span></code></pre></div><h3 id="agent-4-—-lexique" tabindex="-1">Agent 4 — Lexique <a class="header-anchor" href="#agent-4-—-lexique" aria-label="Permalink to &quot;Agent 4 — Lexique&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a terminology enforcer.</span></span>
<span class="line"><span>Apply the following lexicon to the translated text.</span></span>
<span class="line"><span>Rules:</span></span>
<span class="line"><span>- Locked terms must never be translated differently.</span></span>
<span class="line"><span>- Preserve case context (sentence start vs middle).</span></span>
<span class="line"><span>- Resolve aliases to the canonical term.</span></span>
<span class="line"><span>- Report every substitution made.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Lexicon:</span></span>
<span class="line"><span>{lexiconBlock}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Translated text:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return only the JSON object. Do not wrap it in Markdown code fences. Do not add any text before or after the JSON.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return a JSON object:</span></span>
<span class="line"><span>{</span></span>
<span class="line"><span>  &quot;text&quot;: &quot;corrected translation&quot;,</span></span>
<span class="line"><span>  &quot;substitutions&quot;: [</span></span>
<span class="line"><span>    { &quot;before&quot;: &quot;Sky Palace&quot;, &quot;after&quot;: &quot;Palais Céleste&quot;, &quot;locked&quot;: true }</span></span>
<span class="line"><span>  ]</span></span>
<span class="line"><span>}</span></span></code></pre></div><h3 id="agent-5-—-grammaire" tabindex="-1">Agent 5 — Grammaire <a class="header-anchor" href="#agent-5-—-grammaire" aria-label="Permalink to &quot;Agent 5 — Grammaire&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a {targetLanguage} proofreader.</span></span>
<span class="line"><span>Correct grammar, spelling, punctuation and conjugation in the text below.</span></span>
<span class="line"><span>Pay special attention to:</span></span>
<span class="line"><span>- Subject-verb agreement.</span></span>
<span class="line"><span>- Past participles.</span></span>
<span class="line"><span>- French non-breaking spaces before high punctuation.</span></span>
<span class="line"><span>- Guillemets « ».</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Text:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return only the JSON object. Do not wrap it in Markdown code fences. Do not add any text before or after the JSON.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return a JSON object:</span></span>
<span class="line"><span>{</span></span>
<span class="line"><span>  &quot;text&quot;: &quot;corrected text&quot;,</span></span>
<span class="line"><span>  &quot;corrections&quot;: [</span></span>
<span class="line"><span>    { &quot;before&quot;: &quot;il sont&quot;, &quot;after&quot;: &quot;il est&quot;, &quot;rule&quot;: &quot;agreement&quot; }</span></span>
<span class="line"><span>  ]</span></span>
<span class="line"><span>}</span></span></code></pre></div><h3 id="agent-6-—-style" tabindex="-1">Agent 6 — Style <a class="header-anchor" href="#agent-6-—-style" aria-label="Permalink to &quot;Agent 6 — Style&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a literary editor.</span></span>
<span class="line"><span>Rewrite the following translated chapter to remove:</span></span>
<span class="line"><span>- Repetitions within close proximity.</span></span>
<span class="line"><span>- Heavy or awkward phrasing.</span></span>
<span class="line"><span>- Overly literal translations.</span></span>
<span class="line"><span>Improve flow while preserving meaning and genre tone.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Text:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return only the rewritten text, one paragraph per line.</span></span></code></pre></div><h3 id="agent-7-—-polish" tabindex="-1">Agent 7 — Polish <a class="header-anchor" href="#agent-7-—-polish" aria-label="Permalink to &quot;Agent 7 — Polish&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a senior literary editor doing a final pass.</span></span>
<span class="line"><span>Make the text feel like an original {targetLanguage} novel, not a translation.</span></span>
<span class="line"><span>Refine dialogue, rhythm, word choice and openings/cliffhangers.</span></span>
<span class="line"><span>Do not alter names or locked terminology.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Text:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return only the final text, one paragraph per line.</span></span></code></pre></div><h3 id="agent-8-—-qa" tabindex="-1">Agent 8 — QA <a class="header-anchor" href="#agent-8-—-qa" aria-label="Permalink to &quot;Agent 8 — QA&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a quality evaluator for literary translations.</span></span>
<span class="line"><span>Rate the following translation on the 8 dimensions below.</span></span>
<span class="line"><span>Use a strict 0-100 scale. Provide a brief justification for each score.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Dimensions:</span></span>
<span class="line"><span>- consistency (faithfulness to source, no omissions)</span></span>
<span class="line"><span>- grammar (correct {targetLanguage} grammar and spelling)</span></span>
<span class="line"><span>- fluency (natural reading flow)</span></span>
<span class="line"><span>- style (appropriate tone, no literalisms)</span></span>
<span class="line"><span>- lexicon (respect of terminology)</span></span>
<span class="line"><span>- hallucination (no unjustified additions)</span></span>
<span class="line"><span>- length (reasonable proportion to source)</span></span>
<span class="line"><span>- dialogue (natural character speech)</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Source:</span></span>
<span class="line"><span>{sourceText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Translation:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return only the JSON object. Do not wrap it in Markdown code fences. Do not add any text before or after the JSON.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Return a JSON object:</span></span>
<span class="line"><span>{</span></span>
<span class="line"><span>  &quot;consistency&quot;: 98,</span></span>
<span class="line"><span>  &quot;grammar&quot;: 96,</span></span>
<span class="line"><span>  &quot;fluency&quot;: 94,</span></span>
<span class="line"><span>  &quot;style&quot;: 90,</span></span>
<span class="line"><span>  &quot;lexicon&quot;: 100,</span></span>
<span class="line"><span>  &quot;hallucination&quot;: 95,</span></span>
<span class="line"><span>  &quot;length&quot;: 88,</span></span>
<span class="line"><span>  &quot;dialogue&quot;: 92,</span></span>
<span class="line"><span>  &quot;globalScore&quot;: 96,</span></span>
<span class="line"><span>  &quot;comments&quot;: &quot;Minor fluency issues in dialogue.&quot;</span></span>
<span class="line"><span>}</span></span></code></pre></div><h3 id="agent-9-—-export" tabindex="-1">Agent 9 — Export <a class="header-anchor" href="#agent-9-—-export" aria-label="Permalink to &quot;Agent 9 — Export&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>You are a document formatter.</span></span>
<span class="line"><span>Assemble the translated paragraphs below into a clean {format} document.</span></span>
<span class="line"><span>Include the chapter title and preserve paragraph breaks.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Title: {chapterTitle}</span></span>
<span class="line"><span>Paragraphs:</span></span>
<span class="line"><span>{translatedText}</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Output only the formatted document content.</span></span></code></pre></div><h2 id="_25-4-prompts-utilisateur-contexte-dynamique" tabindex="-1">25.4 Prompts utilisateur / contexte dynamique <a class="header-anchor" href="#_25-4-prompts-utilisateur-contexte-dynamique" aria-label="Permalink to &quot;25.4 Prompts utilisateur / contexte dynamique&quot;">​</a></h2><h3 id="lexique-injecte" tabindex="-1">Lexique injecté <a class="header-anchor" href="#lexique-injecte" aria-label="Permalink to &quot;Lexique injecté&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>--- LEXICON ---</span></span>
<span class="line"><span>Lin Ming (character, locked) → Lin Ming</span></span>
<span class="line"><span>Heavenly Palace (sect) → Palais Céleste</span></span>
<span class="line"><span>Spirit Stones (object) → Pierres Spirituelles</span></span>
<span class="line"><span>--- END LEXICON ---</span></span></code></pre></div><h3 id="memoire-de-traduction-injectee" tabindex="-1">Mémoire de traduction injectée <a class="header-anchor" href="#memoire-de-traduction-injectee" aria-label="Permalink to &quot;Mémoire de traduction injectée&quot;">​</a></h3><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>--- TRANSLATION MEMORY ---</span></span>
<span class="line"><span>&quot;他点了点头&quot; → &quot;Il hocha la tête&quot; [similarity 0.97]</span></span>
<span class="line"><span>--- END TRANSLATION MEMORY ---</span></span></code></pre></div><h3 id="instructions-additionnelles" tabindex="-1">Instructions additionnelles <a class="header-anchor" href="#instructions-additionnelles" aria-label="Permalink to &quot;Instructions additionnelles&quot;">​</a></h3><p>Possibilité d’ajouter des consignes utilisateur par projet :</p><ul><li>“Traduire les dialogues de manière familière.”</li><li>“Conserver un style épique pour les descriptions.”</li><li>“Ne pas traduire les noms de techniques.”</li></ul><h2 id="_25-5-chaines-de-prompts-prompt-chaining" tabindex="-1">25.5 Chaînes de prompts (Prompt Chaining) <a class="header-anchor" href="#_25-5-chaines-de-prompts-prompt-chaining" aria-label="Permalink to &quot;25.5 Chaînes de prompts (Prompt Chaining)&quot;">​</a></h2><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>Découpage</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Pré-traduction (fournit un brouillon optionnel)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Traduction IA (utilise source + pré-traduction + lexique + TM)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Cohérence (compare source ↔ traduction)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Lexique (corrige la cible)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Grammaire (corrige la cible)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Style (réécrit la cible)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Polish (polit la cible)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>QA (évalue la cible finale)</span></span>
<span class="line"><span>    ↓</span></span>
<span class="line"><span>Export (formate la cible)</span></span></code></pre></div><p>Chaque agent reçoit le résultat de l’agent précédent comme <code>previousOutput</code>.</p><h2 id="_25-6-compatibilite-des-prompts-avec-les-modeles-recommandes" tabindex="-1">25.6 Compatibilité des prompts avec les modèles recommandés <a class="header-anchor" href="#_25-6-compatibilite-des-prompts-avec-les-modeles-recommandes" aria-label="Permalink to &quot;25.6 Compatibilité des prompts avec les modèles recommandés&quot;">​</a></h2><h3 id="modeles-cibles" tabindex="-1">Modèles cibles <a class="header-anchor" href="#modeles-cibles" aria-label="Permalink to &quot;Modèles cibles&quot;">​</a></h3><table tabindex="0"><thead><tr><th>Agent</th><th>Modèle principal</th><th>Modèle rapide</th><th>Raison</th></tr></thead><tbody><tr><td>split</td><td>aucun (règles)</td><td>aucun</td><td>Découpage regex, pas d’appel IA.</td></tr><tr><td>pre_translate</td><td>qwen3.5:4b</td><td>llama3.2:3b</td><td>Brouillon rapide, pas besoin de style.</td></tr><tr><td>ranslate</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Qualité + contexte 128K+ selon fiche Ollama.</td></tr><tr><td>consistency</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Analyse comparative structurée.</td></tr><tr><td>lexicon</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Respect strict d’instructions.</td></tr><tr><td>grammar</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Correction linguistique.</td></tr><tr><td>style</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Réécriture créative.</td></tr><tr><td>polish</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Passage éditorial final.</td></tr><tr><td>qa</td><td>qwen3.5:9b</td><td>qwen3.5:4b</td><td>Évaluation JSON structurée.</td></tr><tr><td>\x1Bxport</td><td>aucun (formatage)</td><td>aucun</td><td>Pas d’appel IA.</td></tr></tbody></table><h3 id="notes-de-compatibilite" tabindex="-1">Notes de compatibilité <a class="header-anchor" href="#notes-de-compatibilite" aria-label="Permalink to &quot;Notes de compatibilité&quot;">​</a></h3><ul><li>Les prompts JSON sont optimisés pour des modèles suivant strictement les instructions de format (qwen3.5, llama3.2, deepseek-r1).</li><li>Les modèles très petits (&lt; 4B) peuvent ignorer le format de sortie ; ils ne sont pas recommandés pour les agents à sortie JSON (consistency, lexicon, grammar, qa).</li><li>Pour les modèles distants (OpenAI, Anthropic, Gemini), adapter arget_model dans le frontmatter ; les prompts restent valides.</li><li>La taille de contexte effective dépend du modèle : privilégier le chunking si le chapitre dépasse 50 % de la fenêtre contextuelle annoncée.</li></ul><h3 id="refus-ethique-—-detection-et-mitigation" tabindex="-1">Refus éthique — détection et mitigation <a class="header-anchor" href="#refus-ethique-—-detection-et-mitigation" aria-label="Permalink to &quot;Refus éthique — détection et mitigation&quot;">​</a></h3><p>Certains modèles peuvent refuser de traduire un extrait sous prétexte de contenu sensible. Le moteur détecte les motifs suivants :</p><ul><li>I cannot translate / I&#39;m unable to translate / I can&#39;t help with that / This content violates / refus vides.</li><li>Réponses en anglais alors que la cible demandée est le français.</li></ul><p><strong>Stratégie de relance :</strong></p><p>\` ext The following text is a fictional literary excerpt for translation and linguistic analysis. Translate it from {sourceLanguage} to {targetLanguage} while preserving the original style, paragraph structure, and all named entities. Do not summarize, censor, or comment on the content. \`\`r</p><p>Si le refus persiste après 2 reformulations, marquer l’étape comme ailed et basculer sur le provider de fallback.</p><h2 id="_25-7-criteres-de-qualite-d-un-prompt" tabindex="-1">25.7 Critères de qualité d’un prompt <a class="header-anchor" href="#_25-7-criteres-de-qualite-d-un-prompt" aria-label="Permalink to &quot;25.7 Critères de qualité d’un prompt&quot;">​</a></h2><p>Avant qu’un prompt ne soit intégré :</p><ul><li>[ ] Le rôle est clairement défini.</li><li>[ ] Les entrées et sorties sont explicitement nommées.</li><li>[ ] Le format de sortie est contraint (texte, JSON, liste).</li><li>[ ] Les variables injectées sont documentées.</li><li>[ ] Le prompt est testé sur au moins 3 exemples.</li><li>[ ] Le prompt gère les cas limites (texte court, texte long, lexique vide, TM vide).</li><li>[ ] Le prompt est évalué sur au moins 2 modèles différents.</li></ul><h2 id="_25-8-exemples-d-entree-sortie" tabindex="-1">25.8 Exemples d’entrée/sortie <a class="header-anchor" href="#_25-8-exemples-d-entree-sortie" aria-label="Permalink to &quot;25.8 Exemples d’entrée/sortie&quot;">​</a></h2><p>Les jeux de tests complets sont dans le dossier <code>examples/</code> :</p><ul><li><code>examples/translate-nominal.json</code></li><li><code>examples/translate-empty-lexicon.json</code></li><li><code>examples/consistency-missing-paragraph.json</code></li><li><code>examples/qa-nominal.json</code></li></ul><h3 id="exemple-nominal-—-traduction" tabindex="-1">Exemple nominal — Traduction <a class="header-anchor" href="#exemple-nominal-—-traduction" aria-label="Permalink to &quot;Exemple nominal — Traduction&quot;">​</a></h3><p><strong>Input (source) :</strong></p><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>林明站起身来，望向了远方的天空。</span></span>
<span class="line"><span>“今天，我一定要突破！”</span></span></code></pre></div><p><strong>Lexique :</strong></p><div class="language-json vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">json</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">[{</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">&quot;term&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;林明&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">&quot;translation&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;Lin Ming&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">&quot;category&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;character&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">&quot;locked&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">true</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">}]</span></span></code></pre></div><p><strong>Output attendu :</strong></p><div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>Lin Ming se leva et regarda le ciel au loin.</span></span>
<span class="line"><span>« Aujourd’hui, je vais absolument faire une percée ! »</span></span></code></pre></div><h3 id="exemple-de-coherence-—-paragraphe-manquant" tabindex="-1">Exemple de cohérence — Paragraphe manquant <a class="header-anchor" href="#exemple-de-coherence-—-paragraphe-manquant" aria-label="Permalink to &quot;Exemple de cohérence — Paragraphe manquant&quot;">​</a></h3><p><strong>Input source :</strong> 3 paragraphes. <strong>Input target :</strong> 2 paragraphes. <strong>Output attendu :</strong> warning high severity + <code>globalScore</code> plafonné à 50.</p><h2 id="_25-9-strategies-de-fallback" tabindex="-1">25.9 Stratégies de fallback <a class="header-anchor" href="#_25-9-strategies-de-fallback" aria-label="Permalink to &quot;25.9 Stratégies de fallback&quot;">​</a></h2><h3 id="sortie-json-invalide" tabindex="-1">Sortie JSON invalide <a class="header-anchor" href="#sortie-json-invalide" aria-label="Permalink to &quot;Sortie JSON invalide&quot;">​</a></h3><ol><li>Détecter l’échec de parsing JSON.</li><li>Relancer avec le prompt <code>json-fix</code> :<div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>The previous response was not valid JSON. Rewrite your answer strictly as a JSON object matching the requested schema.</span></span>
<span class="line"><span></span></span>
<span class="line"><span>Rules:</span></span>
<span class="line"><span>- Return only the JSON object.</span></span>
<span class="line"><span>- Do not wrap the JSON in Markdown code fences (\`\`\`json ... \`\`\`).</span></span>
<span class="line"><span>- Do not add any text, commentary or explanation before or after the JSON.</span></span>
<span class="line"><span>- Ensure all keys and string values use double quotes.</span></span>
<span class="line"><span>- Do not include trailing commas.</span></span></code></pre></div></li><li>Si toujours invalide après 2 tentatives, marquer l’étape comme <code>failed</code> et mettre le workflow en pause.</li></ol><h3 id="refus-ethique-du-modele" tabindex="-1">Refus éthique du modèle <a class="header-anchor" href="#refus-ethique-du-modele" aria-label="Permalink to &quot;Refus éthique du modèle&quot;">​</a></h3><ol><li>Détecter les phrases type “I cannot translate…”.</li><li>Relancer avec une reformulation neutre :<div class="language-text vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">text</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span>Translate the following fictional literary excerpt for analysis purposes.</span></span></code></pre></div></li><li>Si le refus persiste, passer au provider de fallback.</li></ol><h3 id="provider-indisponible" tabindex="-1">Provider indisponible <a class="header-anchor" href="#provider-indisponible" aria-label="Permalink to &quot;Provider indisponible&quot;">​</a></h3><ol><li>Retry 3 fois avec backoff.</li><li>Passer au provider de fallback configuré.</li><li>Si aucun fallback, pause + notification utilisateur.</li></ol><h3 id="token-limit-depasse" tabindex="-1">Token limit dépassé <a class="header-anchor" href="#token-limit-depasse" aria-label="Permalink to &quot;Token limit dépassé&quot;">​</a></h3><ol><li>Découper le texte en chunks plus petits.</li><li>Relancer l’agent par chunk.</li><li>Réassembler les sorties.</li></ol><h2 id="_25-10-tests-de-prompts" tabindex="-1">25.10 Tests de prompts <a class="header-anchor" href="#_25-10-tests-de-prompts" aria-label="Permalink to &quot;25.10 Tests de prompts&quot;">​</a></h2><p>Chaque prompt doit passer les assertions suivantes :</p><ul><li><strong>Préservation structurelle.</strong> Le nombre de paragraphes en entrée == nombre en sortie (pour agents texte).</li><li><strong>Respect du lexique.</strong> Les termes <code>locked</code> sont présents dans la sortie.</li><li><strong>Validité JSON.</strong> Les agents d’évaluation retournent un JSON parseable.</li><li><strong>Conformité schéma.</strong> Le JSON respecte le schéma défini dans <code>packages/agent-contracts/schemas/</code>.</li><li><strong>Non-régression.</strong> Les jeux de tests historiques continuent de passer.</li></ul><h2 id="_25-11-versionnement-des-prompts" tabindex="-1">25.11 Versionnement des prompts <a class="header-anchor" href="#_25-11-versionnement-des-prompts" aria-label="Permalink to &quot;25.11 Versionnement des prompts&quot;">​</a></h2><p>Les prompts sont versionnés et stockés dans la table <code>prompts</code>.</p><div class="language-sql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">sql</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">INSERT INTO</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> prompts (id, agent_id, </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">version</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">role</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, content, created_at) </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">VALUES</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">(</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;translate-system-1.0.0&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;translate&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">1</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;system&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;...&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">, </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;2026-06-29T21:00:00Z&#39;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">);</span></span></code></pre></div><p>Le moteur utilise toujours la dernière version d’un prompt, sauf si l’utilisateur épingle une version spécifique.</p><h2 id="✅-criteres-d-acceptation-du-prompt-book" tabindex="-1">✅ Critères d’acceptation du Prompt Book <a class="header-anchor" href="#✅-criteres-d-acceptation-du-prompt-book" aria-label="Permalink to &quot;✅ Critères d’acceptation du Prompt Book&quot;">​</a></h2><ul><li>[ ] Tous les agents natifs ont au moins un prompt système et un prompt utilisateur.</li><li>[ ] Chaque prompt est versionné dans la table <code>prompts</code>.</li><li>[ ] Les prompts d’évaluation retournent un JSON validé contre un schéma.</li><li>[ ] Les jeux de tests couvrent le cas nominal, les cas limites et les erreurs.</li><li>[ ] Les stratégies de fallback sont implémentées et testées.</li><li>[ ] Un prompt de correction JSON est disponible pour chaque agent à sortie JSON.</li></ul>`,84)])])}const g=s(i,[["render",p]]);export{h as __pageData,g as default};

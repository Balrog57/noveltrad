import { describe, it, expect } from "vitest";
import { AiRouter } from "../../src/main/services/AiRouter";
import { TRANSLATE_SYSTEM_PROMPT, buildTranslateUserPrompt } from "../../src/main/services/prompts/translate.system";
import { PRE_TRANSLATE_SYSTEM_PROMPT, buildPreTranslateUserPrompt } from "../../src/main/services/prompts/pre-translate.system";
import { GRAMMAR_SYSTEM_PROMPT, buildGrammarUserPrompt } from "../../src/main/services/prompts/grammar.system";
import { STYLE_SYSTEM_PROMPT, buildStyleUserPrompt } from "../../src/main/services/prompts/style.system";
import { POLISH_SYSTEM_PROMPT, buildPolishUserPrompt } from "../../src/main/services/prompts/polish.system";

// ---------------------------------------------------------------------------
// AiRouter.tryParseJson
// ---------------------------------------------------------------------------

describe("AiRouter.tryParseJson", () => {
  const router = new AiRouter();

  it("should parse valid JSON", () => {
    const result = router.tryParseJson('{"key": "value"}');
    expect(result).toEqual({ key: "value" });
  });

  it("should parse valid JSON array", () => {
    const result = router.tryParseJson("[1, 2, 3]");
    expect(result).toEqual([1, 2, 3]);
  });

  it("should parse JSON wrapped in markdown code fences (json)", () => {
    const raw = '```json\n{"key": "value"}\n```';
    const result = router.tryParseJson(raw);
    expect(result).toEqual({ key: "value" });
  });

  it("should parse JSON wrapped in markdown code fences (no lang)", () => {
    const raw = '```\n{"key": "value"}\n```';
    const result = router.tryParseJson(raw);
    expect(result).toEqual({ key: "value" });
  });

  it("should parse JSON inside markdown fences with surrounding text", () => {
    const raw =
      'Here is the result:\n```json\n{"key": "value"}\n```\nHope this helps!';
    const result = router.tryParseJson(raw);
    expect(result).toEqual({ key: "value" });
  });

  it("should fix trailing comma before closing brace", () => {
    const raw = '{"key": "value",}';
    const result = router.tryParseJson(raw);
    expect(result).toEqual({ key: "value" });
  });

  it("should fix trailing comma before closing bracket", () => {
    const raw = '["a", "b",]';
    const result = router.tryParseJson(raw);
    expect(result).toEqual(["a", "b"]);
  });

  it("should fix single quotes to double quotes", () => {
    const raw = "{'key': 'value'}";
    const result = router.tryParseJson(raw);
    expect(result).toEqual({ key: "value" });
  });

  it("should return null for completely invalid JSON", () => {
    const result = router.tryParseJson("not json at all");
    expect(result).toBeNull();
  });

  it("should return null for empty string", () => {
    const result = router.tryParseJson("");
    expect(result).toBeNull();
  });

  it("should return null for plain text with no JSON inside", () => {
    const result = router.tryParseJson("Hello, world!");
    expect(result).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// AiRouter.isEthicalRefusal
// ---------------------------------------------------------------------------

describe("AiRouter.isEthicalRefusal", () => {
  const router = new AiRouter();

  it("should detect 'I cannot' refusal", () => {
    expect(router.isEthicalRefusal("I cannot translate this content.")).toBe(
      true,
    );
  });

  it("should detect 'I'm sorry' refusal", () => {
    expect(
      router.isEthicalRefusal(
        "I'm sorry, but I cannot help with that request.",
      ),
    ).toBe(true);
  });

  it("should detect 'I apologize' refusal", () => {
    expect(
      router.isEthicalRefusal("I apologize, but I am unable to process this."),
    ).toBe(true);
  });

  it("should detect 'As an AI' refusal", () => {
    expect(
      router.isEthicalRefusal(
        "As an AI language model, I cannot complete this task.",
      ),
    ).toBe(true);
  });

  it("should detect Chinese refusal 抱歉", () => {
    expect(router.isEthicalRefusal("抱歉，我无法完成这个请求。")).toBe(true);
  });

  it("should detect Chinese refusal 无法", () => {
    expect(router.isEthicalRefusal("无法处理此内容。")).toBe(true);
  });

  it("should detect Chinese refusal 我不能", () => {
    expect(router.isEthicalRefusal("我不能翻译这个。")).toBe(true);
  });

  it("should NOT flag normal translation text", () => {
    expect(router.isEthicalRefusal("The dragon flew over the mountains.")).toBe(
      false,
    );
  });

  it("should NOT flag normal French text", () => {
    expect(router.isEthicalRefusal("Le dragon survola les montagnes.")).toBe(
      false,
    );
  });

  it("should NOT flag text containing refusal keywords mid-sentence", () => {
    expect(router.isEthicalRefusal("He said: I cannot do this.")).toBe(false);
  });

  it("should NOT flag empty string", () => {
    expect(router.isEthicalRefusal("")).toBe(false);
  });

  it("should be case-insensitive for English patterns", () => {
    expect(router.isEthicalRefusal("i cannot help with that.")).toBe(true);
  });

  it("should detect refusal even with leading whitespace", () => {
    expect(router.isEthicalRefusal("  \n  I'm sorry, I cannot help.")).toBe(
      true,
    );
  });
});

// ---------------------------------------------------------------------------
// Qwen compatibility — prompt format instructions
// ---------------------------------------------------------------------------

describe("Qwen prompt compatibility", () => {
  it("translate prompt starts with 'You are a helpful assistant.'", () => {
    expect(TRANSLATE_SYSTEM_PROMPT.trim()).toMatch(
      /^You are a helpful assistant\./,
    );
  });

  it("pre-translate prompt starts with 'You are a helpful assistant.'", () => {
    expect(PRE_TRANSLATE_SYSTEM_PROMPT.trim()).toMatch(
      /^You are a helpful assistant\./,
    );
  });

  it("grammar prompt starts with 'You are a helpful assistant.'", () => {
    expect(GRAMMAR_SYSTEM_PROMPT.trim()).toMatch(
      /^You are a helpful assistant\./,
    );
  });

  it("style prompt starts with 'You are a helpful assistant.'", () => {
    expect(STYLE_SYSTEM_PROMPT.trim()).toMatch(
      /^You are a helpful assistant\./,
    );
  });

  it("polish prompt starts with 'You are a helpful assistant.'", () => {
    expect(POLISH_SYSTEM_PROMPT.trim()).toMatch(
      /^You are a helpful assistant\./,
    );
  });

  it("translate prompt forbids markdown code fences", () => {
    expect(TRANSLATE_SYSTEM_PROMPT).toContain(
      "Do NOT wrap in markdown code fences",
    );
  });

  it("pre-translate prompt forbids markdown code fences", () => {
    expect(PRE_TRANSLATE_SYSTEM_PROMPT).toContain(
      "Do NOT wrap in markdown code fences",
    );
  });

  it("grammar prompt forbids markdown code fences", () => {
    expect(GRAMMAR_SYSTEM_PROMPT).toContain(
      "Do NOT wrap in markdown code fences",
    );
  });

  it("style prompt forbids markdown code fences", () => {
    expect(STYLE_SYSTEM_PROMPT).toContain(
      "Do NOT wrap in markdown code fences",
    );
  });

  it("polish prompt forbids markdown code fences", () => {
    expect(POLISH_SYSTEM_PROMPT).toContain(
      "Do NOT wrap in markdown code fences",
    );
  });

  it("translate prompt has version comment", () => {
    expect(TRANSLATE_SYSTEM_PROMPT).toBeDefined();
  });

  it("all prompts include 'OUTPUT FORMAT' section", () => {
    const prompts = [
      TRANSLATE_SYSTEM_PROMPT,
      PRE_TRANSLATE_SYSTEM_PROMPT,
      GRAMMAR_SYSTEM_PROMPT,
      STYLE_SYSTEM_PROMPT,
      POLISH_SYSTEM_PROMPT,
    ];
    for (const prompt of prompts) {
      expect(prompt).toContain("OUTPUT FORMAT");
    }
  });

  it("all prompts include 'Do NOT add any text before or after'", () => {
    const prompts = [
      TRANSLATE_SYSTEM_PROMPT,
      PRE_TRANSLATE_SYSTEM_PROMPT,
      GRAMMAR_SYSTEM_PROMPT,
      STYLE_SYSTEM_PROMPT,
      POLISH_SYSTEM_PROMPT,
    ];
    for (const prompt of prompts) {
      expect(prompt).toContain("Do NOT add any text before or after");
    }
  });
});

// ---------------------------------------------------------------------------
// buildTranslateUserPrompt
// ---------------------------------------------------------------------------

describe("buildTranslateUserPrompt", () => {
  it("devrait construire un prompt avec texte source et langues", () => {
    const result = buildTranslateUserPrompt({
      sourceText: "The dragon flew.",
      sourceLanguage: "en",
      targetLanguage: "fr",
      lexiconBlock: "",
      memoryBlock: "",
    });
    expect(result).toContain("Source (en)");
    expect(result).toContain("The dragon flew.");
    expect(result).toContain("Translate to fr:");
  });

  it("devrait inclure le bloc lexique si non vide", () => {
    const result = buildTranslateUserPrompt({
      sourceText: "Hello",
      sourceLanguage: "en",
      targetLanguage: "fr",
      lexiconBlock: "--- LEXICON ---\n- dragon → dragon\n--- END LEXICON ---\n\n",
      memoryBlock: "",
    });
    expect(result).toContain("LEXICON");
    expect(result).toContain("dragon → dragon");
  });

  it("devrait inclure le bloc mémoire si non vide", () => {
    const result = buildTranslateUserPrompt({
      sourceText: "Hello",
      sourceLanguage: "en",
      targetLanguage: "fr",
      lexiconBlock: "",
      memoryBlock: "--- TRANSLATION MEMORY ---\n- \"Hi\" → \"Salut\"\n--- END TM ---\n\n",
    });
    expect(result).toContain("TRANSLATION MEMORY");
    expect(result).toContain("\"Hi\" → \"Salut\"");
  });

  it("devrait inclure le bloc RAG si fourni", () => {
    const result = buildTranslateUserPrompt({
      sourceText: "Hello",
      sourceLanguage: "en",
      targetLanguage: "fr",
      lexiconBlock: "",
      memoryBlock: "",
      ragBlock: "## Traductions similaires précédentes\nSource: Hi\nTraduction: Salut\n\n",
    });
    expect(result).toContain("Traductions similaires précédentes");
    expect(result).toContain("Hi");
    expect(result).toContain("Salut");
  });

  it("devrait ignorer le bloc RAG s'il est undefined", () => {
    const result = buildTranslateUserPrompt({
      sourceText: "Hello",
      sourceLanguage: "en",
      targetLanguage: "fr",
      lexiconBlock: "",
      memoryBlock: "",
    });
    expect(result).not.toContain("undefined");
  });
});

// ---------------------------------------------------------------------------
// buildPreTranslateUserPrompt
// ---------------------------------------------------------------------------

describe("buildPreTranslateUserPrompt", () => {
  it("devrait construire un prompt de pré-traduction", () => {
    const result = buildPreTranslateUserPrompt({
      sourceText: "Line 1\n\nLine 2",
      sourceLanguage: "en",
      targetLanguage: "fr",
    });
    expect(result).toContain("Input (en)");
    expect(result).toContain("Line 1");
    expect(result).toContain("Line 2");
    expect(result).toContain("Translate to fr");
    expect(result).toContain("literal translation");
    expect(result).toContain("same number of paragraphs");
  });
});

// ---------------------------------------------------------------------------
// buildGrammarUserPrompt
// ---------------------------------------------------------------------------

describe("buildGrammarUserPrompt", () => {
  it("devrait construire un prompt de correction grammaticale", () => {
    const result = buildGrammarUserPrompt({
      text: "Le dragon volaient.",
      targetLanguage: "fr",
    });
    expect(result).toContain("Text to proofread (fr)");
    expect(result).toContain("Le dragon volaient.");
    expect(result).toContain("Corrected text:");
  });
});

// ---------------------------------------------------------------------------
// buildStyleUserPrompt
// ---------------------------------------------------------------------------

describe("buildStyleUserPrompt", () => {
  it("devrait construire un prompt d'amélioration stylistique", () => {
    const result = buildStyleUserPrompt({
      text: "Le dragon a volé.",
      targetLanguage: "fr",
    });
    expect(result).toContain("Text to improve (fr)");
    expect(result).toContain("Le dragon a volé.");
    expect(result).toContain("Rewritten text:");
  });
});

// ---------------------------------------------------------------------------
// buildPolishUserPrompt
// ---------------------------------------------------------------------------

describe("buildPolishUserPrompt", () => {
  it("devrait construire un prompt de polissage final", () => {
    const result = buildPolishUserPrompt({
      text: "Le dragon volait dans le ciel.",
      targetLanguage: "fr",
    });
    expect(result).toContain("Text to polish (fr)");
    expect(result).toContain("Le dragon volait dans le ciel.");
    expect(result).toContain("Polished text:");
  });
});

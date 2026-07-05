import { describe, it, expect, beforeEach } from "vitest";
import { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";

describe("TranslationMemoryEngine — segmentSentences", () => {
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    engine = new TranslationMemoryEngine();
  });

  it("devrait segmenter un texte anglais en phrases avec sbd", () => {
    const text = "Hello world. This is a test. How are you?";
    const sentences = engine.segmentSentences(text);
    expect(sentences.length).toBeGreaterThanOrEqual(3);
    expect(sentences[0]).toBe("Hello world.");
    expect(sentences[1]).toBe("This is a test.");
    expect(sentences[2]).toBe("How are you?");
  });

  it("devrait segmenter un texte français avec ponctuation", () => {
    const text = "Bonjour le monde. Comment allez-vous ? Très bien, merci !";
    const sentences = engine.segmentSentences(text);
    expect(sentences.length).toBeGreaterThanOrEqual(3);
    expect(sentences[0]).toBe("Bonjour le monde.");
    expect(sentences[1]).toBe("Comment allez-vous ?");
  });

  it("devrait gérer les textes CJK avec split sur ponctuation", () => {
    const text = "你好世界。这是一个测试。你怎么样？";
    const sentences = engine.segmentSentences(text);
    // CJK falls back to punctuation split since sbd doesn't handle it.
    // Le split sur [。！？] supprime la ponctuation de fin de phrase.
    expect(sentences.length).toBeGreaterThanOrEqual(3);
    expect(sentences[0]).toBe("你好世界");
    expect(sentences[1]).toBe("这是一个测试");
    expect(sentences[2]).toBe("你怎么样");
  });

  it("devrait retourner un tableau vide pour un texte vide ou nul", () => {
    expect(engine.segmentSentences("")).toEqual([]);
    expect(engine.segmentSentences("   ")).toEqual([]);
  });
});

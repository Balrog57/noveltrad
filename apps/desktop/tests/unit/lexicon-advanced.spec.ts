import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { LexiconEngine } from "../../src/main/services/LexiconEngine";
import { useLexiconStore } from "../../src/renderer/src/stores/lexicon";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { LexiconEntry, LexiconConflict, LexiconSuggestion } from "@shared/types/index.js";

/** Crée une entrée de lexique de test */
function makeEntry(overrides: Partial<LexiconEntry> = {}): LexiconEntry {
  return {
    id: crypto.randomUUID(),
    projectId: "proj-1",
    term: "功法",
    translation: "Technique de cultivation",
    category: "technique",
    aliases: [],
    locked: false,
    priority: 5,
    ...overrides,
  };
}

// ── LexiconEngine ──

describe("LexiconEngine — findConflicts (SDD §10.9)", () => {
  const engine = new LexiconEngine();

  it("devrait détecter un duplicate_term (même normalisé)", () => {
    const entries = [
      makeEntry({ id: "e1", term: "功法" }),
      makeEntry({ id: "e2", term: "功法" }),
    ];
    const conflicts = engine.findConflicts(entries);

    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].type).toBe("duplicate_term");
    expect(conflicts[0].description).toContain("功法");
  });

  it("devrait détecter un duplicate_term malgré des différences de casse", () => {
    const entries = [
      makeEntry({ id: "e1", term: "Celestial Sword" }),
      makeEntry({ id: "e2", term: "celestial sword" }),
    ];
    const conflicts = engine.findConflicts(entries);

    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].type).toBe("duplicate_term");
  });

  it("devrait détecter un overlap (terme inclus dans un autre)", () => {
    const entries = [
      makeEntry({ id: "e1", term: "celestial sword" }),
      makeEntry({ id: "e2", term: "sword" }),
    ];
    const conflicts = engine.findConflicts(entries);

    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].type).toBe("overlap");
    expect(conflicts[0].description).toContain("contient");
  });

  it("devrait retourner un conflit pour chaque type (doublon + overlap)", () => {
    const entries = [
      makeEntry({ id: "e1", term: "celestial sword" }),
      makeEntry({ id: "e2", term: "Celestial Sword" }),
      makeEntry({ id: "e3", term: "sword" }),
    ];
    const conflicts = engine.findConflicts(entries);

    // Au moins 2 conflits : 1 duplicate_term + 1 overlap
    expect(conflicts.length).toBeGreaterThanOrEqual(2);
    const duplicates = conflicts.filter((c) => c.type === "duplicate_term");
    const overlaps = conflicts.filter((c) => c.type === "overlap");
    expect(duplicates.length).toBeGreaterThanOrEqual(1);
    expect(overlaps.length).toBeGreaterThanOrEqual(1);
  });

  it("devrait ne pas retourner de conflit pour des termes distincts", () => {
    const entries = [
      makeEntry({ id: "e1", term: "功法" }),
      makeEntry({ id: "e2", term: "灵力" }),
      makeEntry({ id: "e3", term: "丹药" }),
    ];
    const conflicts = engine.findConflicts(entries);
    expect(conflicts).toHaveLength(0);
  });

  it("devrait gérer la normalisation des caractères spéciaux", () => {
    const entries = [
      makeEntry({ id: "e1", term: "célestial-sword!" }),
      makeEntry({ id: "e2", term: "célestial sword" }),
    ];
    const conflicts = engine.findConflicts(entries);

    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].type).toBe("duplicate_term");
  });

  it("devrait retourner un tableau vide pour moins de 2 entrées", () => {
    const conflicts = engine.findConflicts([makeEntry()]);
    expect(conflicts).toHaveLength(0);
  });
});

describe("LexiconEngine — suggestTranslation (SDD §10.10)", () => {
  const engine = new LexiconEngine();

  it("devrait retourner null si le AiRouter échoue", async () => {
    const mockRouter = {
      chat: vi.fn().mockRejectedValue(new Error("Réseau indisponible")),
      tryParseJson: vi.fn().mockReturnValue(null),
    } as unknown as AiRouter;

    const result = await engine.suggestTranslation("test", "", mockRouter, "ollama-default");
    expect(result).toBeNull();
  });

  it("devrait parser le JSON de la réponse IA", async () => {
    const mockResponse = JSON.stringify({
      translation: "Divine Technique",
      category: "technique",
      explanation: "'神功' refers to a divine or godly skill in martial arts novels.",
    });

    const mockRouter = {
      chat: vi.fn().mockResolvedValue(mockResponse),
      tryParseJson: vi.fn().mockReturnValue(JSON.parse(mockResponse)),
    } as unknown as AiRouter;

    const result = await engine.suggestTranslation("神功", "他修炼了神功。", mockRouter, "ollama-default");

    expect(result).not.toBeNull();
    expect(result!.translation).toBe("Divine Technique");
    expect(result!.category).toBe("technique");
    expect(result!.explanation).toBeTruthy();
  });

  it("devrait utiliser le contexte dans le prompt", async () => {
    const mockRouter = {
      chat: vi.fn().mockResolvedValue(
        JSON.stringify({ translation: "T", category: "general", explanation: "E" }),
      ),
      tryParseJson: vi.fn().mockReturnValue({ translation: "T", category: "general", explanation: "E" }),
    } as unknown as AiRouter;

    await engine.suggestTranslation("term", "contexte important", mockRouter, "ollama-default");

    const messages = (mockRouter.chat as ReturnType<typeof vi.fn>).mock.calls[0][1];
    const userMessage = messages.find((m: { role: string }) => m.role === "user").content;
    expect(userMessage).toContain("contexte important");
  });
});

// ── LexiconStore ──

describe("LexiconStore — conflits et suggestions", () => {
  let mockInvoke: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivePinia(createPinia());
    mockInvoke = vi.fn();
    (globalThis as Record<string, unknown>).window = {
      novelTradAPI: { invoke: mockInvoke },
    };
  });

  it("devrait trouver des conflits via le store", async () => {
    const store = useLexiconStore();
    store.entries = [
      makeEntry({ id: "e1", term: "功法" }),
      makeEntry({ id: "e2", term: "功法" }),
    ];
    const fakeConflicts: LexiconConflict[] = [
      {
        type: "duplicate_term",
        entryA: store.entries[0],
        entryB: store.entries[1],
        description: 'Terme en double : "功法" et "功法"',
        normalized: "功法",
      },
    ];
    mockInvoke.mockResolvedValueOnce(fakeConflicts);

    await store.findConflicts("proj-1");

    expect(mockInvoke).toHaveBeenCalledWith("lexicon:find-conflicts", {
      entries: store.entries,
    });
    expect(store.conflicts).toEqual(fakeConflicts);
  });

  it("devrait gérer une erreur de détection de conflits", async () => {
    const store = useLexiconStore();
    store.entries = [makeEntry({ id: "e1" }), makeEntry({ id: "e2" })];
    mockInvoke.mockRejectedValueOnce(new Error("Erreur conflits"));

    await store.findConflicts("proj-1");

    expect(store.error).toBe("Erreur conflits");
    expect(store.conflicts).toEqual([]);
  });

  it("devrait suggérer une traduction via le store", async () => {
    const store = useLexiconStore();
    const fakeSuggestion: LexiconSuggestion = {
      translation: "Divine Skill",
      category: "technique",
      explanation: "Terme composé courant dans les romans xianxia.",
    };
    mockInvoke.mockResolvedValueOnce(fakeSuggestion);

    const result = await store.suggestTranslation("神技", "Il maîtrise la神技.", "proj-1");

    expect(mockInvoke).toHaveBeenCalledWith("lexicon:suggest", {
      term: "神技",
      context: "Il maîtrise la神技.",
      projectId: "proj-1",
    });
    expect(result).toEqual(fakeSuggestion);
    expect(store.suggestion).toEqual(fakeSuggestion);
  });

  it("devrait retourner null si la suggestion échoue", async () => {
    const store = useLexiconStore();
    mockInvoke.mockRejectedValueOnce(new Error("IA indisponible"));

    const result = await store.suggestTranslation("test", "", "proj-1");

    expect(result).toBeNull();
    expect(store.suggestion).toBeNull();
    expect(store.error).toBe("IA indisponible");
  });
});

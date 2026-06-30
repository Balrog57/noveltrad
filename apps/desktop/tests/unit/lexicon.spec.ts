import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { LexiconEngine } from "../../src/main/services/LexiconEngine";
import { useLexiconStore } from "../../src/renderer/src/stores/lexicon";
import type { LexiconEntry } from "@shared/types/index.js";

/** Crée une entrée de lexique de test */
function makeEntry(overrides: Partial<LexiconEntry> = {}): LexiconEntry {
  return {
    id: "entry-1",
    projectId: "proj-1",
    term: "功法",
    translation: "Technique de cultivation",
    category: "technique",
    aliases: ["cultivation method"],
    locked: false,
    priority: 7,
    ...overrides,
  };
}

// ── LexiconEngine ──

describe("LexiconEngine", () => {
  const engine = new LexiconEngine();

  describe("extractCandidates", () => {
    it("devrait extraire des candidats d'un texte chinois (2-6 caractères)", () => {
      const text = `
        功法是修炼者的根基。这部功法极为玄妙。
        修炼功法需要天赋，但这部功法让普通人也能修炼功法。
        普通功法与这部功法相比不值一提。功法碑上刻着功法秘诀。
      `;
      const candidates = engine.extractCandidates(text, "zh");

      // "功法" apparaît 7 fois → doit être présent
      const gongfa = candidates.find((c) => c.term === "功法");
      expect(gongfa).toBeDefined();
      expect(gongfa!.occurrences).toBeGreaterThanOrEqual(3);
      expect(gongfa!.suggestedCategory).toBeDefined();
    });

    it("devrait extraire des candidats d'un texte anglais (1-4 mots)", () => {
      const text = `
        The celestial sword was a legendary weapon. The celestial sword
        could cut through mountains. Many warriors sought the celestial sword.
        The celestial sword was forged by ancient masters. Only the celestial
        sword could defeat the demon king. The celestial sword glowed with
        power. The celestial sword was the key to victory.
      `;
      const candidates = engine.extractCandidates(text, "en");

      // "celestial sword" → 6 occurrences, doit être présent
      const sword = candidates.find((c) => c.term === "celestial sword");
      expect(sword).toBeDefined();
      expect(sword!.occurrences).toBeGreaterThanOrEqual(3);
    });

    it("devrait filtrer les termes avec < 3 occurrences", () => {
      const text = "功法 功法 功法 修炼 修炼";
      const candidates = engine.extractCandidates(text, "zh");

      // "功法" = 3 → présent, "修炼" = 2 → absent
      const gongfa = candidates.find((c) => c.term === "功法");
      expect(gongfa).toBeDefined();
      const xiulian = candidates.find((c) => c.term === "修炼");
      expect(xiulian).toBeUndefined();
    });

    it("devrait retourner au maximum 50 candidats", () => {
      // Générer un texte avec beaucoup de n-grammes uniques
      const words: string[] = [];
      for (let i = 0; i < 200; i++) {
        words.push(`unique${i}`);
      }
      // Répéter 3 fois chaque mot
      const text =
        words.join(" ") + " " + words.join(" ") + " " + words.join(" ");
      const candidates = engine.extractCandidates(text, "en");
      expect(candidates.length).toBeLessThanOrEqual(50);
    });

    it("devrait deviner une catégorie pour les termes chinois", () => {
      const text = "长枪 长枪 长枪 京城 京城 京城";
      const candidates = engine.extractCandidates(text, "zh");

      const spear = candidates.find((c) => c.term === "长枪");
      expect(spear).toBeDefined();
      expect(spear!.suggestedCategory).toBe("arme");

      const capital = candidates.find((c) => c.term === "京城");
      expect(capital).toBeDefined();
      expect(capital!.suggestedCategory).toBe("lieu");
    });
  });

  describe("exportEntries", () => {
    it("devrait exporter en JSON", () => {
      const entries = [
        makeEntry(),
        makeEntry({
          id: "entry-2",
          term: "灵力",
          translation: "Spiritual Energy",
          category: "concept",
        }),
      ];
      const result = engine.exportEntries(entries, "json");
      const parsed = JSON.parse(result);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed).toHaveLength(2);
      expect(parsed[0]).toHaveProperty("term");
      expect(parsed[0]).toHaveProperty("translation");
    });

    it("devrait exporter en CSV", () => {
      const entries = [makeEntry()];
      const result = engine.exportEntries(entries, "csv");
      expect(result).toContain("term,translation");
      expect(result).toContain("功法");
    });

    it("devrait exporter en TSV", () => {
      const entries = [makeEntry()];
      const result = engine.exportEntries(entries, "tsv");
      expect(result).toContain("term\ttranslation");
    });
  });
});

// ── LexiconStore ──

describe("LexiconStore", () => {
  let mockInvoke: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivePinia(createPinia());
    mockInvoke = vi.fn();
    (globalThis as Record<string, unknown>).window = {
      novelTradAPI: { invoke: mockInvoke },
    };
  });

  it("devrait commencer avec un état vide", () => {
    const store = useLexiconStore();
    expect(store.entries).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
    expect(store.filteredEntries).toEqual([]);
    expect(store.categories).toEqual([]);
  });

  it("devrait charger les entrées de lexique", async () => {
    const store = useLexiconStore();
    const mockEntries = [
      makeEntry(),
      makeEntry({ id: "entry-2", term: "灵力" }),
    ];
    mockInvoke.mockResolvedValueOnce(mockEntries);

    await store.loadLexicon("proj-1");

    expect(mockInvoke).toHaveBeenCalledWith("lexicon:list", {
      projectId: "proj-1",
    });
    expect(store.entries).toEqual(mockEntries);
    expect(store.loading).toBe(false);
  });

  it("devrait gérer une erreur de chargement", async () => {
    const store = useLexiconStore();
    mockInvoke.mockRejectedValueOnce(new Error("Erreur DB"));

    await store.loadLexicon("proj-1");

    expect(store.error).toBe("Erreur DB");
    expect(store.entries).toEqual([]);
  });

  it("devrait sauvegarder une nouvelle entrée", async () => {
    const store = useLexiconStore();
    const entry = makeEntry();
    mockInvoke.mockResolvedValueOnce({ success: true, entry });

    await store.saveEntry(entry);

    expect(mockInvoke).toHaveBeenCalledWith("lexicon:save", {
      projectId: "proj-1",
      entry,
    });
    expect(store.entries).toHaveLength(1);
  });

  it("devrait supprimer une entrée", async () => {
    const store = useLexiconStore();
    store.entries = [makeEntry()];
    mockInvoke.mockResolvedValueOnce({ success: true });

    await store.deleteEntry("entry-1", "proj-1");

    expect(mockInvoke).toHaveBeenCalledWith("lexicon:delete", {
      projectId: "proj-1",
      entryId: "entry-1",
    });
    expect(store.entries).toHaveLength(0);
  });

  it("devrait filtrer les entrées par recherche", async () => {
    const store = useLexiconStore();
    store.entries = [
      makeEntry({ id: "e1", term: "功法" }),
      makeEntry({ id: "e2", term: "灵力", translation: "Spiritual Energy" }),
      makeEntry({
        id: "e3",
        term: "丹药",
        translation: "Pilule",
        aliases: ["pill"],
      }),
    ];

    // Par terme
    store.searchQuery = "功法";
    expect(store.filteredEntries).toHaveLength(1);

    // Par traduction
    store.searchQuery = "spiritual";
    expect(store.filteredEntries).toHaveLength(1);

    // Par alias
    store.searchQuery = "pill";
    expect(store.filteredEntries).toHaveLength(1);

    // Vide
    store.searchQuery = "inexistant";
    expect(store.filteredEntries).toHaveLength(0);
  });

  it("devrait filtrer les entrées par catégorie", async () => {
    const store = useLexiconStore();
    store.entries = [
      makeEntry({ id: "e1", term: "功法", category: "technique" }),
      makeEntry({ id: "e2", term: "灵力", category: "concept" }),
    ];

    store.categoryFilter = "technique";
    expect(store.filteredEntries).toHaveLength(1);
    expect(store.filteredEntries[0].term).toBe("功法");
  });

  it("devrait retourner les catégories uniques", () => {
    const store = useLexiconStore();
    store.entries = [
      makeEntry({ id: "e1", category: "technique" }),
      makeEntry({ id: "e2", category: "concept" }),
      makeEntry({ id: "e3", category: "technique" }),
    ];

    expect(store.categories).toContain("technique");
    expect(store.categories).toContain("concept");
    expect(store.categories).toHaveLength(2);
  });
});

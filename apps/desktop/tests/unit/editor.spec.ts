import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useEditorStore } from "../../src/renderer/src/stores/editor";
import type { Paragraph } from "@shared/types/index.js";

/** Crée un paragraphe de test */
function makeParagraph(overrides: Partial<Paragraph> = {}): Paragraph {
  return {
    id: "para-1",
    chapterId: "chap-1",
    indexInChapter: 1,
    sourceText: "Le texte source.",
    translatedText: "The translated text.",
    status: "translated",
    ...overrides,
  };
}

describe("EditorStore", () => {
  let mockInvoke: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivePinia(createPinia());
    // Mock global window.novelTradAPI pour les appels IPC async
    mockInvoke = vi.fn();
    (globalThis as Record<string, unknown>).window = {
      novelTradAPI: { invoke: mockInvoke },
    };
  });

  // --- Tests synchrones existants ---

  it("should start with empty state", () => {
    const store = useEditorStore();
    expect(store.paragraphs).toEqual([]);
    expect(store.chapterId).toBeNull();
    expect(store.hasUnsavedChanges).toBe(false);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });

  it("should update paragraph and mark as dirty", () => {
    const store = useEditorStore();
    const paragraph = makeParagraph();
    store.paragraphs = [paragraph];

    const updated = { ...paragraph, translatedText: "Nouvelle traduction." };
    store.updateParagraph(updated);

    expect(store.paragraphs[0].translatedText).toBe("Nouvelle traduction.");
    expect(store.hasUnsavedChanges).toBe(true);
    expect(store.isDirty(paragraph.id)).toBe(true);
  });

  it("should detect hasUnsavedChanges correctly", () => {
    const store = useEditorStore();
    const p1 = makeParagraph({ id: "p1" });
    const p2 = makeParagraph({ id: "p2" });
    store.paragraphs = [p1, p2];

    store.updateParagraph({ ...p1, translatedText: "Modifié" });
    expect(store.hasUnsavedChanges).toBe(true);
    expect(store.isDirty("p1")).toBe(true);
    expect(store.isDirty("p2")).toBe(false);
  });

  it("should reset paragraph translation", () => {
    const store = useEditorStore();
    const paragraph = makeParagraph({
      translatedText: "Traduction existante",
      status: "translated",
    });
    store.paragraphs = [paragraph];

    store.resetParagraph(paragraph.id);

    expect(store.paragraphs[0].translatedText).toBeUndefined();
    expect(store.paragraphs[0].status).toBe("pending");
    expect(store.isDirty(paragraph.id)).toBe(true);
  });

  it("should not throw when updating unknown paragraph", () => {
    const store = useEditorStore();
    const paragraph = makeParagraph({ id: "unknown" });
    expect(() => store.updateParagraph(paragraph)).not.toThrow();
    expect(store.hasUnsavedChanges).toBe(false);
  });

  // --- Fix 4 : Tests async pour loadChapter et saveAll ---

  it("should load chapter paragraphs successfully", async () => {
    const store = useEditorStore();
    const mockParagraphs: Paragraph[] = [
      makeParagraph({ id: "p1", indexInChapter: 0 }),
      makeParagraph({ id: "p2", indexInChapter: 1 }),
    ];
    mockInvoke.mockResolvedValueOnce(mockParagraphs);

    await store.loadChapter("chap-1");

    expect(mockInvoke).toHaveBeenCalledWith("chapter:get-paragraphs", {
      chapterId: "chap-1",
    });
    expect(store.paragraphs).toEqual(mockParagraphs);
    expect(store.chapterId).toBe("chap-1");
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });

  it("should handle loadChapter error gracefully", async () => {
    const store = useEditorStore();
    mockInvoke.mockRejectedValueOnce(new Error("Connexion échouée"));

    await store.loadChapter("chap-1");

    expect(store.paragraphs).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.error).toBe("Connexion échouée");
  });

  it("should handle loadChapter non-Error rejection", async () => {
    const store = useEditorStore();
    mockInvoke.mockRejectedValueOnce("Erreur inconnue");

    await store.loadChapter("chap-1");

    expect(store.paragraphs).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.error).toBe("Erreur lors du chargement du chapitre");
  });

  it("should save only dirty paragraphs via IPC", async () => {
    const store = useEditorStore();
    store.chapterId = "chap-1";
    const p1 = makeParagraph({
      id: "p1",
      indexInChapter: 0,
      translatedText: "Modifié 1",
    });
    const p2 = makeParagraph({
      id: "p2",
      indexInChapter: 1,
      translatedText: "Original 2",
    });
    store.paragraphs = [p1, p2];

    // Marquer seulement p1 comme dirty
    store.updateParagraph(p1);
    expect(store.hasUnsavedChanges).toBe(true);

    mockInvoke.mockResolvedValueOnce(undefined);

    await store.saveAll();

    // Vérifier que seul le paragraphe dirty a été envoyé
    expect(mockInvoke).toHaveBeenCalledWith("chapter:save", {
      chapterId: "chap-1",
      paragraphs: [{ ...p1, translatedText: "Modifié 1" }],
    });
    expect(store.hasUnsavedChanges).toBe(false);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });

  it("should handle saveAll error gracefully", async () => {
    const store = useEditorStore();
    store.chapterId = "chap-1";
    const paragraph = makeParagraph({ id: "p1" });
    store.paragraphs = [paragraph];
    store.updateParagraph(paragraph);

    mockInvoke.mockRejectedValueOnce(new Error("Erreur DB"));

    await store.saveAll();

    expect(store.loading).toBe(false);
    expect(store.error).toBe("Erreur DB");
  });

  it("should handle saveAll non-Error rejection", async () => {
    const store = useEditorStore();
    store.chapterId = "chap-1";
    const paragraph = makeParagraph({ id: "p1" });
    store.paragraphs = [paragraph];
    store.updateParagraph(paragraph);

    mockInvoke.mockRejectedValueOnce("Erreur inconnue");

    await store.saveAll();

    expect(store.loading).toBe(false);
    expect(store.error).toBe("Erreur lors de la sauvegarde");
  });

  it("should skip saveAll when chapterId is null", async () => {
    const store = useEditorStore();
    store.chapterId = null;
    store.paragraphs = [makeParagraph()];

    await store.saveAll();

    expect(mockInvoke).not.toHaveBeenCalled();
  });

  it("should skip saveAll when no dirty paragraphs", async () => {
    const store = useEditorStore();
    store.chapterId = "chap-1";
    store.paragraphs = [makeParagraph()];
    // Aucun dirty — dirtyParagraphs est vide

    await store.saveAll();

    expect(mockInvoke).not.toHaveBeenCalled();
  });
});

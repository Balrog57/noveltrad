import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import {
  useProjectStore,
  type ProjectStats,
} from "../../src/renderer/src/stores/project";

describe("ProjectStats", () => {
  let mockInvoke: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivePinia(createPinia());
    mockInvoke = vi.fn();
    (globalThis as Record<string, unknown>).window = {
      novelTradAPI: { invoke: mockInvoke },
    };
  });

  // --- Store: loadStats ---

  it("devrait commencer avec stats à null", () => {
    const store = useProjectStore();
    expect(store.stats).toBeNull();
  });

  it("devrait charger les statistiques depuis l'IPC", async () => {
    const store = useProjectStore();
    const mockStats: ProjectStats = {
      chapterCount: 5,
      totalParagraphs: 120,
      translatedParagraphs: 80,
      sourceWordCount: 15000,
      targetWordCount: 12000,
      averageQualityScore: 8.5,
      lastWorkflowStatus: "completed",
    };
    mockInvoke.mockResolvedValueOnce(mockStats);

    await store.loadStats("project-1");

    expect(mockInvoke).toHaveBeenCalledWith("project:stats", "project-1");
    expect(store.stats).toEqual(mockStats);
  });

  it("devrait gérer une erreur de chargement des stats", async () => {
    const store = useProjectStore();
    mockInvoke.mockRejectedValueOnce(new Error("Projet non trouve"));

    await store.loadStats("invalid-id");

    expect(store.stats).toBeNull();
  });

  it("devrait gérer un rejet non-Error lors du chargement des stats", async () => {
    const store = useProjectStore();
    mockInvoke.mockRejectedValueOnce("Erreur inconnue");

    await store.loadStats("project-1");

    expect(store.stats).toBeNull();
  });

  // --- Store: stats structure ---

  it("devrait stocker correctement toutes les proprietes de stats", async () => {
    const store = useProjectStore();
    const mockStats: ProjectStats = {
      chapterCount: 10,
      totalParagraphs: 500,
      translatedParagraphs: 250,
      sourceWordCount: 50000,
      targetWordCount: 40000,
      averageQualityScore: 7.25,
      lastWorkflowStatus: "running",
    };
    mockInvoke.mockResolvedValueOnce(mockStats);

    await store.loadStats("project-2");

    expect(store.stats?.chapterCount).toBe(10);
    expect(store.stats?.totalParagraphs).toBe(500);
    expect(store.stats?.translatedParagraphs).toBe(250);
    expect(store.stats?.sourceWordCount).toBe(50000);
    expect(store.stats?.targetWordCount).toBe(40000);
    expect(store.stats?.averageQualityScore).toBe(7.25);
    expect(store.stats?.lastWorkflowStatus).toBe("running");
  });

  it("devrait accepter averageQualityScore null", async () => {
    const store = useProjectStore();
    const mockStats: ProjectStats = {
      chapterCount: 0,
      totalParagraphs: 0,
      translatedParagraphs: 0,
      sourceWordCount: 0,
      targetWordCount: 0,
      averageQualityScore: null,
      lastWorkflowStatus: null,
    };
    mockInvoke.mockResolvedValueOnce(mockStats);

    await store.loadStats("project-empty");

    expect(store.stats?.averageQualityScore).toBeNull();
    expect(store.stats?.lastWorkflowStatus).toBeNull();
  });

  it("devrait reinitialiser stats a null si le chargement echoue apres succes", async () => {
    const store = useProjectStore();
    const mockStats: ProjectStats = {
      chapterCount: 5,
      totalParagraphs: 120,
      translatedParagraphs: 80,
      sourceWordCount: 15000,
      targetWordCount: 12000,
      averageQualityScore: 8.5,
      lastWorkflowStatus: "completed",
    };
    mockInvoke.mockResolvedValueOnce(mockStats);

    await store.loadStats("project-1");
    expect(store.stats).not.toBeNull();

    // Simuler un echec lors du rechargement
    mockInvoke.mockRejectedValueOnce(new Error("DB error"));
    await store.loadStats("project-1");
    expect(store.stats).toBeNull();
  });
});

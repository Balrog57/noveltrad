import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";

// ── Mock window.novelTradAPI ──

const mockInvoke = vi.fn();

(globalThis as any).window = {
  novelTradAPI: {
    invoke: mockInvoke,
    on: vi.fn(() => vi.fn()),
  },
};

// ── Import après le mock ──

import { useProjectStore } from "../../src/renderer/src/stores/project.js";
import type { ProjectStats } from "../../src/renderer/src/stores/project.js";

// ── Helpers ──

const STATS_OK: ProjectStats = {
  chapterCount: 5,
  totalParagraphs: 100,
  translatedParagraphs: 60,
  sourceWordCount: 5000,
  targetWordCount: 4500,
  averageQualityScore: 8.5,
  lastWorkflowStatus: "completed",
};

// ── Tests — ProjectView states (SDD §4.6, G7) ──

describe("ProjectView states (SDD §4.6, G7)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("loadStats succès → stats définies, error null", async () => {
    mockInvoke.mockResolvedValueOnce(STATS_OK);
    const store = useProjectStore();

    await store.loadStats("proj-1");

    expect(store.stats).toEqual(STATS_OK);
    expect(store.error).toBeNull();
  });

  it("loadStats échec → stats null, error définie (état erreur)", async () => {
    mockInvoke.mockRejectedValueOnce(new Error("DB locked"));
    const store = useProjectStore();

    await store.loadStats("proj-1");

    expect(store.stats).toBeNull();
    expect(store.error).toBe("DB locked");
  });

  it("loadStats retry après erreur → succès efface l'erreur", async () => {
    const store = useProjectStore();

    // 1er appel : échec
    mockInvoke.mockRejectedValueOnce(new Error("DB locked"));
    await store.loadStats("proj-1");
    expect(store.error).toBe("DB locked");

    // 2e appel (retry) : succès
    mockInvoke.mockResolvedValueOnce(STATS_OK);
    await store.loadStats("proj-1");
    expect(store.stats).toEqual(STATS_OK);
    expect(store.error).toBeNull();
  });

  it("loadStats échec sans message Error → error générique", async () => {
    mockInvoke.mockRejectedValueOnce("string error");
    const store = useProjectStore();

    await store.loadStats("proj-1");

    expect(store.stats).toBeNull();
    expect(store.error).toBe("Failed to load stats");
  });
});

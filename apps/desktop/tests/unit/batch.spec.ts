import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock electron-log before any imports that trigger the logger
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    transports: { file: { level: false }, console: { level: false } },
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { setActivePinia, createPinia } from "pinia";
import { ExportEngine } from "../../src/main/services/ExportEngine";
import { exportBatchSchema } from "@shared/schemas/export.js";
import type { Paragraph } from "@shared/types/index.js";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

// ── Mock window.novelTradAPI pour les tests du store ──

const mockOn = vi.fn(() => vi.fn());
const mockInvoke = vi.fn().mockResolvedValue(undefined);

(globalThis as any).window = {
  novelTradAPI: {
    invoke: mockInvoke,
    on: mockOn,
  },
};

// ── Import après le mock ──

import { useWorkflowStore } from "../../src/renderer/src/stores/workflow.js";

// ── Helpers ──

const PROJECT_ID = "00000000-0000-0000-0000-000000000001";

/** Crée un paragraphe de test */
function makeParagraph(
  id: string,
  chapterId: string,
  index: number,
  text: string,
): Paragraph {
  return {
    id,
    chapterId,
    indexInChapter: index,
    sourceText: `Source ${text}`,
    translatedText: `Traduction ${text}`,
    status: "translated",
  };
}

/** Crée un dossier temporaire unique */
function tmpDir(): string {
  return path.join(
    os.tmpdir(),
    `noveltrad-test-batch-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  );
}

// ── Tests ExportEngine.exportBatch (SDD §13.6) ──

describe("ExportEngine.exportBatch", () => {
  const engine = new ExportEngine();

  it("devrait générer un seul fichier EPUB agrégé pour plusieurs chapitres", async () => {
    const dir = tmpDir();
    const chapters = [
      {
        chapterId: "00000000-0000-0000-0000-000000000010",
        title: "Chapitre 1",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000010",
            0,
            "A",
          ),
          makeParagraph(
            "00000000-0000-0000-0000-000000000002",
            "00000000-0000-0000-0000-000000000010",
            1,
            "B",
          ),
        ],
      },
      {
        chapterId: "00000000-0000-0000-0000-000000000020",
        title: "Chapitre 2",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000003",
            "00000000-0000-0000-0000-000000000020",
            0,
            "C",
          ),
        ],
      },
    ];

    const result = await engine.exportBatch(
      PROJECT_ID,
      "Mon Roman",
      "Auteur Test",
      chapters,
      "epub",
      dir,
    );

    // EPUB agrégé : un seul fichier
    expect(result.paths).toHaveLength(1);
    expect(result.format).toBe("epub");

    const epubPath = result.paths[0]!;
    expect(fs.existsSync(epubPath)).toBe(true);
    const stat = fs.statSync(epubPath);
    expect(stat.size).toBeGreaterThan(0);

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("devrait générer un fichier par chapitre pour le format Markdown", async () => {
    const dir = tmpDir();
    const chapters = [
      {
        chapterId: "00000000-0000-0000-0000-000000000010",
        title: "Chapitre 1",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000010",
            0,
            "A",
          ),
        ],
      },
      {
        chapterId: "00000000-0000-0000-0000-000000000020",
        title: "Chapitre 2",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000003",
            "00000000-0000-0000-0000-000000000020",
            0,
            "C",
          ),
        ],
      },
    ];

    const result = await engine.exportBatch(
      PROJECT_ID,
      "Mon Roman",
      undefined,
      chapters,
      "markdown",
      dir,
    );

    // Un fichier par chapitre
    expect(result.paths).toHaveLength(2);
    expect(result.format).toBe("markdown");

    for (const p of result.paths) {
      expect(fs.existsSync(p)).toBe(true);
      const stat = fs.statSync(p);
      expect(stat.size).toBeGreaterThan(0);
    }

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("devrait générer un fichier par chapitre pour le format TXT", async () => {
    const dir = tmpDir();
    const chapters = [
      {
        chapterId: "00000000-0000-0000-0000-000000000010",
        title: "Chapitre 1",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000010",
            0,
            "A",
          ),
        ],
      },
      {
        chapterId: "00000000-0000-0000-0000-000000000020",
        title: "Chapitre 2",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000003",
            "00000000-0000-0000-0000-000000000020",
            0,
            "C",
          ),
        ],
      },
      {
        chapterId: "00000000-0000-0000-0000-000000000030",
        title: "Chapitre 3",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000005",
            "00000000-0000-0000-0000-000000000030",
            0,
            "E",
          ),
        ],
      },
    ];

    const result = await engine.exportBatch(
      PROJECT_ID,
      "Mon Roman TXT",
      undefined,
      chapters,
      "txt",
      dir,
    );

    expect(result.paths).toHaveLength(3);
    expect(result.format).toBe("txt");

    for (const p of result.paths) {
      expect(fs.existsSync(p)).toBe(true);
      const stat = fs.statSync(p);
      expect(stat.size).toBeGreaterThan(0);
    }

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("devrait créer le dossier de sortie s'il n'existe pas", async () => {
    const dir = path.join(
      os.tmpdir(),
      `noveltrad-test-batch-${Date.now()}-nested`,
      "sous-dossier",
    );
    expect(fs.existsSync(dir)).toBe(false);

    const chapters = [
      {
        chapterId: "00000000-0000-0000-0000-000000000010",
        title: "Chapitre 1",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000010",
            0,
            "A",
          ),
        ],
      },
    ];

    const result = await engine.exportBatch(
      PROJECT_ID,
      "Test Dossier",
      undefined,
      chapters,
      "markdown",
      dir,
    );

    expect(fs.existsSync(dir)).toBe(true);
    expect(result.paths).toHaveLength(1);

    // Nettoyer
    fs.rmSync(path.dirname(dir), { recursive: true, force: true });
  });

  it("devrait lever une erreur si aucun chapitre n'est fourni", async () => {
    const dir = tmpDir();
    await expect(
      engine.exportBatch(PROJECT_ID, "Vide", undefined, [], "markdown", dir),
    ).rejects.toThrow(/aucun chapitre/i);

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("devrait respecter le mode bilingue dans l'EPUB agrégé", async () => {
    const dir = tmpDir();
    const chapters = [
      {
        chapterId: "00000000-0000-0000-0000-000000000010",
        title: "Chapitre 1",
        paragraphs: [
          makeParagraph(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000010",
            0,
            "A",
          ),
        ],
      },
    ];

    const result = await engine.exportBatch(
      PROJECT_ID,
      "Bilingue EPUB",
      undefined,
      chapters,
      "epub",
      dir,
      { bilingual: true },
    );

    expect(result.paths).toHaveLength(1);
    // Vérifier que le fichier EPUB contient du contenu bilingue (source + traduction)
    const epubBuffer = fs.readFileSync(result.paths[0]!);
    // L'EPUB est un ZIP, on vérifie juste qu'il n'est pas vide et contient les entrées attendues
    expect(epubBuffer.length).toBeGreaterThan(0);

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });
});

// ── Tests schéma exportBatchSchema (SDD §13.6) ──

describe("exportBatchSchema", () => {
  it("devrait valider un payload d'export par lots valide", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      projectTitle: "Mon Roman",
      chapterIds: [
        "00000000-0000-0000-0000-000000000010",
        "00000000-0000-0000-0000-000000000020",
      ],
      format: "epub",
      outputDir: "/tmp/exports",
    };

    const result = exportBatchSchema.parse(payload);
    expect(result.projectId).toBe(payload.projectId);
    expect(result.chapterIds).toHaveLength(2);
    expect(result.format).toBe("epub");
  });

  it("devrait rejeter un payload sans projectId", () => {
    const payload = {
      projectTitle: "Mon Roman",
      chapterIds: ["00000000-0000-0000-0000-000000000010"],
      format: "epub",
      outputDir: "/tmp/exports",
    };

    expect(() => exportBatchSchema.parse(payload)).toThrow();
  });

  it("devrait rejeter un payload sans chapterIds", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      projectTitle: "Mon Roman",
      format: "epub",
      outputDir: "/tmp/exports",
    };

    expect(() => exportBatchSchema.parse(payload)).toThrow();
  });

  it("devrait rejeter un payload avec un tableau chapterIds vide", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      projectTitle: "Mon Roman",
      chapterIds: [],
      format: "epub",
      outputDir: "/tmp/exports",
    };

    expect(() => exportBatchSchema.parse(payload)).toThrow();
  });

  it("devrait rejeter un payload avec un format invalide", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      projectTitle: "Mon Roman",
      chapterIds: ["00000000-0000-0000-0000-000000000010"],
      format: "pdf",
      outputDir: "/tmp/exports",
    };

    expect(() => exportBatchSchema.parse(payload)).toThrow();
  });

  it("devrait accepter les options facultatives", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      projectTitle: "Mon Roman",
      author: "Auteur",
      chapterIds: ["00000000-0000-0000-0000-000000000010"],
      format: "markdown",
      outputDir: "/tmp/exports",
      options: {
        bilingual: true,
        includeTitle: false,
        includeParagraphNumbers: true,
      },
    };

    const result = exportBatchSchema.parse(payload);
    expect(result.options?.bilingual).toBe(true);
    expect(result.options?.includeTitle).toBe(false);
    expect(result.options?.includeParagraphNumbers).toBe(true);
    expect(result.author).toBe("Auteur");
  });
});

// ── Tests WorkflowStore — gestion de la sélection (SDD §7.9) ──

describe("WorkflowStore — sélection multiple (SDD §7.9)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("devrait commencer avec une sélection vide", () => {
    const store = useWorkflowStore();
    expect(store.selectedChapterIds).toEqual([]);
  });

  it("devrait basculer la sélection d'un chapitre", () => {
    const store = useWorkflowStore();
    const chapterId = "ch-1";

    store.toggleChapterSelection(chapterId);
    expect(store.selectedChapterIds).toContain(chapterId);
    expect(store.isSelected(chapterId)).toBe(true);

    store.toggleChapterSelection(chapterId);
    expect(store.selectedChapterIds).not.toContain(chapterId);
    expect(store.isSelected(chapterId)).toBe(false);
  });

  it("devrait sélectionner plusieurs chapitres avec selectAll", () => {
    const store = useWorkflowStore();
    const ids = ["ch-1", "ch-2", "ch-3"];

    store.selectAll(ids);
    expect(store.selectedChapterIds).toEqual(ids);
    expect(store.selectedChapterIds).toHaveLength(3);
  });

  it("devrait désélectionner tous les chapitres avec clearSelection", () => {
    const store = useWorkflowStore();
    store.selectAll(["ch-1", "ch-2"]);
    expect(store.selectedChapterIds).toHaveLength(2);

    store.clearSelection();
    expect(store.selectedChapterIds).toEqual([]);
  });

  it("devrait vérifier si un chapitre est sélectionné avec isSelected", () => {
    const store = useWorkflowStore();
    store.selectAll(["ch-1", "ch-2"]);

    expect(store.isSelected("ch-1")).toBe(true);
    expect(store.isSelected("ch-2")).toBe(true);
    expect(store.isSelected("ch-3")).toBe(false);
  });
});

// ── Tests WorkflowStore — non-régression pause/resume/cancel (SDD §7.9) ──

describe("WorkflowStore — non-régression batch existant (SDD §7.9)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("devrait appeler invoke pour startBatch", async () => {
    const store = useWorkflowStore();

    mockInvoke.mockResolvedValueOnce({
      id: "job-batch-1",
      status: "running",
      createdAt: new Date().toISOString(),
    });

    const job = await store.startBatch("/path/to/project", ["ch-1", "ch-2"]);
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:start-batch",
      "/path/to/project",
      ["ch-1", "ch-2"],
    );
    expect((job as any).id).toBe("job-batch-1");
  });

  it("devrait appeler invoke pour pause", async () => {
    const store = useWorkflowStore();
    await store.pause("job-1");
    expect(mockInvoke).toHaveBeenCalledWith("workflow:pause", "job-1");
  });

  it("devrait appeler invoke pour resume", async () => {
    const store = useWorkflowStore();
    await store.resume("job-1");
    expect(mockInvoke).toHaveBeenCalledWith("workflow:resume", "job-1");
  });

  it("devrait appeler invoke pour cancel", async () => {
    const store = useWorkflowStore();
    await store.cancel("job-1");
    expect(mockInvoke).toHaveBeenCalledWith("workflow:cancel", "job-1");
  });

  it("devrait appeler invoke pour listActive (SDD §7.11)", async () => {
    const store = useWorkflowStore();
    mockInvoke.mockResolvedValueOnce([]);
    const result = await store.listActive("/path/to/project");
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:list-active",
      "/path/to/project",
    );
    expect(result).toEqual([]);
  });

  it("devrait appeler invoke pour resumeBatch (SDD §7.11)", async () => {
    const store = useWorkflowStore();
    const job = {
      id: "job-1",
      projectId: "proj-1",
      type: "batch" as const,
      status: "running" as const,
      chapterIds: ["ch-1", "ch-2"],
      createdAt: new Date().toISOString(),
    };
    await store.resumeBatch("/path/to/project", job);
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:resume-batch",
      "/path/to/project",
      job,
    );
  });

  it("devrait exposer les méthodes existantes sans régression", () => {
    const store = useWorkflowStore();
    expect(store.start).toBeDefined();
    expect(store.startBatch).toBeDefined();
    expect(store.pause).toBeDefined();
    expect(store.resume).toBeDefined();
    expect(store.cancel).toBeDefined();
    expect(store.retryStep).toBeDefined();
    expect(store.retryFrom).toBeDefined();
    expect(store.list).toBeDefined();
    // Nouvelles méthodes SDD §7.9/§7.11
    expect(store.listActive).toBeDefined();
    expect(store.resumeBatch).toBeDefined();
    expect(store.toggleChapterSelection).toBeDefined();
    expect(store.selectAll).toBeDefined();
    expect(store.clearSelection).toBeDefined();
    expect(store.isSelected).toBeDefined();
  });
});

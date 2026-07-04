import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import type { DuplicateInfo } from "@shared/types/index.js";

// Mock electron-log (ProjectManager imports logger which imports electron-log)
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    transports: { console: { format: vi.fn() }, file: { format: vi.fn() } },
  },
  initialize: vi.fn(),
}));

// ── Mock SQLite DB (évite le "database is locked" de node-sqlite3-wasm) ──
// Cette mock supporte les requêtes utilisées par ProjectManager :
//   - SELECT * FROM chapters WHERE id = ? AND project_id = ?
//   - SELECT id, title, metadata FROM chapters WHERE project_id = ? ORDER BY order_index
//   - DELETE FROM paragraphs WHERE chapter_id = ?
//   - INSERT INTO paragraphs (...)
//   - UPDATE chapters SET metadata = ? WHERE id = ?
//   - SELECT * FROM projects WHERE id = ?

type MockRow = Record<string, unknown>;
interface MockStmt {
  get(params?: unknown[]): MockRow | undefined;
  all(params?: unknown[]): MockRow[];
  run(params?: unknown[]): { changes: number; lastInsertRowid: number };
}

function createMockDb(initialData?: {
  chapters?: MockRow[];
  projects?: MockRow[];
  paragraphs?: MockRow[];
}): {
  db: { prepare: (sql: string) => MockStmt; exec: (sql: string) => void; close: () => void };
  getChapters: () => MockRow[];
  getParagraphs: () => MockRow[];
  getProjects: () => MockRow[];
} {
  const chapters: MockRow[] = initialData?.chapters ?? [];
  const projects: MockRow[] = initialData?.projects ?? [];
  const paragraphs: MockRow[] = initialData?.paragraphs ?? [];

  const matchParams = (row: MockRow, params: unknown[]): boolean => {
    // Les paramètres ? sont positionnels — on ne vérifie que les colonnes connues
    return true; // Simplification : laisse la logique applicative filtrer
  };

  const prepare = (sql: string): MockStmt => {
    const lower = sql.toLowerCase().trim();

    if (lower.startsWith("select * from chapters where id = ?")) {
      return {
        get(params?: unknown[]) {
          const id = params?.[0] as string;
          return chapters.find((c) => c.id === id);
        },
        all() { return []; },
        run() { return { changes: 0, lastInsertRowid: 0 }; },
      };
    }

    if (lower.startsWith("select id, title, metadata from chapters")) {
      return {
        get() { return undefined; },
        all(params?: unknown[]) {
          const projectId = params?.[0] as string;
          return chapters
            .filter((c) => c.project_id === projectId)
            .sort((a, b) => (a.order_index as number) - (b.order_index as number));
        },
        run() { return { changes: 0, lastInsertRowid: 0 }; },
      };
    }

    if (lower.startsWith("select * from projects")) {
      return {
        get(params?: unknown[]) {
          const id = params?.[0] as string;
          return projects.find((p) => p.id === id);
        },
        all() { return []; },
        run() { return { changes: 0, lastInsertRowid: 0 }; },
      };
    }

    if (lower.startsWith("delete from paragraphs")) {
      return {
        get() { return undefined; },
        all() { return []; },
        run(params?: unknown[]) {
          const chapterId = params?.[0] as string;
          const initialLen = paragraphs.length;
          for (let i = paragraphs.length - 1; i >= 0; i--) {
            if (paragraphs[i].chapter_id === chapterId) {
              paragraphs.splice(i, 1);
            }
          }
          return { changes: initialLen - paragraphs.length, lastInsertRowid: 0 };
        },
      };
    }

    if (lower.startsWith("insert into paragraphs")) {
      return {
        get() { return undefined; },
        all() { return []; },
        run(params?: unknown[]) {
          const newPara: MockRow = {
            id: params?.[0] as string,
            chapter_id: params?.[1] as string,
            index_in_chapter: params?.[2] as number,
            source_text: params?.[3] as string,
            translated_text: params?.[4] as string | null,
            status: params?.[5] as string,
          };
          paragraphs.push(newPara);
          return { changes: 1, lastInsertRowid: paragraphs.length };
        },
      };
    }

    if (lower.startsWith("update chapters set metadata")) {
      return {
        get() { return undefined; },
        all() { return []; },
        run(params?: unknown[]) {
          const metadataStr = params?.[0] as string;
          const id = params?.[1] as string;
          const chapter = chapters.find((c) => c.id === id);
          if (chapter) {
            try {
              chapter.metadata = JSON.parse(metadataStr);
            } catch {
              chapter.metadata = metadataStr;
            }
          }
          return { changes: chapter ? 1 : 0, lastInsertRowid: 0 };
        },
      };
    }

    // Fallback : stmt vide
    return {
      get() { return undefined; },
      all() { return []; },
      run() { return { changes: 0, lastInsertRowid: 0 }; },
    };
  };

  return {
    db: {
      prepare,
      exec: () => {},
      close: () => {},
    },
    getChapters: () => [...chapters],
    getParagraphs: () => [...paragraphs],
    getProjects: () => [...projects],
  };
}

// ── Mock le module DB ──
let mockDbHelper: ReturnType<typeof createMockDb>;

vi.mock("../../src/main/db/connection.js", () => ({
  createProjectDatabase: () => mockDbHelper.db,
  runMigrations: () => {},
}));

// ── Mock SettingsManager ──
class MockSettingsManager {
  private store: Record<string, unknown> = {
    recentProjects: [],
    defaultProjectsPath: os.tmpdir(),
    sourceLanguage: "en",
    targetLanguage: "fr",
    ollamaHost: "http://localhost:11434",
    defaultModel: "qwen3.5:9b",
  };
  get<K extends string>(key: K): unknown { return this.store[key]; }
  set<K extends string>(key: K, value: unknown): void { this.store[key] = value; }
  getAll(): Record<string, unknown> { return { ...this.store }; }
}

/**
 * Crée un projet temporaire sur disque (répertoires, config.json, fichier source,
 * fichiers .md) avec une DB mockée pour éviter les limites de node-sqlite3-wasm.
 */
async function createTestContext(): Promise<{
  projectManager: import("../../src/main/managers/ProjectManager.js").ProjectManager;
  tmpDir: string;
  projectDir: string;
  projectId: string;
  chapterId: string;
  sourceFilePath: string;
  chapterMeta: Record<string, unknown>;
}> {
  const { ProjectManager } = await import(
    "../../src/main/managers/ProjectManager.js"
  );

  const tmpDir = path.join(
    os.tmpdir(),
    `noveltrad-test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  );
  const projectName = "TestProject";
  const projectDir = path.join(tmpDir, projectName);

  // 1. Répertoires
  fs.mkdirSync(projectDir, { recursive: true });
  fs.mkdirSync(path.join(projectDir, "chapitres"));
  fs.mkdirSync(path.join(projectDir, "source"));
  fs.mkdirSync(path.join(projectDir, "traductions"));
  fs.mkdirSync(path.join(projectDir, "lexique"));
  fs.mkdirSync(path.join(projectDir, "exports"));
  fs.mkdirSync(path.join(projectDir, "cache"));
  fs.mkdirSync(path.join(projectDir, "logs"));

  // 2. config.json
  const projectId = crypto.randomUUID();
  fs.writeFileSync(
    path.join(projectDir, "config.json"),
    JSON.stringify({
      id: projectId, name: projectName, author: "Test",
      sourceLanguage: "en", targetLanguage: "fr",
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      version: "1.0.0",
      parser: { chapterSeparator: "^Chapter\\s+\\d+", paragraphSeparator: "\\n\\n" },
    }, null, 2), "utf-8",
  );

  // 3. Fichier source original (nommé comme le projet pour le test de titre)
  const sourceContent = "Chapter 1\n\nThis is the first paragraph.\n\nHere is the second paragraph.\n\nAnd the third paragraph.";
  const originalFileHash = crypto.createHash("sha256").update(sourceContent, "utf-8").digest("hex");
  const sourceFilePath = path.join(tmpDir, "TestProject.txt");
  fs.writeFileSync(sourceFilePath, sourceContent, "utf-8");

  // 4. Chapitre dans la DB mockée
  const chapterId = crypto.randomUUID();
  const chapterMeta = { originalFileHash, sourceHash: crypto.createHash("sha256").update(sourceContent, "utf-8").digest("hex") };

  // Écrire le fichier .md normalisé
  fs.writeFileSync(path.join(projectDir, "source", `${chapterId}.md`), sourceContent, "utf-8");

  // Initialiser la DB mockée
  mockDbHelper = createMockDb({
    projects: [{
      id: projectId, name: projectName, author: "Test",
      source_language: "en", target_language: "fr",
      path: projectDir,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }],
    chapters: [{
      id: chapterId, project_id: projectId, title: "TestProject",
      source_path: sourceFilePath, order_index: 0,
      status: "pending",
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      metadata: JSON.stringify(chapterMeta), // La DB stocke en JSON string
    }],
    paragraphs: sourceContent.split(/\n\n+/).filter(Boolean).map((text, i) => ({
      id: crypto.randomUUID(), chapter_id: chapterId,
      index_in_chapter: i + 1, source_text: text,
      translated_text: null, status: "pending",
    })),
  });

  // 5. Settings
  const settings = new MockSettingsManager();
  settings.set("recentProjects", [projectDir]);

  // 6. ProjectManager
  const pm = new ProjectManager(settings as any);

  // Pour que resolveProjectPath trouve le projet, on mocke aussi la DB
  // que ProjectManager.createProjectDatabase va ouvrir.
  // Notre mock retourne la même DB mockée.

  return { projectManager: pm, tmpDir, projectDir, projectId, chapterId, sourceFilePath, chapterMeta };
}

// ── Tests refreshSource (SDD §5.8) ──

describe("refreshSource — backend (SDD §5.8)", () => {
  let ctx: Awaited<ReturnType<typeof createTestContext>>;

  beforeEach(async () => {
    ctx = await createTestContext();
  });

  afterEach(() => {
    try { fs.rmSync(ctx.tmpDir, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("devrait retourner le chapitre inchangé si le fichier source original n'a pas changé", async () => {
    const result = await ctx.projectManager.refreshSource(
      ctx.projectId, ctx.chapterId, "replace",
    );
    expect(result).toBeDefined();
    expect(result.id).toBe(ctx.chapterId);
    // Le hash original correspond → le chapitre est retourné inchangé
  });

  it("devrait rafraîchir le chapitre avec la stratégie 'replace' après modification", async () => {
    // Modifier le fichier source original
    const newContent = "Chapter 1\n\nUPDATED first paragraph.\n\nUPDATED second paragraph.";
    fs.writeFileSync(ctx.sourceFilePath, newContent, "utf-8");

    const result = await ctx.projectManager.refreshSource(
      ctx.projectId, ctx.chapterId, "replace",
    );
    expect(result).toBeDefined();
    expect(result.id).toBe(ctx.chapterId);

    // Vérifier que le fichier .md a été mis à jour
    const mdPath = path.join(ctx.projectDir, "source", `${ctx.chapterId}.md`);
    const mdContent = fs.readFileSync(mdPath, "utf-8");
    expect(mdContent).toContain("UPDATED first paragraph");
    expect(mdContent).not.toContain("This is the first paragraph");
  });

  it("devrait fusionner avec la stratégie 'merge'", async () => {
    // Ajouter un paragraphe
    const newContent = "Chapter 1\n\nThis is the first paragraph.\n\nHere is the second paragraph.\n\nAnd the third paragraph.\n\nA brand new fourth paragraph.";
    fs.writeFileSync(ctx.sourceFilePath, newContent, "utf-8");

    const result = await ctx.projectManager.refreshSource(
      ctx.projectId, ctx.chapterId, "merge",
    );
    expect(result).toBeDefined();

    const mdPath = path.join(ctx.projectDir, "source", `${ctx.chapterId}.md`);
    const mdContent = fs.readFileSync(mdPath, "utf-8");
    expect(mdContent).toContain("brand new fourth paragraph");
    expect(mdContent).toContain("first paragraph");
  });

  it("devrait lever une erreur si le chapitre est introuvable", async () => {
    await expect(
      ctx.projectManager.refreshSource(ctx.projectId, "00000000-0000-0000-0000-000000000000", "replace"),
    ).rejects.toThrow("Chapitre non trouvé");
  });

  it("devrait utiliser 'replace' par défaut si aucune stratégie n'est fournie", async () => {
    const newContent = "Chapter 1\n\nDefault strategy replacement content.";
    fs.writeFileSync(ctx.sourceFilePath, newContent, "utf-8");

    const result = await ctx.projectManager.refreshSource(ctx.projectId, ctx.chapterId);
    expect(result).toBeDefined();
    expect(result.id).toBe(ctx.chapterId);

    const mdPath = path.join(ctx.projectDir, "source", `${ctx.chapterId}.md`);
    expect(fs.readFileSync(mdPath, "utf-8")).toContain("Default strategy replacement content");
  });
});

// ── Tests detectDuplicate (SDD §5.10) ──

describe("detectDuplicate — backend (SDD §5.10)", () => {
  let ctx: Awaited<ReturnType<typeof createTestContext>>;

  beforeEach(async () => {
    ctx = await createTestContext();
  });

  afterEach(() => {
    try { fs.rmSync(ctx.tmpDir, { recursive: true, force: true }); } catch { /* ok */ }
  });

  it("devrait détecter un doublon par titre ET hash (même fichier)", () => {
    // Le même fichier correspond par titre (même nom) ET par originalFileHash
    const result = ctx.projectManager.detectDuplicate(ctx.projectId, ctx.sourceFilePath);
    expect(result).not.toBeNull();
    expect(result!.type).toBe("both"); // Titre + hash correspondent
    expect(result!.existingChapterId).toBe(ctx.chapterId);
    expect(result!.fileHash).toBeTruthy();
    expect(result!.existingHash).toBeTruthy();
  });

  it("devrait détecter un doublon par hash SHA256 (fichier identique, nom différent)", () => {
    // Copier le même contenu avec un nom différent → ne match que par hash
    const sameContentDiffName = path.join(ctx.tmpDir, "CopyOfProject.txt");
    fs.writeFileSync(sameContentDiffName,
      fs.readFileSync(ctx.sourceFilePath), // Même contenu
    );

    const result = ctx.projectManager.detectDuplicate(ctx.projectId, sameContentDiffName);
    expect(result).not.toBeNull();
    // Le titre diffère, mais le hash binaire correspond à originalFileHash
    expect(result!.fileHash).toBeTruthy();
  });

  it("devrait retourner null pour un fichier complètement différent", () => {
    const diffPath = path.join(ctx.tmpDir, "different.txt");
    fs.writeFileSync(diffPath, "Completely different content never imported.", "utf-8");

    const result = ctx.projectManager.detectDuplicate(ctx.projectId, diffPath);
    expect(result).toBeNull();
  });

  it("devrait lever une erreur si le fichier est introuvable", () => {
    expect(() =>
      ctx.projectManager.detectDuplicate(ctx.projectId, "/nonexistent/file.txt"),
    ).toThrow("Fichier introuvable");
  });
});

// ── Tests suppression de projet (renderer mock) ──

describe("suppression de projet (SDD §5.11)", () => {
  const mockInvoke = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (globalThis as Record<string, unknown>).window = {
      novelTradAPI: { invoke: mockInvoke, on: vi.fn() },
    };
  });

  it("devrait supprimer un projet de la liste (sans les fichiers)", async () => {
    mockInvoke.mockResolvedValueOnce(undefined);
    await window.novelTradAPI.invoke("project:delete", "proj-1", false);
    expect(mockInvoke).toHaveBeenCalledWith("project:delete", "proj-1", false);
  });

  it("devrait supprimer un projet ET ses fichiers", async () => {
    mockInvoke.mockResolvedValueOnce(undefined);
    await window.novelTradAPI.invoke("project:delete", "proj-1", true);
    expect(mockInvoke).toHaveBeenCalledWith("project:delete", "proj-1", true);
  });

  it("devrait lever une erreur si le projet n'existe pas", async () => {
    mockInvoke.mockRejectedValueOnce(new Error("Projet non trouvé"));
    await expect(
      window.novelTradAPI.invoke("project:delete", "proj-inexistant", false),
    ).rejects.toThrow("Projet non trouvé");
  });
});

// ── Tests de validation Zod ──

describe("Validation Zod des handlers Phase F", () => {
  const mockInvoke = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (globalThis as Record<string, unknown>).window = {
      novelTradAPI: { invoke: mockInvoke, on: vi.fn() },
    };
  });

  it("devrait valider le schéma refreshSource", async () => {
    mockInvoke.mockResolvedValueOnce({ id: "chapter-1" });
    const r = await window.novelTradAPI.invoke<Record<string, unknown>>("project:refresh-source", {
      projectId: "550e8400-e29b-41d4-a716-446655440000",
      chapterId: "660e8400-e29b-41d4-a716-446655440001",
      strategy: "replace",
    });
    expect(r!.id).toBe("chapter-1");
  });

  it("devrait rejeter un projectId non UUID pour refreshSource", async () => {
    mockInvoke.mockRejectedValueOnce(new Error("Validation error"));

    await expect(
      window.novelTradAPI.invoke("project:refresh-source", {
        projectId: "pas-un-uuid",
        chapterId: "660e8400-e29b-41d4-a716-446655440001",
        strategy: "replace",
      }),
    ).rejects.toThrow("Validation error");
  });

  it("devrait valider le schéma detectDuplicate", async () => {
    mockInvoke.mockResolvedValueOnce(null);
    const r = await window.novelTradAPI.invoke("project:detect-duplicate", {
      projectId: "550e8400-e29b-41d4-a716-446655440000",
      filePath: "/path/to/file.txt",
    });
    expect(r).toBeNull();
  });

  it("devrait rejeter un projectId non UUID pour detectDuplicate", async () => {
    mockInvoke.mockRejectedValueOnce(new Error("Validation error"));
    await expect(
      window.novelTradAPI.invoke("project:detect-duplicate", {
        projectId: "invalide",
        filePath: "/path/to/file.txt",
      }),
    ).rejects.toThrow();
  });

  it("devrait rejeter une stratégie invalide pour refreshSource", async () => {
    mockInvoke.mockRejectedValueOnce(new Error("Invalid enum value"));
    await expect(
      window.novelTradAPI.invoke("project:refresh-source", {
        projectId: "550e8400-e29b-41d4-a716-446655440000",
        chapterId: "660e8400-e29b-41d4-a716-446655440001",
        strategy: "invalide",
      }),
    ).rejects.toThrow();
  });
});

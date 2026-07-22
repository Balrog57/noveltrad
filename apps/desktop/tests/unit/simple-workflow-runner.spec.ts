import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

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

// Mock AgentFactory : le runner l'instancie en interne. On remplace par des
// stub-agents qui retournent des canned outputs par stage, pour tester
// l'orchestration du runner (séquence, events, persistance) sans dépendre des
// appels LLM ni du marshallage interne des vrais agents.
const createdStages: string[] = [];
vi.mock("../../src/main/services/agents/AgentFactory", () => ({
  AgentFactory: vi.fn().mockImplementation(() => ({
    create: vi.fn().mockImplementation((stage: string) => {
      createdStages.push(stage);
      // Stub-agent minimal : son execute() retourne un AgentOutput selon le stage.
      return {
        stage,
        execute: vi.fn().mockImplementation(async (input: {
          paragraphs?: Array<{ sourceText: string }>;
        }) => {
          if (stage === "translate") {
            // Retourne des paragraphes "traduits".
            return {
              paragraphs: (input.paragraphs ?? []).map((p) => ({
                ...p,
                translatedText: `[trad] ${p.sourceText}`,
                status: "translated",
              })),
            };
          }
          if (stage === "proofread" || stage === "glossary") {
            return { text: "Texte raffiné." };
          }
          // validate
          return {
            report: { globalScore: 90 },
            score: 90,
          };
        }),
      };
    }),
  })),
}));

import { SimpleWorkflowRunner, SIMPLE_STAGES } from "../../src/main/managers/SimpleWorkflowRunner";
import type { SettingsManager } from "../../src/main/managers/SettingsManager";
import { createProjectDatabase, runMigrations } from "../../src/main/db/connection";
import { ProjectRepository } from "../../src/main/db/repositories/ProjectRepository";
import { ChapterRepository } from "../../src/main/db/repositories/ChapterRepository";
import { ParagraphRepository } from "../../src/main/db/repositories/ParagraphRepository";

const MIGRATIONS_DIR = path.resolve(
  __dirname,
  "../../src/main/db/migrations",
);

// ---------------------------------------------------------------------------
// Helpers — projet temporaire sur disque (createProjectDatabase a besoin d'un dir)
// ---------------------------------------------------------------------------

function makeTempProject(): string {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "simple-runner-test-"),
  );
  return dir;
}

function seedProject(projectPath: string): {
  projectId: string;
  chapterId: string;
} {
  const db = createProjectDatabase(projectPath);
  try {
    runMigrations(db, MIGRATIONS_DIR);
    const projectRepo = new ProjectRepository(db);
    const chapterRepo = new ChapterRepository(db);
    const paragraphRepo = new ParagraphRepository(db);
    const now = new Date().toISOString();

    const projectId = "proj-1";
    const chapterId = "ch1";
    projectRepo.create({
      id: projectId,
      name: "Test Novel",
      sourceLanguage: "en",
      targetLanguage: "fr",
      path: projectPath,
      createdAt: now,
      updatedAt: now,
    });
    chapterRepo.create({
      id: chapterId,
      projectId,
      title: "Chapter 1",
      orderIndex: 0,
      status: "pending",
      createdAt: now,
      updatedAt: now,
    });
    paragraphRepo.upsertMany(chapterId, [
      {
        id: "p1",
        chapterId,
        indexInChapter: 0,
        sourceText: "The dragon flew over the mountains.",
        status: "pending",
      },
      {
        id: "p2",
        chapterId,
        indexInChapter: 1,
        sourceText: "The knights gathered at dawn.",
        status: "pending",
      },
    ]);
    return { projectId, chapterId };
  } finally {
    db.close();
  }
}

function makeMockSettings(overrides: Record<string, unknown> = {}): SettingsManager {
  const defaults: Record<string, unknown> = {
    defaultModel: "qwen3.5:9b",
    ollamaHost: "http://localhost:11434",
    modelCosts: {},
    summarizerEnabled: false, // désactivé par défaut pour isoler le pipeline
    maxConcurrentJobs: 1,
    ragEnabled: false,
    reviewLoopEnabled: false,
  };
  return {
    get: vi.fn().mockImplementation((key: string) => {
      if (key in overrides) {
        return overrides[key];
      }
      return defaults[key];
    }),
  } as unknown as SettingsManager;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SimpleWorkflowRunner", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = makeTempProject();
    createdStages.length = 0;
  });

  afterEach(() => {
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it("SIMPLE_STAGES définit le pipeline 4-stages dans l'ordre", () => {
    expect(SIMPLE_STAGES).toEqual([
      "translate",
      "proofread",
      "glossary",
      "validate",
    ]);
  });

  it("runChapter exécute les 4 stages et émet des events de progression", async () => {
    const { chapterId } = seedProject(tempDir);
    const events: { stage: string; status: string }[] = [];
    const runner = new SimpleWorkflowRunner(
      tempDir,
      makeMockSettings(),
      (p) => events.push({ stage: p.stage, status: p.status }),
    );
    try {
      await runner.runChapter("job-1", chapterId);
    } finally {
      runner.dispose();
    }

    // 4 stages × 2 events (running + completed) = 8 events
    expect(events).toHaveLength(8);
    const stages = events.filter((e) => e.status === "running").map((e) => e.stage);
    expect(stages).toEqual(["translate", "proofread", "glossary", "validate"]);
    // Tous les events "completed" ne sont pas des "failed"
    expect(events.every((e) => e.status !== "failed")).toBe(true);
  });

  it("runChapter marque le chapitre completed à la fin", async () => {
    const { chapterId } = seedProject(tempDir);
    const runner = new SimpleWorkflowRunner(tempDir, makeMockSettings());
    try {
      await runner.runChapter("job-1", chapterId);
    } finally {
      runner.dispose();
    }

    const db = createProjectDatabase(tempDir);
    try {
      const chapter = new ChapterRepository(db).getById(chapterId);
      expect(chapter?.status).toBe("completed");
    } finally {
      db.close();
    }
  });

  it("cancel arrête un batch après le chapitre courant", async () => {
    seedProject(tempDir);
    // Ajouter un 2e chapitre.
    const db = createProjectDatabase(tempDir);
    const chapterId2 = "ch2";
    try {
      runMigrations(db, MIGRATIONS_DIR);
      const projectRepo = new ProjectRepository(db);
      const chapterRepo = new ChapterRepository(db);
      const paragraphRepo = new ParagraphRepository(db);
      const project = projectRepo.getByPath(tempDir)!;
      const now = new Date().toISOString();
      chapterRepo.create({
        id: chapterId2,
        projectId: project.id,
        title: "Chapter 2",
        orderIndex: 1,
        status: "pending",
        createdAt: now,
        updatedAt: now,
      });
      paragraphRepo.upsertMany(chapterId2, [
        {
          id: "p3",
          chapterId: chapterId2,
          indexInChapter: 0,
          sourceText: "A new adventure begins.",
          status: "pending",
        },
      ]);
    } finally {
      db.close();
    }

    const runner = new SimpleWorkflowRunner(tempDir, makeMockSettings(), () => {
      // Cancel dès le premier event (chapitre 0, stage translate running).
      runner.cancel();
    });
    try {
      const firstChapterId = await getFirstChapterId(tempDir);
      await runner.runBatch("job-cancel", [firstChapterId, chapterId2]);
    } finally {
      runner.dispose();
    }

    // Le cancel prend effet après le stage courant : seul "translate" du
    // chapitre 0 a pu démarrer ; les 3 stages suivants et le chapitre 1 sont
    // sautés. On vérifie qu'aucun stage du chapitre 1 n'a tourné.
    expect(createdStages).toContain("translate");
    // Pas de "validate" (le 4e stage) car le pipeline a été coupé avant.
    expect(createdStages).not.toContain("validate");
  });

  it("runBatch exécute plusieurs chapitres séquentiellement", async () => {
    seedProject(tempDir);
    // Récupérer les chapitres (un seul seedé ici, on en ajoute un 2e).
    const db = createProjectDatabase(tempDir);
    const chapterId2 = "ch2";
    try {
      runMigrations(db, MIGRATIONS_DIR);
      const projectRepo = new ProjectRepository(db);
      const chapterRepo = new ChapterRepository(db);
      const paragraphRepo = new ParagraphRepository(db);
      const project = projectRepo.getByPath(tempDir)!;
      const now = new Date().toISOString();
      chapterRepo.create({
        id: chapterId2,
        projectId: project.id,
        title: "Chapter 2",
        orderIndex: 1,
        status: "pending",
        createdAt: now,
        updatedAt: now,
      });
      paragraphRepo.upsertMany(chapterId2, [
        {
          id: "p3",
          chapterId: chapterId2,
          indexInChapter: 0,
          sourceText: "A new adventure begins.",
          status: "pending",
        },
      ]);
    } finally {
      db.close();
    }

    const events: { batchIndex?: number; stage: string; status: string }[] = [];
    const runner = new SimpleWorkflowRunner(
      tempDir,
      makeMockSettings(),
      (p) =>
        events.push({
          batchIndex: p.batchChapterIndex,
          stage: p.stage,
          status: p.status,
        }),
    );
    try {
      const firstChapterId = await getFirstChapterId(tempDir);
      await runner.runBatch("job-batch", [firstChapterId, chapterId2]);
    } finally {
      runner.dispose();
    }

    // 2 chapitres × 4 stages × 2 events = 16 events
    expect(events).toHaveLength(16);
    const batch0 = events.filter((e) => e.batchIndex === 0).map((e) => e.stage);
    const batch1 = events.filter((e) => e.batchIndex === 1).map((e) => e.stage);
    expect(batch0).toContain("translate");
    expect(batch1).toContain("validate");
  });
});

async function getFirstChapterId(projectPath: string): Promise<string> {
  const db = createProjectDatabase(projectPath);
  try {
    const project = new ProjectRepository(db).getByPath(projectPath)!;
    const chapters = new ChapterRepository(db).listByProject(project.id);
    return chapters[0].id;
  } finally {
    db.close();
  }
}

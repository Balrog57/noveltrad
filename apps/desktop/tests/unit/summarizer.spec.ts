import { describe, it, expect, beforeEach, vi } from "vitest";
import path from "node:path";
import sqlite3 from "node-sqlite3-wasm";

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

import { SummarizerAgent } from "../../src/main/services/agents/SummarizerAgent";
import { SummaryRepository } from "../../src/main/db/repositories/SummaryRepository";
import { runMigrations } from "../../src/main/db/connection";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { AgentInput } from "@shared/types/index.js";

// ---------------------------------------------------------------------------
// Helpers — DB en mémoire avec migrations
// ---------------------------------------------------------------------------

const MIGRATIONS_DIR = path.resolve(__dirname, "../../src/main/db/migrations");

function makeDb(): sqlite3.Database {
  const db = new sqlite3.Database();
  runMigrations(db as never, MIGRATIONS_DIR);
  // Créer un projet + chapter de test (schéma réel : path NOT NULL UNIQUE, pas de version)
  db.prepare(
    "INSERT INTO projects (id, name, source_language, target_language, path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
  ).run(["proj-1", "Test", "en", "fr", "/tmp/test", "2026-01-01", "2026-01-01"]);
  db.prepare(
    "INSERT INTO chapters (id, project_id, title, order_index, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
  ).run(["ch1", "proj-1", "Chapter 1", 0, "translated", "2026-01-01", "2026-01-01"]);
  return db;
}

const CONFIG = { providerId: "ollama", model: "qwen3.5:9b" };

function makeParagraphs(): AgentInput["paragraphs"] {
  return [
    {
      id: "p1",
      chapterId: "ch1",
      indexInChapter: 0,
      sourceText: "The hero entered the dark cave.",
      translatedText: "Le héros entra dans la grotte sombre.",
      status: "translated",
    },
  ];
}

// ---------------------------------------------------------------------------
// SummarizerAgent
// ---------------------------------------------------------------------------

describe("SummarizerAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn(),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("produit chapterSummary + novelSummary depuis une sortie LLM JSON", async () => {
    const llmOutput = {
      chapterSummary: "The hero enters a dark cave.",
      novelSummary: "A hero explores a mysterious cave.",
    };
    mockRouter.chat = vi.fn().mockResolvedValue(JSON.stringify(llmOutput));
    mockRouter.tryParseJson = vi.fn().mockReturnValue(llmOutput);

    const agent = new SummarizerAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: makeParagraphs(),
    });

    expect(output.metadata?.chapterSummary).toBe("The hero enters a dark cave.");
    expect(output.metadata?.novelSummary).toBe("A hero explores a mysterious cave.");
  });

  it("refus éthique → résumé inchangé + flag", async () => {
    mockRouter.chat = vi.fn().mockResolvedValue("I cannot summarize this.");
    mockRouter.isEthicalRefusal = vi.fn().mockReturnValue(true);

    const agent = new SummarizerAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: makeParagraphs(),
      options: { novelSummary: "previous summary" },
    });

    expect(output.metadata?.novelSummary).toBe("previous summary");
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("chapitre vide → skipped", async () => {
    const agent = new SummarizerAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
    });

    expect(output.metadata?.skipped).toBe(true);
    expect(mockRouter.chat).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// SummaryRepository (avec vraie DB)
// ---------------------------------------------------------------------------

describe("SummaryRepository", () => {
  let db: sqlite3.Database;
  let repo: SummaryRepository;

  beforeEach(() => {
    db = makeDb();
    repo = new SummaryRepository(db as never);
  });

  it("upsert/get chapter summary", () => {
    repo.upsertChapterSummary({
      chapterId: "ch1",
      projectId: "proj-1",
      summary: "Chapter 1 summary.",
    });
    const got = repo.getChapterSummary("ch1");
    expect(got).not.toBeNull();
    expect(got!.summary).toBe("Chapter 1 summary.");

    // Upsert (même chapter_id → update)
    repo.upsertChapterSummary({
      chapterId: "ch1",
      projectId: "proj-1",
      summary: "Updated chapter 1 summary.",
    });
    const updated = repo.getChapterSummary("ch1");
    expect(updated!.summary).toBe("Updated chapter 1 summary.");
  });

  it("upsert novel summary incrémente la version", () => {
    const v1 = repo.upsertNovelSummary("proj-1", "First summary.");
    expect(v1.version).toBe(1);

    const v2 = repo.upsertNovelSummary("proj-1", "Second summary.");
    expect(v2.version).toBe(2);
    expect(v2.summary).toBe("Second summary.");

    // Singleton par projet
    const all = repo.listChapterSummaries("proj-1");
    expect(all).toHaveLength(0); // pas de chapter summary inséré ici
  });

  it("getNovelSummary retourne null si absent", () => {
    expect(repo.getNovelSummary("nonexistent")).toBeNull();
  });
});

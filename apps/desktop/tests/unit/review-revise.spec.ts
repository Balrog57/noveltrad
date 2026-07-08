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

import { ReviewAgent } from "../../src/main/services/agents/ReviewAgent";
import { ReviseAgent } from "../../src/main/services/agents/ReviseAgent";
import { AgentFactory } from "../../src/main/services/agents/AgentFactory";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { AgentInput } from "@shared/types/index.js";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CONFIG = { providerId: "ollama", model: "qwen3.5:9b" };

function makeParagraphs(): AgentInput["paragraphs"] {
  return [
    {
      id: "p1",
      chapterId: "ch1",
      indexInChapter: 0,
      sourceText: "The dragon flew over the mountains.",
      translatedText: "Le dragon a couru vite.",
      status: "translated",
    },
    {
      id: "p2",
      chapterId: "ch1",
      indexInChapter: 1,
      sourceText: "She drew her sword.",
      translatedText: "Elle tira son épée.",
      status: "translated",
    },
  ];
}

// ---------------------------------------------------------------------------
// ReviewAgent
// ---------------------------------------------------------------------------

describe("ReviewAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn(),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("produit un ReviewReport valide depuis une sortie LLM JSON", async () => {
    const llmReport = {
      issues: [
        {
          paragraphIndex: 0,
          severity: "high",
          category: "fidelity",
          original: "a couru vite",
          suggestion: "s'est élancé à toute vitesse",
          reason: "Source implies flight, not running.",
        },
      ],
      summary: "Fidelity issue in paragraph 0.",
    };
    mockRouter.chat = vi.fn().mockResolvedValue(JSON.stringify(llmReport));
    mockRouter.tryParseJson = vi.fn().mockReturnValue(llmReport);

    const agent = new ReviewAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: makeParagraphs(),
      options: { targetLanguage: "French" },
    });

    expect(output.report).toBeDefined();
    const report = output.report as { issues: unknown[]; summary: string };
    expect(report.issues).toHaveLength(1);
    expect(report.summary).toBe("Fidelity issue in paragraph 0.");
    // Score abaissé car 1 issue high
    expect(output.score).toBeLessThan(100);
    expect(output.score).toBeGreaterThanOrEqual(40);
  });

  it("retourne un rapport vide en cas de refus éthique", async () => {
    mockRouter.chat = vi.fn().mockResolvedValue("I cannot translate this content.");
    mockRouter.isEthicalRefusal = vi.fn().mockReturnValue(true);

    const agent = new ReviewAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: makeParagraphs(),
    });

    const report = output.report as { issues: unknown[] };
    expect(report.issues).toHaveLength(0);
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("fallback : rapport vide si le LLM échoue", async () => {
    mockRouter.chat = vi.fn().mockRejectedValue(new Error("network"));

    const agent = new ReviewAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: makeParagraphs(),
    });

    const report = output.report as { issues: unknown[] };
    expect(report.issues).toHaveLength(0);
    expect(output.score).toBe(90);
  });

  it("normalise les sévérités/catégories invalides", async () => {
    const llmReport = {
      issues: [
        { paragraphIndex: 0, severity: "critical", category: "typo", original: "x", suggestion: "y", reason: "z" },
      ],
      summary: "test",
    };
    mockRouter.chat = vi.fn().mockResolvedValue(JSON.stringify(llmReport));
    mockRouter.tryParseJson = vi.fn().mockReturnValue(llmReport);

    const agent = new ReviewAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: makeParagraphs(),
    });

    const report = output.report as { issues: Array<{ severity: string; category: string }> };
    expect(report.issues[0].severity).toBe("medium"); // fallback
    expect(report.issues[0].category).toBe("fidelity"); // fallback
  });
});

// ---------------------------------------------------------------------------
// ReviseAgent
// ---------------------------------------------------------------------------

describe("ReviseAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("Le dragon s'élança à toute vitesse.\n\nElle tira son épée."),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("applique les corrections du ReviewReport", async () => {
    const agent = new ReviseAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon a couru vite.\n\nElle tira son épée.",
      options: {
        reviewReport: {
          issues: [
            {
              paragraphIndex: 0,
              severity: "high",
              category: "fidelity",
              original: "a couru vite",
              suggestion: "s'est élancé à toute vitesse",
              reason: "Source implies flight.",
            },
          ],
          summary: "Fix paragraph 0.",
        },
      },
    });

    expect(output.text).toContain("s'élança");
    expect(mockRouter.chat).toHaveBeenCalledTimes(1);
  });

  it("retourne le texte inchangé si aucune issue", async () => {
    const agent = new ReviseAgent(CONFIG, mockRouter);
    const inputText = "Texte sans problème.";
    const output = await agent.execute({
      projectId: "proj-1",
      text: inputText,
      options: { reviewReport: { issues: [], summary: "" } },
    });

    expect(output.text).toBe(inputText);
    expect(mockRouter.chat).not.toHaveBeenCalled();
  });

  it("conservation du texte en cas de refus éthique", async () => {
    mockRouter.isEthicalRefusal = vi.fn().mockReturnValue(true);
    const agent = new ReviseAgent(CONFIG, mockRouter);
    const inputText = "Texte sensible.";
    const output = await agent.execute({
      projectId: "proj-1",
      text: inputText,
      options: {
        reviewReport: {
          issues: [{ paragraphIndex: 0, severity: "low", category: "style", original: "x", suggestion: "y", reason: "z" }],
          summary: "",
        },
      },
    });

    expect(output.text).toBe(inputText);
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// AgentFactory — les nouveaux stages sont bien instanciés
// ---------------------------------------------------------------------------

describe("AgentFactory — review/revise", () => {
  it("crée un ReviewAgent pour le stage 'review'", () => {
    const factory = new AgentFactory({
      aiRouter: {} as AiRouter,
      lexiconEngine: {} as never,
      tmEngine: {} as never,
      consistencyChecker: {} as never,
      qualityChecker: {} as never,
      exportEngine: {} as never,
    });
    const agent = factory.create("review", CONFIG);
    expect(agent).toBeInstanceOf(ReviewAgent);
    expect(agent.stage).toBe("review");
  });

  it("crée un ReviseAgent pour le stage 'revise'", () => {
    const factory = new AgentFactory({
      aiRouter: {} as AiRouter,
      lexiconEngine: {} as never,
      tmEngine: {} as never,
      consistencyChecker: {} as never,
      qualityChecker: {} as never,
      exportEngine: {} as never,
    });
    const agent = factory.create("revise", CONFIG);
    expect(agent).toBeInstanceOf(ReviseAgent);
    expect(agent.stage).toBe("revise");
  });
});

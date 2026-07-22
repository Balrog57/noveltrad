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

import { ProofreaderAgent } from "../../src/main/services/agents/ProofreaderAgent";
import { ValidatorAgent } from "../../src/main/services/agents/ValidatorAgent";
import { AgentFactory } from "../../src/main/services/agents/AgentFactory";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { ConsistencyChecker } from "../../src/main/services/ConsistencyChecker";
import type { QualityChecker } from "../../src/main/services/QualityChecker";
import type { LexiconEngine } from "../../src/main/services/LexiconEngine";
import type { ExportEngine } from "../../src/main/services/ExportEngine";
import type { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";
import type {
  Paragraph,
  QualityReport,
  ConsistencyReport,
} from "@shared/types/index.js";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CONFIG = { providerId: "ollama", model: "qwen3.5:9b" };

function makeParagraph(overrides: Partial<Paragraph> = {}): Paragraph {
  return {
    id: "p1",
    chapterId: "ch1",
    indexInChapter: 0,
    sourceText: "The dragon flew over the mountains.",
    translatedText: "Le dragon survola les montagnes.",
    status: "translated",
    ...overrides,
  };
}

function makeMockRouter(overrides: Partial<AiRouter> = {}): AiRouter {
  return {
    chat: vi.fn().mockResolvedValue("Le dragon survola les montagnes."),
    chatWithChunking: vi
      .fn()
      .mockResolvedValue("Le dragon survola les montagnes."),
    tryParseJson: vi.fn(),
    isEthicalRefusal: vi.fn().mockReturnValue(false),
    resolvePrompt: vi
      .fn()
      .mockImplementation((_id: string, def: string) => Promise.resolve(def)),
    ...overrides,
  } as unknown as AiRouter;
}

const MOCK_CONSISTENCY_REPORT: ConsistencyReport = {
  metrics: [],
  warnings: [],
  globalScore: 90,
};

function makeMockConsistencyChecker(): ConsistencyChecker {
  return {
    check: vi.fn().mockReturnValue(MOCK_CONSISTENCY_REPORT),
  } as unknown as ConsistencyChecker;
}

function makeMockQualityChecker(report?: Partial<QualityReport>): QualityChecker {
  const fullReport: QualityReport = {
    consistency: 85,
    grammar: 90,
    fluency: 88,
    style: 82,
    lexicon: 95,
    hallucination: 100,
    length: 80,
    dialogue: 90,
    globalScore: 87,
    comments: "",
    ...report,
  };
  return {
    evaluate: vi.fn().mockResolvedValue(fullReport),
  } as unknown as QualityChecker;
}

// ---------------------------------------------------------------------------
// ProofreaderAgent (v3 : fusion grammar + style + polish)
// ---------------------------------------------------------------------------

describe("ProofreaderAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = makeMockRouter();
  });

  it("devrait raffiner le texte via le prompt unifié", async () => {
    const agent = new ProofreaderAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon survola les montagnes.",
      options: { targetLanguage: "fr" },
    });
    expect(output.text).toBe("Le dragon survola les montagnes.");
    expect(mockRouter.chatWithChunking).toHaveBeenCalledOnce();
  });

  it("devrait détecter un refus éthique et conserver le texte d'entrée", async () => {
    (mockRouter.isEthicalRefusal as ReturnType<typeof vi.fn>).mockReturnValue(
      true,
    );
    const agent = new ProofreaderAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Texte original.",
      options: { targetLanguage: "fr" },
    });
    expect(output.text).toBe("Texte original.");
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("devrait exposer l'identité v3 (stage proofread)", () => {
    const agent = new ProofreaderAgent(CONFIG, mockRouter);
    expect(agent.id).toBe("proofread");
    expect(agent.name).toBe("Proofreader");
    expect(agent.stage).toBe("proofread");
  });

  it("devrait propager les erreurs AI", async () => {
    (mockRouter.chatWithChunking as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Erreur réseau"),
    );
    const agent = new ProofreaderAgent(CONFIG, mockRouter);
    await expect(
      agent.execute({ projectId: "proj-1", text: "test" }),
    ).rejects.toThrow("Erreur réseau");
  });
});

// ---------------------------------------------------------------------------
// ValidatorAgent (v3 : fusion consistency + qa)
// ---------------------------------------------------------------------------

describe("ValidatorAgent", () => {
  let mockRouter: AiRouter;
  let mockQuality: QualityChecker;
  let mockConsistency: ConsistencyChecker;

  beforeEach(() => {
    mockRouter = makeMockRouter({
      chat: vi.fn().mockResolvedValue(
        JSON.stringify({
          consistency: 92,
          grammar: 90,
          fluency: 88,
          style: 85,
          lexicon: 95,
          hallucination: 97,
          length: 80,
          dialogue: 90,
          globalScore: 90,
          comments: "Bonne traduction.",
          suspectSentences: [],
          consistencyWarnings: [],
        }),
      ),
      tryParseJson: vi
        .fn()
        .mockImplementation((raw: string) => JSON.parse(raw)),
    });
    mockQuality = makeMockQualityChecker();
    mockConsistency = makeMockConsistencyChecker();
  });

  it("devrait évaluer la qualité et retourner un score + report", async () => {
    const agent = new ValidatorAgent(
      CONFIG,
      mockRouter,
      mockQuality,
      mockConsistency,
    );
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });
    expect(output.score).toBe(90);
    expect(output.report).toBeDefined();
    const report = output.report as QualityReport;
    expect(report.globalScore).toBe(90);
    expect(report.grammar).toBe(90);
  });

  it("devrait parser suspectSentences depuis la sortie LLM", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      JSON.stringify({
        consistency: 60,
        grammar: 65,
        fluency: 70,
        style: 68,
        lexicon: 90,
        hallucination: 95,
        length: 80,
        dialogue: 75,
        globalScore: 65,
        comments: "Plusieurs phrases problématiques.",
        suspectSentences: [
          {
            sentence: "Le dragon volaient.",
            score: 35,
            issue: "erreur d'accord",
          },
        ],
        consistencyWarnings: [
          { severity: "medium", message: "Name drift: 'Drako' vs 'Draco'." },
        ],
      }),
    );
    const agent = new ValidatorAgent(
      CONFIG,
      mockRouter,
      mockQuality,
      mockConsistency,
    );
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    const report = output.report as QualityReport;
    expect(report.suspectSentences).toHaveLength(1);
    expect(report.suspectSentences![0].score).toBe(35);
  });

  it("devrait calculer le ConsistencyReport heuristique en interne", async () => {
    const agent = new ValidatorAgent(
      CONFIG,
      mockRouter,
      mockQuality,
      mockConsistency,
    );
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });
    // Le ConsistencyChecker doit être appelé (internalisation de l'ancien stage).
    expect(mockConsistency.check).toHaveBeenCalledOnce();
  });

  it("devrait utiliser le fallback heuristique si le LLM échoue", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("LLM indisponible"),
    );
    const agent = new ValidatorAgent(
      CONFIG,
      mockRouter,
      mockQuality,
      mockConsistency,
    );
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    // Score vient du fallback QualityChecker (globalScore 87).
    expect(output.score).toBe(87);
    expect(mockQuality.evaluate).toHaveBeenCalledOnce();
  });

  it("devrait utiliser le fallback si le JSON LLM est invalide", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      "ceci n'est pas du json",
    );
    (mockRouter.tryParseJson as ReturnType<typeof vi.fn>).mockReturnValue(null);
    const agent = new ValidatorAgent(
      CONFIG,
      mockRouter,
      mockQuality,
      mockConsistency,
    );
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    expect(output.score).toBe(87);
    expect(mockQuality.evaluate).toHaveBeenCalledOnce();
  });

  it("devrait exposer l'identité v3 (stage validate)", () => {
    const agent = new ValidatorAgent(
      CONFIG,
      mockRouter,
      mockQuality,
      mockConsistency,
    );
    expect(agent.id).toBe("validate");
    expect(agent.name).toBe("Validator");
    expect(agent.stage).toBe("validate");
  });
});

// ---------------------------------------------------------------------------
// AgentFactory — cas v3
// ---------------------------------------------------------------------------

describe("AgentFactory — stages v3", () => {
  function makeFactory(router: AiRouter) {
    return new AgentFactory({
      aiRouter: router,
      lexiconEngine: {} as LexiconEngine,
      tmEngine: {} as TranslationMemoryEngine,
      consistencyChecker: {} as ConsistencyChecker,
      qualityChecker: {} as QualityChecker,
      exportEngine: {} as ExportEngine,
    });
  }

  it("devrait créer un ProofreaderAgent pour le stage 'proofread'", () => {
    const factory = makeFactory(makeMockRouter());
    const agent = factory.create("proofread", CONFIG);
    expect(agent).toBeInstanceOf(ProofreaderAgent);
    expect(agent.stage).toBe("proofread");
  });

  it("devrait créer un ValidatorAgent pour le stage 'validate'", () => {
    const factory = makeFactory(makeMockRouter());
    const agent = factory.create("validate", CONFIG);
    expect(agent).toBeInstanceOf(ValidatorAgent);
    expect(agent.stage).toBe("validate");
  });

  it("devrait toujours créer les agents historiques (transition v3)", () => {
    const factory = makeFactory(makeMockRouter());
    // grammar/style/polish/qa/consistency toujours disponibles.
    expect(factory.create("grammar", CONFIG)).toBeDefined();
    expect(factory.create("style", CONFIG)).toBeDefined();
    expect(factory.create("polish", CONFIG)).toBeDefined();
    expect(factory.create("qa", CONFIG)).toBeDefined();
    expect(factory.create("consistency", CONFIG)).toBeDefined();
  });
});

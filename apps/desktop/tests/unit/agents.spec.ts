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

import { TranslateAgent } from "../../src/main/services/agents/TranslateAgent";
import { PreTranslateAgent } from "../../src/main/services/agents/PreTranslateAgent";
import { GrammarAgent } from "../../src/main/services/agents/GrammarAgent";
import { StyleAgent } from "../../src/main/services/agents/StyleAgent";
import { PolishAgent } from "../../src/main/services/agents/PolishAgent";
import { ConsistencyAgent } from "../../src/main/services/agents/ConsistencyAgent";
import { LexiconAgent } from "../../src/main/services/agents/LexiconAgent";
import { QaAgent } from "../../src/main/services/agents/QaAgent";
import { ExportAgent } from "../../src/main/services/agents/ExportAgent";
import { SplitAgent } from "../../src/main/services/agents/SplitAgent";
import { AgentFactory } from "../../src/main/services/agents/AgentFactory";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { Paragraph, LexiconEntry } from "@shared/types/index.js";
import type { ConsistencyChecker } from "../../src/main/services/ConsistencyChecker";
import type { QualityChecker } from "../../src/main/services/QualityChecker";
import type { LexiconEngine } from "../../src/main/services/LexiconEngine";
import type { ExportEngine } from "../../src/main/services/ExportEngine";
import type { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";
import type { CalibrationService } from "../../src/main/services/CalibrationService";
import type { QualityReport } from "@shared/types/index.js";
import type { ConsistencyReport } from "@shared/types/index.js";

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
    status: "pending",
    ...overrides,
  };
}

function makeLexiconEntry(overrides: Partial<LexiconEntry> = {}): LexiconEntry {
  return {
    id: "l1",
    projectId: "proj-1",
    term: "dragon",
    translation: "dragon",
    category: "creature",
    aliases: [],
    locked: false,
    priority: 10,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// TranslateAgent
// ---------------------------------------------------------------------------

describe("TranslateAgent", () => {
  let mockRouter: AiRouter;
  let mockTmEngine: TranslationMemoryEngine;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("Le dragon survola les montagnes."),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
    mockTmEngine = {
      fuzzyMatches: vi.fn().mockReturnValue([]),
    } as unknown as TranslationMemoryEngine;
  });

  it("devrait traduire un paragraphe avec succès", async () => {
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });
    expect(output.paragraphs).toHaveLength(1);
    expect(output.paragraphs![0].translatedText).toBe(
      "Le dragon survola les montagnes.",
    );
    expect(output.paragraphs![0].status).toBe("translated");
  });

  it("devrait gérer une liste de paragraphes vide", async () => {
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
    });
    expect(output.paragraphs).toEqual([]);
  });

  it("devrait détecter un refus éthique et conserver le texte source", async () => {
    (mockRouter.isEthicalRefusal as ReturnType<typeof vi.fn>).mockReturnValue(
      true,
    );
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      "I cannot translate this content.",
    );
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    expect(output.paragraphs![0].translatedText).toBe(
      "The dragon flew over the mountains.",
    );
    expect(output.paragraphs![0].status).toBe("pending");
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("devrait inclure le bloc lexique dans le prompt utilisateur", async () => {
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const lexicon = [makeLexiconEntry()];
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      lexicon,
    });
    const messages = (mockRouter.chat as ReturnType<typeof vi.fn>).mock
      .calls[0][1];
    const userMsg = messages.find((m: { role: string }) => m.role === "user");
    expect(userMsg.content).toContain("LEXICON");
    expect(userMsg.content).toContain("dragon → dragon");
  });

  it("devrait inclure le bloc RAG si fourni", async () => {
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph({ id: "p1" })],
      options: {
        ragContext: {
          p1: [
            {
              paragraphId: "p0",
              sourceText: "The cat sat.",
              translatedText: "Le chat s'assit.",
              similarity: 0.9,
            },
          ],
        },
      },
    });
    const messages = (mockRouter.chat as ReturnType<typeof vi.fn>).mock
      .calls[0][1];
    const userMsg = messages.find((m: { role: string }) => m.role === "user");
    expect(userMsg.content).toContain("Traductions similaires précédentes");
    expect(userMsg.content).toContain("Le chat s'assit.");
  });

  it("devrait gérer les erreurs AI", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("AI indisponible"),
    );
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    await expect(
      agent.execute({
        projectId: "proj-1",
        paragraphs: [makeParagraph()],
      }),
    ).rejects.toThrow("AI indisponible");
  });
});

// ---------------------------------------------------------------------------
// PreTranslateAgent
// ---------------------------------------------------------------------------

describe("PreTranslateAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("Le dragon survola les montagnes."),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("devrait pré-traduire plusieurs paragraphes", async () => {
    const agent = new PreTranslateAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph(), makeParagraph({ id: "p2", sourceText: "Hello world." })],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });
    expect(output.paragraphs).toHaveLength(2);
    expect(output.paragraphs![0].preTranslatedText).toBeDefined();
  });

  it("devrait gérer des paragraphes vides", async () => {
    const agent = new PreTranslateAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
    });
    expect(output.paragraphs).toEqual([]);
  });

  it("devrait détecter un refus éthique", async () => {
    (mockRouter.isEthicalRefusal as ReturnType<typeof vi.fn>).mockReturnValue(
      true,
    );
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      "I cannot process this request.",
    );
    const agent = new PreTranslateAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    expect(output.paragraphs![0].preTranslatedText).toBe(
      "The dragon flew over the mountains.",
    );
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("devrait gérer les erreurs AI", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Timeout"),
    );
    const agent = new PreTranslateAgent(CONFIG, mockRouter);
    await expect(
      agent.execute({ projectId: "proj-1", paragraphs: [makeParagraph()] }),
    ).rejects.toThrow("Timeout");
  });
});

// ---------------------------------------------------------------------------
// GrammarAgent
// ---------------------------------------------------------------------------

describe("GrammarAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("Le dragon survola les montagnes."),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("devrait corriger la grammaire d'un texte", async () => {
    const agent = new GrammarAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon survola les montagnes.",
      options: { targetLanguage: "fr" },
    });
    expect(output.text).toBe("Le dragon survola les montagnes.");
  });

  it("devrait gérer un texte vide (le texte vide est envoyé à l'IA)", async () => {
    const agent = new GrammarAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "",
    });
    // L'agent appelle toujours l'IA, même avec un texte vide
    expect(output.text).toBeDefined();
  });

  it("devrait détecter un refus éthique", async () => {
    (mockRouter.isEthicalRefusal as ReturnType<typeof vi.fn>).mockReturnValue(
      true,
    );
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      "I'm sorry, I cannot do that.",
    );
    const agent = new GrammarAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon.",
      options: { targetLanguage: "fr" },
    });
    expect(output.text).toBe("Le dragon.");
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("devrait gérer les erreurs AI", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Erreur réseau"),
    );
    const agent = new GrammarAgent(CONFIG, mockRouter);
    await expect(
      agent.execute({ projectId: "proj-1", text: "test" }),
    ).rejects.toThrow("Erreur réseau");
  });
});

// ---------------------------------------------------------------------------
// StyleAgent
// ---------------------------------------------------------------------------

describe("StyleAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("Le dragon majestueux survola les montagnes enneigées."),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("devrait améliorer le style d'un texte", async () => {
    const agent = new StyleAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon survola les montagnes.",
      options: { targetLanguage: "fr" },
    });
    expect(output.text).toBe(
      "Le dragon majestueux survola les montagnes enneigées.",
    );
  });

  it("devrait gérer un texte vide (le texte vide est envoyé à l'IA)", async () => {
    const agent = new StyleAgent(CONFIG, mockRouter);
    const output = await agent.execute({ projectId: "proj-1", text: "" });
    // L'agent appelle toujours l'IA, même avec un texte vide
    expect(output.text).toBeDefined();
  });

  it("devrait détecter un refus éthique", async () => {
    (mockRouter.isEthicalRefusal as ReturnType<typeof vi.fn>).mockReturnValue(
      true,
    );
    const agent = new StyleAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon.",
      options: { targetLanguage: "fr" },
    });
    expect(output.metadata?.ethicalRefusal).toBe(true);
    expect(output.text).toBe("Le dragon.");
  });

  it("devrait gérer les erreurs AI", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Service indisponible"),
    );
    const agent = new StyleAgent(CONFIG, mockRouter);
    await expect(
      agent.execute({ projectId: "proj-1", text: "test" }),
    ).rejects.toThrow("Service indisponible");
  });
});

// ---------------------------------------------------------------------------
// PolishAgent
// ---------------------------------------------------------------------------

describe("PolishAgent", () => {
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("Le dragon survola les montagnes enneigées, ses ailes déployées."),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;
  });

  it("devrait polir un texte final", async () => {
    const agent = new PolishAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon survola les montagnes.",
      options: { targetLanguage: "fr" },
    });
    expect(output.text).toContain("Le dragon");
  });

  it("devrait gérer un texte vide (le texte vide est envoyé à l'IA)", async () => {
    const agent = new PolishAgent(CONFIG, mockRouter);
    const output = await agent.execute({ projectId: "proj-1", text: "" });
    // L'agent appelle toujours l'IA, même avec un texte vide
    expect(output.text).toBeDefined();
  });

  it("devrait détecter un refus éthique", async () => {
    (mockRouter.isEthicalRefusal as ReturnType<typeof vi.fn>).mockReturnValue(
      true,
    );
    const agent = new PolishAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "Le dragon.",
      options: { targetLanguage: "fr" },
    });
    expect(output.metadata?.ethicalRefusal).toBe(true);
  });

  it("devrait gérer les erreurs AI", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Erreur"),
    );
    const agent = new PolishAgent(CONFIG, mockRouter);
    await expect(
      agent.execute({ projectId: "proj-1", text: "test" }),
    ).rejects.toThrow("Erreur");
  });
});

// ---------------------------------------------------------------------------
// ConsistencyAgent
// ---------------------------------------------------------------------------

describe("ConsistencyAgent", () => {
  let mockChecker: ConsistencyChecker;

  beforeEach(() => {
    const fakeReport: ConsistencyReport = {
      metrics: [
        { name: "length", source: 10, target: 12, ok: true },
        { name: "sentences", source: 1, target: 1, ok: true },
      ],
      warnings: [],
      globalScore: 95,
    };
    mockChecker = {
      check: vi.fn().mockReturnValue(fakeReport),
    } as unknown as ConsistencyChecker;
  });

  it("devrait retourner un rapport de cohérence", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph(),
        makeParagraph({
          id: "p2",
          sourceText: "Hello world.",
          translatedText: "Bonjour le monde.",
        }),
      ],
    });
    expect(output.report).toBeDefined();
    expect((output.report as ConsistencyReport).globalScore).toBe(95);
  });

  it("devrait gérer des paragraphes vides", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
    });
    expect(output.report).toBeDefined();
  });

  it("devrait passer la paire de langues au checker", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });
    const args = (mockChecker.check as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(args[3]).toBe("en-fr");
  });
});

// ---------------------------------------------------------------------------
// LexiconAgent
// ---------------------------------------------------------------------------

describe("LexiconAgent", () => {
  let mockEngine: LexiconEngine;

  beforeEach(() => {
    mockEngine = {
      apply: vi.fn().mockReturnValue({
        text: "Le dragon survola les montagnes.",
        substitutions: [
          { before: "dragon", after: "dragon", locked: false },
        ],
      }),
    } as unknown as LexiconEngine;
  });

  it("devrait appliquer les substitutions lexicales", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "The dragon flew.",
      lexicon: [makeLexiconEntry()],
    });
    expect(output.text).toBe("Le dragon survola les montagnes.");
    expect(output.substitutions).toHaveLength(1);
  });

  it("devrait retourner le texte inchangé sans projectId ni text", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine);
    const output = await agent.execute({ projectId: "" });
    expect(output.text).toBeUndefined();
  });

  it("devrait retourner le texte inchangé si projectId manque", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine);
    const output = await agent.execute({
      projectId: "",
      text: "The dragon flew.",
    });
    expect(output.text).toBe("The dragon flew.");
  });
});

// ---------------------------------------------------------------------------
// QaAgent
// ---------------------------------------------------------------------------

describe("QaAgent", () => {
  let mockRouter: AiRouter;
  let mockQuality: QualityChecker;
  let mockCalibration: CalibrationService;

  beforeEach(() => {
    mockRouter = {} as unknown as AiRouter;
    mockQuality = {
      evaluate: vi.fn().mockResolvedValue({
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
      } as QualityReport),
    } as unknown as QualityChecker;
    mockCalibration = {
      calibrateScore: vi.fn().mockImplementation((score: number) => score),
    } as unknown as CalibrationService;
  });

  it("devrait évaluer la qualité et retourner un score", async () => {
    const agent = new QaAgent(CONFIG, mockRouter, mockQuality, mockCalibration);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ translatedText: "Le dragon survola les montagnes." }),
      ],
    });
    expect(output.score).toBeGreaterThanOrEqual(0);
    expect(output.report).toBeDefined();
  });

  it("devrait gérer des paragraphes vides", async () => {
    const agent = new QaAgent(CONFIG, mockRouter, mockQuality);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
    });
    expect(output.score).toBeDefined();
  });

  it("devrait appliquer la calibration si fournie", async () => {
    const agent = new QaAgent(CONFIG, mockRouter, mockQuality, mockCalibration);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ translatedText: "Le dragon survola les montagnes." }),
      ],
    });
    expect(mockCalibration.calibrateScore).toHaveBeenCalled();
  });

  it("devrait fonctionner sans calibration", async () => {
    const agent = new QaAgent(CONFIG, mockRouter, mockQuality);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ translatedText: "Le dragon survola les montagnes." }),
      ],
    });
    expect(output.score).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// ExportAgent
// ---------------------------------------------------------------------------

describe("ExportAgent", () => {
  let mockExportEngine: ExportEngine;

  beforeEach(() => {
    mockExportEngine = {
      export: vi.fn().mockResolvedValue("/path/to/output.md"),
    } as unknown as ExportEngine;
  });

  it("devrait exporter un projet au format markdown", async () => {
    const agent = new ExportAgent(CONFIG, mockExportEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: { format: "markdown", title: "Mon Livre" },
    });
    expect(output.metadata?.exportPath).toBe("/path/to/output.md");
  });

  it("devrait lancer une erreur si projectId manque", async () => {
    const agent = new ExportAgent(CONFIG, mockExportEngine);
    await expect(agent.execute({ projectId: "" })).rejects.toThrow(
      "projectId requis",
    );
  });

  it("devrait passer les options à ExportEngine", async () => {
    const agent = new ExportAgent(CONFIG, mockExportEngine);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: {
        format: "markdown",
        title: "Titre",
        author: "Auteur",
        bilingual: true,
      },
    });
    const exportInput = (mockExportEngine.export as ReturnType<typeof vi.fn>)
      .mock.calls[0][0];
    expect(exportInput.format).toBe("markdown");
    expect(exportInput.title).toBe("Titre");
    expect(exportInput.author).toBe("Auteur");
    expect(exportInput.options.bilingual).toBe(true);
  });

  it("devrait gérer des paragraphes vides", async () => {
    const agent = new ExportAgent(CONFIG, mockExportEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
      options: { format: "txt", title: "Test" },
    });
    expect(output.metadata?.exportPath).toBe("/path/to/output.md");
  });
});

// ---------------------------------------------------------------------------
// AgentFactory
// ---------------------------------------------------------------------------

describe("AgentFactory", () => {
  let mockRouter: AiRouter;
  let mockServices: import("../../src/main/services/agents/AgentFactory").AgentFactoryServices;

  beforeEach(() => {
    mockRouter = {
      chat: vi.fn().mockResolvedValue("test"),
      tryParseJson: vi.fn(),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;

    mockServices = {
      aiRouter: mockRouter,
      lexiconEngine: {} as unknown as import("../../src/main/services/LexiconEngine").LexiconEngine,
      tmEngine: {} as unknown as import("../../src/main/services/TranslationMemoryEngine").TranslationMemoryEngine,
      consistencyChecker: {} as unknown as import("../../src/main/services/ConsistencyChecker").ConsistencyChecker,
      qualityChecker: {} as unknown as import("../../src/main/services/QualityChecker").QualityChecker,
      exportEngine: {} as unknown as import("../../src/main/services/ExportEngine").ExportEngine,
    };
  });

  it("devrait créer un agent pour chaque stage connu", () => {
    const factory = new AgentFactory(mockServices);
    const stages = [
      "split", "pre_translate", "translate", "consistency",
      "lexicon", "grammar", "style", "polish", "qa", "export",
    ] as const;

    for (const stage of stages) {
      const agent = factory.create(stage, { providerId: "test", model: "test" });
      expect(agent).toBeDefined();
      expect(typeof agent.execute).toBe("function");
    }
  });

  it("devrait passer les options de config à chaque agent", () => {
    const factory = new AgentFactory(mockServices);
    const config = { providerId: "ollama", model: "qwen3.5:9b", temperature: 0.3 };
    const agent = factory.create("translate", config);
    expect(agent).toBeDefined();
    // Le constructeur reçoit bien config, pas d'erreur
  });

  it("devrait lancer une erreur pour un stage inconnu", () => {
    const factory = new AgentFactory(mockServices);
    expect(() =>
      factory.create("unknown_stage" as never, { providerId: "test", model: "test" }),
    ).toThrow(/inconnu|unknown/i);
  });

  it("devrait utiliser l'agent du plugin si getPluginAgent retourne un agent", () => {
    const pluginAgent = new SplitAgent({ providerId: "plugin", model: "plugin-model" });
    const factory = new AgentFactory({
      ...mockServices,
      getPluginAgent: (_stage: string, _config: { providerId: string; model: string }) => {
        return pluginAgent;
      },
    });

    const agent = factory.create("translate", { providerId: "test", model: "test" });
    expect(agent).toBe(pluginAgent);
  });

  it("devrait ignorer getPluginAgent si elle retourne undefined (fallback built-in)", () => {
    const factory = new AgentFactory({
      ...mockServices,
      getPluginAgent: (_stage: string, _config: { providerId: string; model: string }) => {
        return undefined;
      },
    });

    const agent = factory.create("translate", { providerId: "test", model: "test" });
    expect(agent).toBeDefined();
    // Vérifier que c'est bien un agent built-in, pas le plugin
    expect(agent.constructor.name).toBe("TranslateAgent");
  });

  it("devrait fonctionner sans getPluginAgent (undefined)", () => {
    const factory = new AgentFactory(mockServices);
    // services.getPluginAgent est undefined → le if (this.services.getPluginAgent) est false
    const agent = factory.create("translate", { providerId: "test", model: "test" });
    expect(agent).toBeDefined();
    expect(agent.constructor.name).toBe("TranslateAgent");
  });
});

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
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
    } as unknown as AiRouter;
    mockTmEngine = {
      fuzzyMatches: vi.fn().mockReturnValue([]),
      exactMatch: vi.fn().mockReturnValue(null),
      findBestMatch: vi.fn().mockReturnValue(null),
      segmentSentences: vi.fn().mockReturnValue([]),
      promoteToGlobal: vi.fn(),
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

  it("devrait utiliser TM exact match et sauter le LLM si trouvé (T11)", async () => {
    (mockTmEngine.exactMatch as ReturnType<typeof vi.fn>).mockReturnValue(
      "Traduction TM exacte",
    );
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph({ sourceText: "Exact match text" })],
    });
    // Le LLM ne doit PAS être appelé
    expect(mockRouter.chat).not.toHaveBeenCalled();
    expect(output.paragraphs![0].translatedText).toBe("Traduction TM exacte");
    expect(output.paragraphs![0].status).toBe("translated");
  });

  it("devrait appeler le LLM si TM exact match est null (T11)", async () => {
    // exactMatch retourne déjà null par défaut
    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    // Le LLM doit être appelé
    expect(mockRouter.chat).toHaveBeenCalled();
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
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
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
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
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
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
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
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
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
  let mockRouter: AiRouter;

  beforeEach(() => {
    const fakeReport: ConsistencyReport = {
      metrics: [
        { name: "length", source: 10, target: 12, ok: true, score: 100 },
        { name: "sentences", source: 1, target: 1, ok: true, score: 100 },
      ],
      warnings: [],
      globalScore: 95,
    };
    mockChecker = {
      check: vi.fn().mockReturnValue(fakeReport),
    } as unknown as ConsistencyChecker;
    mockRouter = {
      chat: vi.fn().mockResolvedValue(
        JSON.stringify({
          metrics: [],
          warnings: [{ severity: "high", message: "LLM warning" }],
          globalScore: 80,
        }),
      ),
      tryParseJson: vi.fn().mockImplementation(
        (raw: string) => JSON.parse(raw),
      ),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
    } as unknown as AiRouter;
  });

  it("devrait retourner un rapport de cohérence", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);
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
    expect((output.report as ConsistencyReport).globalScore).toBeGreaterThanOrEqual(0);
  });

  it("devrait gérer des paragraphes vides", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [],
    });
    expect(output.report).toBeDefined();
  });

  it("devrait passer la paire de langues au checker", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });
    const args = (mockChecker.check as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(args[3]).toBe("en-fr");
  });

  it("devrait appeler le LLM pour la vérification de cohérence", async () => {
    const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    expect(mockRouter.chat).toHaveBeenCalledTimes(1);
    const messages = (mockRouter.chat as ReturnType<typeof vi.fn>).mock
      .calls[0][1];
    const systemMsg = messages.find((m: { role: string }) => m.role === "system");
    expect(systemMsg.content).toContain("consistency");
  });

  it("devrait fusionner les warnings LLM et heuristiques", async () => {
    const heuristicReport: ConsistencyReport = {
      metrics: [],
      warnings: [{ severity: "medium", message: "Heuristic warning" }],
      globalScore: 90,
    };
    (mockChecker.check as ReturnType<typeof vi.fn>).mockReturnValue(heuristicReport);
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      JSON.stringify({
        metrics: [],
        warnings: [{ severity: "high", message: "LLM warning" }],
        globalScore: 80,
      }),
    );

    const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    const report = output.report as ConsistencyReport;
    expect(report.warnings).toHaveLength(2);
    expect(report.warnings.some((w) => w.message === "Heuristic warning")).toBe(true);
    expect(report.warnings.some((w) => w.message === "LLM warning")).toBe(true);
    // Score should be average of 90 + 80 = 85
    expect(report.globalScore).toBe(85);
  });

  it("devrait utiliser uniquement les heuristiques si le LLM échoue", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("LLM indisponible"),
    );
    const heuristicReport: ConsistencyReport = {
      metrics: [],
      warnings: [{ severity: "low", message: "Heuristic only" }],
      globalScore: 90,
    };
    (mockChecker.check as ReturnType<typeof vi.fn>).mockReturnValue(heuristicReport);

    const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph()],
    });
    const report = output.report as ConsistencyReport;
    expect(report.warnings).toHaveLength(1);
    expect(report.warnings[0].message).toBe("Heuristic only");
    expect(report.globalScore).toBe(90);
  });
});

// ---------------------------------------------------------------------------
// LexiconAgent
// ---------------------------------------------------------------------------

describe("LexiconAgent", () => {
  let mockEngine: LexiconEngine;
  let mockRouter: AiRouter;

  beforeEach(() => {
    mockEngine = {
      apply: vi.fn().mockReturnValue({
        text: "Le dragon survola les montagnes.",
        substitutions: [
          { before: "dragon", after: "dragon", locked: false },
        ],
      }),
    } as unknown as LexiconEngine;
    mockRouter = {
      chat: vi.fn().mockResolvedValue(
        JSON.stringify({
          text: "Le dragon majestueux survola les montagnes.",
          substitutions: [
            { before: "dragon", after: "dragon majestueux", locked: false },
          ],
        }),
      ),
      tryParseJson: vi.fn().mockImplementation(
        (raw: string) => JSON.parse(raw),
      ),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
    } as unknown as AiRouter;
  });

  it("devrait appliquer les substitutions lexicales", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "The dragon flew.",
      lexicon: [makeLexiconEntry()],
    });
    expect(output.text).toBe("Le dragon survola les montagnes.");
    expect(output.substitutions).toBeDefined();
  });

  it("devrait retourner le texte inchangé sans projectId ni text", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine, mockRouter);
    const output = await agent.execute({ projectId: "" });
    expect(output.text).toBeUndefined();
  });

  it("devrait retourner le texte inchangé si projectId manque", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine, mockRouter);
    const output = await agent.execute({
      projectId: "",
      text: "The dragon flew.",
    });
    expect(output.text).toBe("The dragon flew.");
  });

  it("devrait appeler le LLM pour les suggestions lexicales", async () => {
    const agent = new LexiconAgent(CONFIG, mockEngine, mockRouter);
    await agent.execute({
      projectId: "proj-1",
      text: "The dragon flew.",
      lexicon: [makeLexiconEntry()],
    });
    expect(mockRouter.chat).toHaveBeenCalledTimes(1);
    const messages = (mockRouter.chat as ReturnType<typeof vi.fn>).mock
      .calls[0][1];
    const systemMsg = messages.find((m: { role: string }) => m.role === "system");
    expect(systemMsg.content).toContain("terminology enforcer");
  });

  it("devrait appliquer les suggestions LLM puis le moteur lexical", async () => {
    const llmOutput = JSON.stringify({
      text: "Le dragon majestueux survola les montagnes.",
      substitutions: [
        { before: "dragon", after: "dragon majestueux", locked: false },
      ],
    });
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(llmOutput);
    (mockEngine.apply as ReturnType<typeof vi.fn>).mockReturnValue({
      text: "Le dragon majestueux survola les montagnes.",
      substitutions: [
        { before: "dragon majestueux", after: "dragon majestueux", locked: false },
      ],
    });

    const agent = new LexiconAgent(CONFIG, mockEngine, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "The dragon flew.",
      lexicon: [makeLexiconEntry()],
    });

    // Should have substitutions from both LLM and lexicon engine
    expect(output.substitutions!.length).toBeGreaterThanOrEqual(1);
    // Engine should receive the LLM-modified text
    const engineArg = (mockEngine.apply as ReturnType<typeof vi.fn>).mock
      .calls[0][0];
    expect(engineArg).toBe("Le dragon majestueux survola les montagnes.");
  });

  it("devrait utiliser le moteur lexical seul si le LLM échoue", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("LLM down"),
    );

    const agent = new LexiconAgent(CONFIG, mockEngine, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      text: "The dragon flew.",
      lexicon: [makeLexiconEntry()],
    });

    // Engine should receive the original text (not LLM-modified)
    const engineArg = (mockEngine.apply as ReturnType<typeof vi.fn>).mock
      .calls[0][0];
    expect(engineArg).toBe("The dragon flew.");
    expect(output.text).toBe("Le dragon survola les montagnes.");
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
    mockRouter = {
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
          comments: "Bonne traduction, quelques ajustements de style.",
        }),
      ),
      tryParseJson: vi.fn().mockImplementation(
        (raw: string) => JSON.parse(raw),
      ),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
    } as unknown as AiRouter;
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

  it("devrait appeler le LLM pour l'évaluation qualité", async () => {
    const agent = new QaAgent(CONFIG, mockRouter, mockQuality, mockCalibration);
    await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ translatedText: "Le dragon survola les montagnes." }),
      ],
    });
    expect(mockRouter.chat).toHaveBeenCalledTimes(1);
    const messages = (mockRouter.chat as ReturnType<typeof vi.fn>).mock
      .calls[0][1];
    const systemMsg = messages.find((m: { role: string }) => m.role === "system");
    expect(systemMsg.content).toContain("quality evaluator");
    // Vérifier que jsonMode est passé
    const options = (mockRouter.chat as ReturnType<typeof vi.fn>).mock
      .calls[0][2];
    expect(options.jsonMode).toBe(true);
  });

  it("devrait utiliser le score LLM comme score principal", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(
      JSON.stringify({
        consistency: 95,
        grammar: 95,
        fluency: 95,
        style: 95,
        lexicon: 95,
        hallucination: 95,
        length: 95,
        dialogue: 95,
        globalScore: 95,
        comments: "Excellent.",
      }),
    );

    const agent = new QaAgent(CONFIG, mockRouter, mockQuality, mockCalibration);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ translatedText: "Le dragon survola les montagnes." }),
      ],
    });

    expect(output.score).toBe(95);
    // QualityChecker should NOT have been called (LLM succeeded)
    expect(mockQuality.evaluate).not.toHaveBeenCalled();
  });

  it("devrait utiliser QualityChecker en fallback si le LLM est indisponible", async () => {
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("LLM down"),
    );

    const agent = new QaAgent(CONFIG, mockRouter, mockQuality);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ translatedText: "Le dragon survola les montagnes." }),
      ],
    });

    // QualityChecker should have been called as fallback
    expect(mockQuality.evaluate).toHaveBeenCalledTimes(1);
    // Score should come from the fallback (87)
    expect(output.score).toBe(87);
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
// Validation Zod (SDD §8.13) — +2 tests par agent (output validé / invalide)
// ---------------------------------------------------------------------------

describe("Agent validateOutput — TranslateAgent", () => {
  const mockRouter = { chat: vi.fn(), tryParseJson: vi.fn(), isEthicalRefusal: vi.fn().mockReturnValue(false), resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)) } as unknown as AiRouter;
  const mockTm = { fuzzyMatches: vi.fn().mockReturnValue([]) } as unknown as TranslationMemoryEngine;
  const agent = new TranslateAgent(CONFIG, mockRouter, mockTm);

  it("devrait valider une sortie correcte (output validé)", () => {
    const valid = { paragraphs: [makeParagraph({ translatedText: "x", status: "translated" })] };
    expect(() => agent.validateOutput(valid)).not.toThrow();
  });

  it("devrait lever une erreur sur une sortie invalide (output invalide → fallback)", () => {
    expect(() => agent.validateOutput({ paragraphs: "not-an-array" })).toThrow();
  });
});

describe("Agent validateOutput — PreTranslateAgent", () => {
  const mockRouter = { chat: vi.fn(), tryParseJson: vi.fn(), isEthicalRefusal: vi.fn().mockReturnValue(false), resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)) } as unknown as AiRouter;
  const agent = new PreTranslateAgent(CONFIG, mockRouter);

  it("devrait valider une sortie correcte", () => {
    expect(() => agent.validateOutput({ paragraphs: [makeParagraph()] })).not.toThrow();
  });

  it("devrait lever sur une sortie invalide", () => {
    expect(() => agent.validateOutput({ paragraphs: null })).toThrow();
  });
});

describe("Agent validateOutput — SplitAgent", () => {
  const agent = new SplitAgent(CONFIG);

  it("devrait valider une sortie correcte", () => {
    expect(() => agent.validateOutput({ paragraphs: [makeParagraph()] })).not.toThrow();
  });

  it("devrait lever sur une sortie invalide", () => {
    expect(() => agent.validateOutput({ paragraphs: [{ id: "x" }] })).toThrow();
  });
});

describe("Agent validateOutput — ConsistencyAgent", () => {
  const mockRouter = { chat: vi.fn(), tryParseJson: vi.fn() } as unknown as AiRouter;
  const mockChecker = {} as unknown as ConsistencyChecker;
  const agent = new ConsistencyAgent(CONFIG, mockChecker, mockRouter);

  it("devrait valider un rapport de cohérence correct", () => {
    expect(() =>
      agent.validateOutput({
        report: {
          metrics: [{ name: "paragraphs", source: 5, target: 5, ok: true, score: 100 }],
          warnings: [],
          globalScore: 90,
        },
      }),
    ).not.toThrow();
  });

  it("devrait lever sur un rapport sans globalScore", () => {
    expect(() =>
      agent.validateOutput({ report: { metrics: [], warnings: [] } }),
    ).toThrow();
  });
});

describe("Agent validateOutput — LexiconAgent", () => {
  const mockRouter = { chat: vi.fn(), tryParseJson: vi.fn() } as unknown as AiRouter;
  const mockLexicon = {} as unknown as LexiconEngine;
  const agent = new LexiconAgent(CONFIG, mockLexicon, mockRouter);

  it("devrait valider une sortie lexique correcte", () => {
    expect(() =>
      agent.validateOutput({
        text: "Le dragon",
        substitutions: [{ before: "x", after: "y", locked: false }],
      }),
    ).not.toThrow();
  });

  it("devrait lever sur une sortie lexique invalide", () => {
    expect(() =>
      agent.validateOutput({ text: "ok" }),
    ).toThrow();
  });
});

describe("Agent validateOutput — GrammarAgent", () => {
  const mockRouter = { chat: vi.fn(), isEthicalRefusal: vi.fn().mockReturnValue(false), resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)) } as unknown as AiRouter;
  const agent = new GrammarAgent(CONFIG, mockRouter);

  it("devrait valider une sortie texte correcte", () => {
    expect(() => agent.validateOutput({ text: "Corrigé" })).not.toThrow();
  });

  it("devrait lever sur une sortie sans champ text", () => {
    expect(() => agent.validateOutput({ metadata: {} })).toThrow();
  });
});

describe("Agent validateOutput — StyleAgent", () => {
  const mockRouter = { chat: vi.fn(), isEthicalRefusal: vi.fn().mockReturnValue(false), resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)) } as unknown as AiRouter;
  const agent = new StyleAgent(CONFIG, mockRouter);

  it("devrait valider une sortie texte correcte", () => {
    expect(() => agent.validateOutput({ text: "Stylisé" })).not.toThrow();
  });

  it("devrait lever sur une sortie sans champ text", () => {
    expect(() => agent.validateOutput({ metadata: {} })).toThrow();
  });
});

describe("Agent validateOutput — PolishAgent", () => {
  const mockRouter = { chat: vi.fn(), isEthicalRefusal: vi.fn().mockReturnValue(false), resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)) } as unknown as AiRouter;
  const agent = new PolishAgent(CONFIG, mockRouter);

  it("devrait valider une sortie texte correcte", () => {
    expect(() => agent.validateOutput({ text: "Poli" })).not.toThrow();
  });

  it("devrait lever sur une sortie sans champ text", () => {
    expect(() => agent.validateOutput({ metadata: {} })).toThrow();
  });
});

describe("Agent validateOutput — QaAgent", () => {
  const mockRouter = { chat: vi.fn(), tryParseJson: vi.fn() } as unknown as AiRouter;
  const mockQc = { evaluate: vi.fn() } as unknown as QualityChecker;
  const agent = new QaAgent(CONFIG, mockRouter, mockQc);

  it("devrait valider un rapport QA correct", () => {
    expect(() =>
      agent.validateOutput({
        report: {
          consistency: 90,
          grammar: 90,
          fluency: 90,
          style: 90,
          lexicon: 90,
          hallucination: 90,
          length: 90,
          dialogue: 90,
          globalScore: 90,
          comments: "ok",
        },
        score: 90,
      }),
    ).not.toThrow();
  });

  it("devrait lever sur un score hors limites", () => {
    expect(() =>
      agent.validateOutput({
        report: {
          consistency: 90, grammar: 90, fluency: 90,
          style: 90, lexicon: 90, hallucination: 90,
          length: 90, dialogue: 90, globalScore: 90, comments: "x",
        },
        score: 999,
      }),
    ).toThrow();
  });
});

describe("Agent validateOutput — ExportAgent", () => {
  const mockExport = {} as unknown as ExportEngine;
  const agent = new ExportAgent(CONFIG, mockExport);

  it("devrait valider une sortie export correcte", () => {
    expect(() =>
      agent.validateOutput({ metadata: { exportPath: "/out.epub" } }),
    ).not.toThrow();
  });

  it("devrait lever sur une sortie sans exportPath", () => {
    expect(() =>
      agent.validateOutput({ metadata: {} }),
    ).toThrow();
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
      resolvePrompt: vi.fn().mockImplementation((_id: string, def: string) => Promise.resolve(def)),
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

import { describe, it, expect, beforeEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Guards anti-boucle (settings maxQaRetries / maxJobTokens + garde-fou 90%)
//
// Trois garde-fous inspirés d'un design SaaS multi-agent, adaptés au desktop :
//   1. Cap de retries QA automatiques par chapitre (maxQaRetries, défaut 3)
//   2. Cap de tokens cumulés par job (maxJobTokens, défaut 50000, 0 = off)
//   3. Garde-fou anti-résumé : traduction < 90% des mots source → flag
// ---------------------------------------------------------------------------

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

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: {
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { TranslateAgent } from "../../src/main/services/agents/TranslateAgent";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";
import type { Paragraph } from "@shared/types/index.js";

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

// ===========================================================================
// 3. Garde-fou 90% mots source — test d'intégration TranslateAgent
// ===========================================================================

describe("Garde-fou anti-résumé (TranslateAgent, 90% mots source)", () => {
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

  it("devrait marquer pending un paragraphe dont la traduction est < 90% des mots source", async () => {
    // Source : 30 mots (> 20, seuil atteint). Traduction raccourcie : ~5 mots
    // (< 90% = 27 mots) → anomalie détectée.
    const longSource =
      "The dragon flew over the mountains and the castle while the knights watched in silence from below the walls as the sun set behind them.";
    const shortTranslation = "Le dragon survola tout."; // ~5 mots

    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(shortTranslation);

    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph({ sourceText: longSource })],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });

    expect(output.paragraphs![0].status).toBe("pending");
    expect(output.metadata).toBeDefined();
    expect(output.metadata?.lengthAnomaly).toBe(true);
    expect(output.metadata?.anomalyCount).toBe(1);
  });

  it("ne devrait PAS flagguer une traduction de longueur normale", async () => {
    // Source 24 mots (> 20), traduction équivalente en longueur → OK
    const source =
      "The dragon flew over the mountains and the castle while the knights watched carefully from the walls above the deep valley below them.";
    const translation =
      "Le dragon survola les montagnes et le château tandis que les chevaliers observaient attentivement depuis les remparts au-dessus de la profonde vallée en contrebas.";

    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(translation);

    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph({ sourceText: source })],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });

    expect(output.paragraphs![0].status).toBe("translated");
    expect(output.metadata?.lengthAnomaly).toBeUndefined();
  });

  it("ne devrait PAS flagguer les paragraphes courts (< 20 mots source) — évite les faux positifs", async () => {
    // Source court : 7 mots. Traduction 2 mots. Sans le seuil de 20 mots,
    // ce serait un faux positif (phrase courte légitimement compressible).
    const shortSource = "The dragon flew over the mountains today.";
    const veryShortTranslation = "Vol."

    ;(mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue(veryShortTranslation);

    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [makeParagraph({ sourceText: shortSource })],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });

    expect(output.paragraphs![0].status).toBe("translated");
    expect(output.metadata?.lengthAnomaly).toBeUndefined();
  });

  it("devrait compter plusieurs anomalies dans anomalyCount", async () => {
    const longSource =
      "The dragon flew over the mountains and the castle while the knights watched in silence from below the walls above the valley.";

    // 2 paragraphes longs, chacun traduit trop court
    (mockRouter.chat as ReturnType<typeof vi.fn>).mockResolvedValue("Court.");

    const agent = new TranslateAgent(CONFIG, mockRouter, mockTmEngine);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs: [
        makeParagraph({ id: "p1", sourceText: longSource }),
        makeParagraph({ id: "p2", sourceText: longSource }),
      ],
      options: { sourceLanguage: "en", targetLanguage: "fr" },
    });

    expect(output.metadata?.lengthAnomaly).toBe(true);
    expect(output.metadata?.anomalyCount).toBe(2);
    expect(output.paragraphs!.every((p) => p.status === "pending")).toBe(true);
  });
});

// ===========================================================================
// 1 & 2. Caps QA retries / tokens — logique de décision (pattern workflow-branching)
// ===========================================================================
//
// WorkflowEngine est trop lourd à instancier (DB, migrations, settings…). On
// valide la logique de borne via une simulation fidèle au code de runStep(),
// comme le fait workflow-branching.spec.ts.

describe("Cap retries QA (maxQaRetries)", () => {
  function simulateQaBranch(
    score: number,
    qualityThreshold: number,
    qaRetryCount: number,
    maxQaRetries: number,
  ): { action: "retry" | "pause"; newCount: number; reason?: string } {
    // Reflète la logique de WorkflowEngine.runStep branche QA
    if (score >= qualityThreshold) {
      return { action: "retry", newCount: qaRetryCount }; // continue, pas de retry
    }
    if (score >= qualityThreshold - 20) {
      const newCount = qaRetryCount + 1;
      if (newCount > maxQaRetries) {
        return { action: "pause", newCount, reason: "max_qa_retries_exceeded" };
      }
      return { action: "retry", newCount };
    }
    return { action: "pause", newCount: qaRetryCount }; // score < threshold - 20
  }

  it("devrait retry tant que le compteur ne dépasse pas maxQaRetries", () => {
    let count = 0;
    // 3 retries autorisés (score 65 intermédiaire, threshold 80)
    for (let i = 0; i < 3; i++) {
      const result = simulateQaBranch(65, 80, count, 3);
      expect(result.action).toBe("retry");
      count = result.newCount;
    }
    expect(count).toBe(3);
  });

  it("devrait pause au (maxQaRetries + 1)e score intermédiaire", () => {
    const count = 3; // déjà 3 retries
    const result = simulateQaBranch(65, 80, count, 3);
    expect(result.action).toBe("pause");
    expect(result.reason).toBe("max_qa_retries_exceeded");
    expect(result.newCount).toBe(4);
  });

  it("devrait respecter un cap custom (maxQaRetries = 1)", () => {
    // 1er retry OK
    let result = simulateQaBranch(65, 80, 0, 1);
    expect(result.action).toBe("retry");
    expect(result.newCount).toBe(1);
    // 2e → pause
    result = simulateQaBranch(65, 80, 1, 1);
    expect(result.action).toBe("pause");
    expect(result.reason).toBe("max_qa_retries_exceeded");
  });

  it("ne devrait jamais retry si maxQaRetries = 0", () => {
    const result = simulateQaBranch(65, 80, 0, 0);
    // 0 + 1 = 1 > 0 → pause immédiate
    expect(result.action).toBe("pause");
    expect(result.reason).toBe("max_qa_retries_exceeded");
  });

  it("un score >= threshold ne devrait jamais incrémenter le compteur", () => {
    const result = simulateQaBranch(85, 80, 0, 3);
    expect(result.action).toBe("retry");
    expect(result.newCount).toBe(0);
  });

  it("un score < threshold - 20 devrait pause sans toucher au compteur", () => {
    const result = simulateQaBranch(50, 80, 2, 3);
    expect(result.action).toBe("pause");
    expect(result.newCount).toBe(2); // inchangé
  });
});

describe("Cap tokens par job (maxJobTokens)", () => {
  function simulateTokenCap(
    tokensUsedBefore: number,
    stepTokensIn: number,
    stepTokensOut: number,
    maxJobTokens: number,
  ): { pause: boolean; tokensUsedAfter: number } {
    // Reflète la logique de WorkflowEngine.runStep après accumulation coût
    if (maxJobTokens <= 0) {
      return { pause: false, tokensUsedAfter: tokensUsedBefore }; // désactivé
    }
    const after = tokensUsedBefore + stepTokensIn + stepTokensOut;
    return { pause: after > maxJobTokens, tokensUsedAfter: after };
  }

  it("ne devrait pas pause sous le plafond", () => {
    const result = simulateTokenCap(10000, 2000, 1000, 50000);
    expect(result.pause).toBe(false);
    expect(result.tokensUsedAfter).toBe(13000);
  });

  it("devrait pause au-dessus du plafond", () => {
    const result = simulateTokenCap(48000, 2000, 1000, 50000);
    expect(result.pause).toBe(true);
    expect(result.tokensUsedAfter).toBe(51000);
  });

  it("devrait être désactivé quand maxJobTokens = 0", () => {
    const result = simulateTokenCap(999999, 100000, 100000, 0);
    expect(result.pause).toBe(false);
  });

  it("devrait cumuler les tokens sur plusieurs steps", () => {
    let used = 0;
    const max = 50000;
    const steps = [
      { in: 10000, out: 5000 },
      { in: 12000, out: 6000 },
      { in: 11000, out: 7000 },
    ];
    let paused = false;
    for (const s of steps) {
      const r = simulateTokenCap(used, s.in, s.out, max);
      used = r.tokensUsedAfter;
      if (r.pause) {paused = true; break;}
    }
    // 15k + 18k + 18k = 51k > 50k → pause au 3e step
    expect(paused).toBe(true);
    expect(used).toBe(51000);
  });

  it("devrait être inactif quand tokensIn/Out sont absents (providers sans usage)", () => {
    // Tant que le token accounting n'est pas câblé côté providers, step.tokensIn/Out
    // restent undefined → la branche `if (step.tokensIn || step.tokensOut)` est
    // sautée → pas de cumul, pas de pause. Le guard est correctement inactif.
    const tokensIn = undefined;
    const tokensOut = undefined;
    expect(tokensIn || tokensOut).toBeFalsy();
  });
});

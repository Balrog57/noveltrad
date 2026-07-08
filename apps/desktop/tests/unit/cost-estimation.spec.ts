import { describe, it, expect, beforeEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// G3 : Cost estimation (SDD §3.8)
//
// AiRouter.estimateCost() calcule le coût USD d'un appel basé sur les
// modelCosts configurés (par model id). Les modèles locaux (Ollama) ne sont
// pas dans la map → coût 0.
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

import { AiRouter } from "../../src/main/services/AiRouter";

describe("Cost estimation (SDD §3.8, G3)", () => {
  let router: AiRouter;

  beforeEach(() => {
    router = new AiRouter();
  });

  it("devrait calculer le coût correct pour un modèle configuré", () => {
    router.setModelCosts({
      "gpt-4": {
        costPerInputToken: 0.03, // $0.03 per 1K input tokens
        costPerOutputToken: 0.06, // $0.06 per 1K output tokens
      },
    });

    // 1000 input + 500 output = 0.03 + 0.03 = 0.06 USD
    const cost = router.estimateCost("gpt-4", 1000, 500);
    expect(cost).toBeCloseTo(0.06, 6);
  });

  it("devrait retourner 0 pour un modèle non configuré (local/Ollama)", () => {
    router.setModelCosts({});

    const cost = router.estimateCost("qwen3.5:9b", 5000, 2000);
    expect(cost).toBe(0);
  });

  it("devrait retourner 0 si aucun modelCosts n'est configuré", () => {
    // router sans setModelCosts → modelCosts vide par défaut
    const cost = router.estimateCost("any-model", 1000, 1000);
    expect(cost).toBe(0);
  });

  it("devrait accumuler le coût sur plusieurs appels (simulation job)", () => {
    router.setModelCosts({
      "gpt-4": {
        costPerInputToken: 0.03,
        costPerOutputToken: 0.06,
      },
    });

    // Simulation de 3 étapes de job
    let jobCost = 0;
    jobCost += router.estimateCost("gpt-4", 1000, 500); // 0.06
    jobCost += router.estimateCost("gpt-4", 2000, 1000); // 0.06 + 0.06 = 0.12
    jobCost += router.estimateCost("gpt-4", 500, 250); // 0.015 + 0.015 = 0.03

    // Total = 0.06 + 0.12 + 0.03 = 0.21
    expect(jobCost).toBeCloseTo(0.21, 6);
  });
});

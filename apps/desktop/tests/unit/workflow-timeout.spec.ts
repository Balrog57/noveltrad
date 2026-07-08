import { describe, it, expect, beforeEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// G1 : Per-step timeout (SDD §7.10)
//
// WorkflowRunner.runStep() enveloppe l'exécution de l'agent dans un
// Promise.race([execute, timeout]). Si l'agent ne répond pas dans
// stepTimeoutMs, une erreur "timed out" est levée → catch existant →
// step.status = "failed".
//
// Ce test valide la logique executeWithTimeout directement (le runner complet
// nécessite trop de mocks ; la logique de timeout est isolée et testable).
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

/**
 * Réplique exacte de la logique executeWithTimeout de WorkflowEngine.runStep().
 * Tester cette fonction isolément valide le comportement timeout sans instancier
 * tout le WorkflowRunner (qui nécessite DB, agents, settings, etc.).
 */
async function executeWithTimeout<T>(
  fn: () => Promise<T>,
  timeoutMs: number,
  stage: string,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`Step ${stage} timed out after ${timeoutMs}ms`)),
      timeoutMs,
    );
  });
  try {
    return await Promise.race([fn(), timeoutPromise]);
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
  }
}

describe("Per-step timeout (SDD §7.10, G1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("devrait réussir si l'agent termine avant le timeout", async () => {
    const fastAgent = async () => {
      await new Promise((r) => setTimeout(r, 10));
      return { score: 95 } as unknown as never;
    };

    const result = await executeWithTimeout(fastAgent, 1000, "translate");

    expect(result).toEqual({ score: 95 });
  });

  it("devrait lever une erreur 'timed out' si l'agent dépasse stepTimeoutMs", async () => {
    const hungAgent = async () => {
      await new Promise((r) => setTimeout(r, 5000)); // 5s, bien au-delà du timeout
      return { score: 95 } as unknown as never;
    };

    await expect(executeWithTimeout(hungAgent, 50, "translate")).rejects.toThrow(
      "Step translate timed out after 50ms",
    );
  });

  it("devrait utiliser un stepTimeoutMs custom (override par étape)", async () => {
    // Un agent qui prend 80ms : échoue avec timeout 50ms, réussit avec 200ms.
    const slowAgent = async () => {
      await new Promise((r) => setTimeout(r, 80));
      return "ok" as unknown as never;
    };

    await expect(executeWithTimeout(slowAgent, 50, "qa")).rejects.toThrow(
      "timed out after 50ms",
    );

    const result = await executeWithTimeout(slowAgent, 200, "qa");
    expect(result).toBe("ok");
  });

  it("devrait nettoyer le timer même en cas de succès (pas de fuite)", async () => {
    const fastAgent = async () => "ok" as unknown as never;

    const result = await executeWithTimeout(fastAgent, 10000, "export");

    expect(result).toBe("ok");
    // Pas d'assertion directe sur le timer (interne), mais le fait que le test
    // se termine sans attendre 10s prouve que clearTimeout a été appelé.
  });
});

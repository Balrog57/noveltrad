import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
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

// ---------------------------------------------------------------------------
// Tests — Concurrency gate (SDD §7.4)
// ---------------------------------------------------------------------------

describe("Workflow concurrency gate (SDD §7.4)", () => {
  let PQueue: any;
  let queueInstance: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    // Import real PQueue for testing
    const pQueueModule = await import("p-queue");
    PQueue = pQueueModule.default;
  });

  it("devrait lancer le job si sous la limite de concurrence", async () => {
    const queue = new PQueue({ concurrency: 2 });
    let executed = false;

    const result = await queue.add(async () => {
      executed = true;
      return "ok";
    });

    expect(result).toBe("ok");
    expect(executed).toBe(true);
    expect(queue.size).toBe(0);
    expect(queue.pending).toBe(0);
  });

  it("devrait mettre en file d'attente si la limite est atteinte", async () => {
    const queue = new PQueue({ concurrency: 1 });
    let order: string[] = [];
    let resolveFirst: () => void;

    const firstPromise = new Promise<void>((resolve) => { resolveFirst = resolve; });

    // Premier job qui bloque
    const first = queue.add(async () => {
      order.push("first-started");
      await firstPromise!;
      order.push("first-completed");
    });

    // Deuxième job (devrait être en file d'attente)
    const second = queue.add(async () => {
      order.push("second-started");
    });

    // Le premier a démarré, le second est en attente
    expect(queue.size).toBe(1); // un dans la file
    expect(queue.pending).toBe(1); // un en cours

    // Libérer le premier
    resolveFirst!();
    await first;
    await second;

    expect(order).toEqual(["first-started", "first-completed", "second-started"]);
    expect(queue.size).toBe(0);
  });

  it("devrait libérer et lancer le suivant quand un job se termine", async () => {
    const queue = new PQueue({ concurrency: 1 });
    const executionOrder: number[] = [];

    const jobs = [1, 2, 3].map((id) =>
      queue.add(async () => {
        executionOrder.push(id);
      }),
    );

    await Promise.all(jobs);

    // Les jobs doivent s'exécuter dans l'ordre (séquentiel car concurrency=1)
    expect(executionOrder).toEqual([1, 2, 3]);
  });
});

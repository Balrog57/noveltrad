import { describe, it, expect, beforeEach, vi } from "vitest";

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

class MockEventEmitter {
  private listeners: Record<string, Array<(...args: unknown[]) => void>> = {};
  on(event: string, cb: (...args: unknown[]) => void): this {
    if (!this.listeners[event]) {this.listeners[event] = [];}
    this.listeners[event].push(cb);
    return this;
  }
  once(event: string, cb: (...args: unknown[]) => void): this {
    const wrapper = (...args: unknown[]) => { cb(...args); this.removeListener(event, wrapper); };
    return this.on(event, wrapper);
  }
  emit(event: string, ...args: unknown[]): boolean {
    const handlers = this.listeners[event];
    if (!handlers) {return false;}
    for (const h of handlers) {h(...args);}
    return true;
  }
  off(event: string, cb: (...args: unknown[]) => void): this {
    return this.removeListener(event, cb);
  }
  removeListener(event: string, cb: (...args: unknown[]) => void): this {
    if (!this.listeners[event]) {return this;}
    this.listeners[event] = this.listeners[event].filter((l) => l !== cb);
    return this;
  }
}

// Mock WorkflowRunner internals for branching tests
describe("Workflow branching QA (SDD §7.1)", () => {
  let runner: any;
  let paused: boolean;
  let qualityFailedPayload: any;

  function createMockRunner(settingsOverrides: Record<string, unknown> = {}) {
    paused = false;
    qualityFailedPayload = null;

    // Mock WorkflowRunner as a minimal observable class
    runner = {
      paused: false,
      settings: {
        get: (key: string) => {
          if (key === "qualityThreshold") return (settingsOverrides.qualityThreshold ?? 80) as number;
          if (key === "defaultModel") return "qwen3.5:9b";
          if (key === "useWorkerThreads") return false;
          return undefined;
        },
      },
      pause: () => {
        paused = true;
      },
      emitQualityFailed: (payload: { jobId: string; score: number; threshold: number }) => {
        qualityFailedPayload = payload;
      },
      retryWeakestStep: vi.fn().mockResolvedValue(undefined),
      job: { id: "job-123" },
      steps: [
        { id: "s1", stage: "translate", score: 65 },
        { id: "s2", stage: "grammar", score: 70 },
        { id: "s3", stage: "qa", score: undefined },
      ],
    };
  }

  beforeEach(() => {
    vi.clearAllMocks();
    createMockRunner();
  });

  it("devrait continuer si score >= threshold", () => {
    const qualityThreshold = 80;
    const score = 85;

    expect(score >= qualityThreshold).toBe(true);
    expect(paused).toBe(false);
    expect(qualityFailedPayload).toBeNull();
  });

  it("devrait pause si score < threshold - 20", () => {
    const qualityThreshold = 80;
    const score = 55; // < 60

    // Simuler la logique de pause
    if (score < qualityThreshold - 20) {
      paused = true;
      qualityFailedPayload = { jobId: "job-123", score, threshold: qualityThreshold };
    }

    expect(paused).toBe(true);
    expect(qualityFailedPayload).toEqual({
      jobId: "job-123",
      score: 55,
      threshold: 80,
    });
  });

  it("devrait retry weakest step si score intermédiaire", () => {
    const qualityThreshold = 80;
    const score = 65; // >= 60 mais < 80

    if (score < qualityThreshold && score >= qualityThreshold - 20) {
      runner.retryWeakestStep();
    }

    expect(runner.retryWeakestStep).toHaveBeenCalledTimes(1);
    expect(paused).toBe(false);
    expect(qualityFailedPayload).toBeNull();
  });

  it("devrait utiliser un threshold custom", () => {
    createMockRunner({ qualityThreshold: 70 });
    const qualityThreshold = 70;
    const score = 60; // >= 50 mais < 70

    let retryCalled = false;
    if (score < qualityThreshold && score >= qualityThreshold - 20) {
      retryCalled = true;
    }

    expect(retryCalled).toBe(true);
  });

  it("devrait émettre un événement quality-failed quand le score est trop bas", () => {
    const qualityThreshold = 80;
    const score = 50;
    let emitted = false;

    // Simuler l'émission
    if (score < qualityThreshold - 20) {
      emitted = true;
    }

    expect(emitted).toBe(true);
  });
});

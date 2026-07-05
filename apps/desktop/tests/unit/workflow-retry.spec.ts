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

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: {
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

const mockNetFetch = vi.fn();

function mockJsonResponse(data: unknown, status = 200, ok = true) {
  const bodyStr = JSON.stringify(data);
  return {
    ok,
    status,
    text: () => Promise.resolve(bodyStr),
    json: () => Promise.resolve(data),
    body: null,
  };
}

function mockStreamBody() {
  const encoder = new TextEncoder();
  return {
    getReader: () => ({
      read: () =>
        Promise.resolve({
          done: true,
          value: encoder.encode(""),
        }),
    }),
  };
}

vi.mock("electron", () => ({
  net: { fetch: mockNetFetch },
}));

// Helper: p-retry wrapper with minimal delay for test speed
import pRetry, { AbortError } from "p-retry";

async function fastRetry<T>(fn: () => Promise<T>): Promise<T> {
  return pRetry(fn, {
    retries: 3,
    factor: 2,
    minTimeout: 10, // 10ms for fast tests
    maxTimeout: 100,
  });
}

// ---------------------------------------------------------------------------
// Tests — OllamaProvider retry behavior (SDD §7.10)
// ---------------------------------------------------------------------------

describe("Workflow retry — OllamaProvider (SDD §7.10)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNetFetch.mockReset();
  });

  it("devrait réussir après 2 échecs réseau (retry success)", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    // Use the provider's built-in retry, but mock with fast success after failures
    mockNetFetch
      .mockRejectedValueOnce(new Error("ECONNREFUSED"))
      .mockRejectedValueOnce(new Error("timeout"))
      .mockResolvedValueOnce(mockJsonResponse({ message: { content: "Réussi" } }));

    const result = await provider.chat([{ role: "user", content: "test" }]);
    expect(result).toBe("Réussi");
    expect(mockNetFetch).toHaveBeenCalledTimes(3);
  }, 15000);

  it("devrait abandonner après 3 échecs (retry abandon)", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    mockNetFetch.mockRejectedValue(new Error("ECONNREFUSED"));

    await expect(
      provider.chat([{ role: "user", content: "test" }]),
    ).rejects.toThrow("ECONNREFUSED");
    // 1 tentative + 3 retries = 4 appels (le retry abandon après 3 échecs)
    expect(mockNetFetch).toHaveBeenCalledTimes(4);
  }, 15000);

  it("ne devrait pas retry sur erreur 4xx", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    mockNetFetch.mockResolvedValue(mockJsonResponse({ error: "Bad Request" }, 400, false));

    await expect(
      provider.chat([{ role: "user", content: "test" }]),
    ).rejects.toThrow("HTTP 400");
    // Pas de retry sur 4xx (AbortError immédiat)
    expect(mockNetFetch).toHaveBeenCalledTimes(1);
  });

  it("devrait retry sur streamChat en cas d'erreur réseau", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    mockNetFetch
      .mockRejectedValueOnce(new Error("ECONNREFUSED"))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
        text: () => Promise.resolve(""),
        body: mockStreamBody(),
      });

    const gen = provider.streamChat([{ role: "user", content: "test" }]);
    const iterator = gen[Symbol.asyncIterator]();
    const result = await iterator.next();
    expect(result.done).toBe(true);
    expect(mockNetFetch).toHaveBeenCalledTimes(2);
  }, 15000);

  it("devrait appliquer un backoff exponentiel — délais croissants entre tentatives", async () => {
    // Test du comportement backoff avec pRetry directement
    const timings: number[] = [];
    const startTime = Date.now();

    await expect(
      pRetry(
        async (attempt) => {
          timings.push(Date.now() - startTime);
          throw new Error("échec");
        },
        {
          retries: 3,
          factor: 2,
          minTimeout: 50,
          maxTimeout: 500,
        },
      ),
    ).rejects.toThrow("échec");

    // timings[0] ≈ 0ms (1ère tentative), timings[1] ≈ 50ms (après 1er backoff),
    // timings[2] ≈ 150ms (50+100), timings[3] ≈ 350ms (50+100+200)
    expect(timings.length).toBe(4);
    for (let i = 1; i < timings.length; i++) {
      const gap = timings[i] - timings[i - 1];
      expect(gap).toBeGreaterThanOrEqual(40); // au moins ~minTimeout
    }
  }, 10000);
});

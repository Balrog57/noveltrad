import { describe, it, expect, beforeEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// G2 : HTTP 429 handling (SDD §3.7)
//
// OllamaProvider et OpenAiCompatibleProvider doivent traiter le 429 comme
// retryable (respecter Retry-After, lever une Error simple — PAS AbortError).
// Le pRetry de l'AiRouter va alors retryer la requête.
// ---------------------------------------------------------------------------

// vi.hoisted garantit que le mock est initialisé avant le vi.mock hissé.
const { mockNetFetch } = vi.hoisted(() => ({
  mockNetFetch: vi.fn(),
}));

function mockResponse(opts: {
  status: number;
  ok?: boolean;
  body?: unknown;
  headers?: Record<string, string>;
}) {
  const bodyStr = JSON.stringify(opts.body ?? {});
  const h = new Map<string, string>();
  if (opts.headers) {
    for (const [k, v] of Object.entries(opts.headers)) {
      h.set(k.toLowerCase(), v);
    }
  }
  return {
    ok: opts.ok ?? opts.status === 200,
    status: opts.status,
    text: () => Promise.resolve(bodyStr),
    json: () => Promise.resolve(opts.body ?? {}),
    body: null,
    headers: {
      get: (name: string) => h.get(name.toLowerCase()) ?? null,
    },
  };
}

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: {
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

vi.mock("electron", () => ({
  net: { fetch: mockNetFetch },
}));

import { OllamaProvider } from "../../src/main/services/providers/OllamaProvider";
import { AiRouter } from "../../src/main/services/AiRouter";

describe("HTTP 429 handling (SDD §3.7, G2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("OllamaProvider: 429 avec Retry-After → sleep puis retry (succès 2e tentative)", async () => {
    let callCount = 0;
    mockNetFetch.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) {
        return mockResponse({
          status: 429,
          headers: { "Retry-After": "1" },
        });
      }
      return mockResponse({
        status: 200,
        body: { message: { content: "ok" } },
      });
    });

    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const router = new AiRouter();
    router.register(provider);

    const result = await router.chat("ollama", [
      { role: "user", content: "test" },
    ]);

    expect(result).toBe("ok");
    expect(callCount).toBe(2); // 1er = 429, 2e = succès
  }, 15000);

  it("OllamaProvider: 429 sans Retry-After → retry avec backoff par défaut", async () => {
    let callCount = 0;
    mockNetFetch.mockImplementation(async () => {
      callCount++;
      if (callCount <= 2) {
        return mockResponse({ status: 429 });
      }
      return mockResponse({
        status: 200,
        body: { message: { content: "ok" } },
      });
    });

    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const router = new AiRouter();
    router.register(provider);

    const result = await router.chat("ollama", [
      { role: "user", content: "test" },
    ]);

    expect(result).toBe("ok");
    expect(callCount).toBe(3); // 2× 429 + 1× succès
  }, 30000);

  it("OllamaProvider: 429 persistant → échec après épuisement des retries", async () => {
    mockNetFetch.mockResolvedValue(mockResponse({ status: 429 }));

    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const router = new AiRouter();
    router.register(provider);

    await expect(
      router.chat("ollama", [{ role: "user", content: "test" }]),
    ).rejects.toThrow("429");

    // 1 tentative + 3 retries = 4 appels
    expect(mockNetFetch).toHaveBeenCalledTimes(4);
  }, 30000);

  it("OllamaProvider: 4xx autre que 429 (ex 400) → pas de retry (AbortError)", async () => {
    mockNetFetch.mockResolvedValue(mockResponse({ status: 400 }));

    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const router = new AiRouter();
    router.register(provider);

    await expect(
      router.chat("ollama", [{ role: "user", content: "test" }]),
    ).rejects.toThrow("HTTP 400");

    // Un seul appel — 4xx non-429 est AbortError, pas de retry
    expect(mockNetFetch).toHaveBeenCalledTimes(1);
  }, 15000);
});

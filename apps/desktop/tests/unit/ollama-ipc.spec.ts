/**
 * Tests d'intégration IPC — Handlers Ollama (Phase 0 validation)
 *
 * Valide les 4 handlers Ollama : is-available, list-models, pull-model, test-model.
 * Vérifie : réponse correcte, propagation erreurs, logs, temps de réponse.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const { mockNetFetch, mockIpcMainHandle, mockLogger } = vi.hoisted(() => ({
  mockNetFetch: vi.fn(),
  mockIpcMainHandle: vi.fn(),
  mockLogger: { error: vi.fn(), info: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

vi.mock("electron", () => ({
  ipcMain: { handle: mockIpcMainHandle },
  net: { fetch: mockNetFetch },
}));

vi.mock("../../src/main/managers/SettingsManager.js", () => ({
  SettingsManager: vi.fn().mockImplementation(() => ({
    get: vi.fn((key: string) => {
      if (key === "ollamaHost") {return "http://localhost:11434";}
      if (key === "defaultModel") {return "qwen3.5:9b";}
      return "";
    }),
  })),
}));

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: mockLogger,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function mockStreamResponse(chunks: string[]) {
  let i = 0;
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(chunks.join("")),
    json: () => Promise.reject(new Error("Not JSON")),
    body: {
      getReader: () => ({
        read: () => {
          if (i < chunks.length) {
            const encoder = new TextEncoder();
            return Promise.resolve({
              done: false,
              value: encoder.encode(chunks[i++]),
            });
          }
          return Promise.resolve({ done: true, value: undefined });
        },
      }),
    },
  };
}

function mockErrorResponse(status = 500) {
  return {
    ok: false,
    status,
    text: () => Promise.resolve("Internal Server Error"),
    json: () => Promise.reject(new Error("Not JSON")),
    body: null,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("IPC handlers — Ollama (Phase 0 validation)", () => {
  const handlers = new Map<string, (...args: unknown[]) => Promise<unknown>>();

  beforeEach(async () => {
    vi.clearAllMocks();
    mockNetFetch.mockReset();
    handlers.clear();

    // Capture handlers registered via ipcMain.handle
    mockIpcMainHandle.mockImplementation((channel: string, fn: (...args: unknown[]) => Promise<unknown>) => {
      handlers.set(channel, fn);
    });

    const { registerOllamaHandlers } = await import(
      "../../src/main/ipc/handlers/ollama.js"
    );
    registerOllamaHandlers();
  });

  // ── ollama:is-available ──────────────────────────────────────────

  describe("ollama:is-available", () => {
    it("enregistre le handler", () => {
      expect(handlers.has("ollama:is-available")).toBe(true);
    });

    it("retourne true quand Ollama est disponible", async () => {
      mockNetFetch.mockResolvedValue(mockJsonResponse({ models: [] }));
      const result = await handlers.get("ollama:is-available")!({}, undefined);
      expect(result).toBe(true);
    });

    it("retourne false quand Ollama est indisponible", async () => {
      mockNetFetch.mockRejectedValue(new Error("Connection refused"));
      const result = await handlers.get("ollama:is-available")!({}, undefined);
      expect(result).toBe(false);
    });

    it("retourne false sur erreur HTTP 500", async () => {
      mockNetFetch.mockResolvedValue(mockErrorResponse(500));
      const result = await handlers.get("ollama:is-available")!({}, undefined);
      expect(result).toBe(false);
    });

    it("ne lance pas d'exception non capturée", async () => {
      mockNetFetch.mockRejectedValue(new Error("Unexpected"));
      await expect(
        handlers.get("ollama:is-available")!({}, undefined),
      ).resolves.toBeDefined();
    });

    it("mesure le temps de réponse (< 5s)", async () => {
      mockNetFetch.mockResolvedValue(mockJsonResponse({ models: [] }));
      const start = performance.now();
      await handlers.get("ollama:is-available")!({}, undefined);
      const elapsed = performance.now() - start;
      expect(elapsed).toBeLessThan(5000);
    });
  });

  // ── ollama:list-models ───────────────────────────────────────────

  describe("ollama:list-models", () => {
    it("enregistre le handler", () => {
      expect(handlers.has("ollama:list-models")).toBe(true);
    });

    it("retourne la liste des modèles", async () => {
      mockNetFetch.mockResolvedValue(
        mockJsonResponse({
          models: [{ name: "qwen3.5:9b", size: 5_000_000_000 }],
        }),
      );
      const result = await handlers.get("ollama:list-models")!({}, undefined);
      expect(Array.isArray(result)).toBe(true);
      expect(result).toHaveLength(1);
      expect((result as Array<{ name: string }>)[0].name).toBe("qwen3.5:9b");
    });

    it("propage l'erreur si Ollama est indisponible", async () => {
      mockNetFetch.mockRejectedValue(new Error("Connection refused"));
      await expect(
        handlers.get("ollama:list-models")!({}, undefined),
      ).rejects.toThrow("Connection refused");
    });

    it("mesure le temps de réponse (< 5s)", async () => {
      mockNetFetch.mockResolvedValue(mockJsonResponse({ models: [] }));
      const start = performance.now();
      await handlers.get("ollama:list-models")!({}, undefined);
      const elapsed = performance.now() - start;
      expect(elapsed).toBeLessThan(5000);
    });
  });

  // ── ollama:pull-model ────────────────────────────────────────────

  describe("ollama:pull-model", () => {
    it("enregistre le handler", () => {
      expect(handlers.has("ollama:pull-model")).toBe(true);
    });

    it("télécharge un modèle et retourne { done: true }", async () => {
      const ndjson =
        JSON.stringify({ status: "pulling manifest" }) + "\n" +
        JSON.stringify({ completed: 100, total: 100, status: "success" }) + "\n" +
        JSON.stringify({ status: "cleanup" }) + "\n";
      mockNetFetch.mockResolvedValue(mockStreamResponse([ndjson]));

      const mockSend = vi.fn();
      const result = await handlers.get("ollama:pull-model")!(
        { sender: { send: mockSend } },
        "llama3",
      );
      expect(result).toEqual({ done: true });
    });

    it("envoie des événements ollama:pull-progress", async () => {
      const ndjson =
        JSON.stringify({ status: "pulling manifest" }) + "\n" +
        JSON.stringify({ completed: 50, total: 100, status: "downloading" }) + "\n" +
        JSON.stringify({ completed: 100, total: 100, status: "success" }) + "\n" +
        JSON.stringify({ status: "cleanup" }) + "\n";
      mockNetFetch.mockResolvedValue(mockStreamResponse([ndjson]));

      const mockSend = vi.fn();
      await handlers.get("ollama:pull-model")!(
        { sender: { send: mockSend } },
        "llama3",
      );
      expect(mockSend).toHaveBeenCalledWith("ollama:pull-progress", expect.any(Object));
    });

    it("propage l'erreur si le téléchargement échoue", async () => {
      mockNetFetch.mockRejectedValue(new Error("Model not found"));
      await expect(
        handlers.get("ollama:pull-model")!(
          { sender: { send: vi.fn() } },
          "nonexistent",
        ),
      ).rejects.toThrow("Model not found");
    });

    it("rejette un payload avec name vide (validation Zod)", async () => {
      await expect(
        handlers.get("ollama:pull-model")!(
          { sender: { send: vi.fn() } },
          "",
        ),
      ).rejects.toThrow();
    });
  });

  // ── ollama:test-model ────────────────────────────────────────────

  describe("ollama:test-model", () => {
    it("enregistre le handler", () => {
      expect(handlers.has("ollama:test-model")).toBe(true);
    });

    it("retourne { success: true, response } quand le modèle répond", async () => {
      mockNetFetch.mockResolvedValue(
        mockJsonResponse({ message: { content: "ok" } }),
      );

      const result = await handlers.get("ollama:test-model")!({}, "qwen3.5:9b");
      expect(result).toEqual({ success: true, response: "ok" });
    });

    it("retourne { success: false, error } quand le test échoue", async () => {
      mockNetFetch.mockRejectedValue(new Error("Model not loaded"));

      const result = await handlers.get("ollama:test-model")!({}, "bad-model");
      expect(result).toEqual({
        success: false,
        error: "Model not loaded",
      });
    });

    it("rejette un payload avec modelName vide (validation Zod)", async () => {
      await expect(
        handlers.get("ollama:test-model")!({}, ""),
      ).rejects.toThrow();
    });

    it("mesure le temps de réponse (< 5s)", async () => {
      mockNetFetch.mockResolvedValue(
        mockJsonResponse({ message: { content: "ok" } }),
      );
      const start = performance.now();
      await handlers.get("ollama:test-model")!({}, "qwen3.5:9b");
      const elapsed = performance.now() - start;
      expect(elapsed).toBeLessThan(5000);
    });
  });
});

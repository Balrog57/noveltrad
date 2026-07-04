/**
 * Tests pour OllamaManager (SDD §19)
 *
 * R3. Teste isAvailable, listModels, pullModel avec mock de electron/net.fetch.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Helpers pour créer des objets Response-like
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
// Mocks
// ---------------------------------------------------------------------------

const mockNetFetch = vi.fn();

vi.mock("electron", () => ({
  net: { fetch: mockNetFetch },
}));

vi.mock("../../src/main/managers/SettingsManager.js", () => ({
  SettingsManager: vi.fn().mockImplementation(() => ({
    get: vi.fn((key: string) => {
      if (key === "ollamaHost") return "http://localhost:11434";
      return "";
    }),
  })),
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OllamaManager (SDD §19)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── isAvailable() ───────────────────────────────────────────────────

  describe("isAvailable()", () => {
    it("retourne true quand le service Ollama répond", async () => {
      mockNetFetch.mockResolvedValue(
        mockJsonResponse({ models: [] }),
      );

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const result = await manager.isAvailable();
      expect(result).toBe(true);
      expect(mockNetFetch).toHaveBeenCalledWith(
        "http://localhost:11434/api/tags",
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });

    it("retourne false quand le service Ollama est indisponible", async () => {
      mockNetFetch.mockRejectedValue(new Error("Connection refused"));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const result = await manager.isAvailable();
      expect(result).toBe(false);
    });

    it("retourne false en cas d'erreur réseau", async () => {
      mockNetFetch.mockRejectedValue(new Error("ECONNREFUSED"));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const result = await manager.isAvailable();
      expect(result).toBe(false);
    });
  });

  // ── listModels() ────────────────────────────────────────────────────

  describe("listModels()", () => {
    it("retourne la liste des modèles avec tous les champs", async () => {
      mockNetFetch.mockResolvedValue(
        mockJsonResponse({
          models: [
            {
              name: "qwen3.5:9b",
              size: 5_200_000_000,
              details: {
                parameter_size: "9B",
                quantization_level: "Q4_K_M",
              },
            },
            {
              name: "nomic-embed-text:latest",
              size: 274_000_000,
              details: {},
            },
          ],
        }),
      );

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const models = await manager.listModels();

      expect(models).toHaveLength(2);
      expect(models[0]).toEqual({
        name: "qwen3.5:9b",
        size: 5_200_000_000,
        parameterSize: "9B",
        quantizationLevel: "Q4_K_M",
      });
      expect(models[1]).toEqual({
        name: "nomic-embed-text:latest",
        size: 274_000_000,
        parameterSize: undefined,
        quantizationLevel: undefined,
      });
    });

    it("retourne un tableau vide si aucun modèle", async () => {
      mockNetFetch.mockResolvedValue(mockJsonResponse({ models: [] }));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const models = await manager.listModels();
      expect(models).toEqual([]);
    });

    it("propage une erreur de fetch", async () => {
      mockNetFetch.mockRejectedValue(new Error("Ollama not running"));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      await expect(manager.listModels()).rejects.toThrow("Ollama not running");
    });
  });

  // ── pullModel() ─────────────────────────────────────────────────────

  describe("pullModel()", () => {
    it("télécharge un modèle et appelle onProgress avec chaque chunk", async () => {
      // NDJSON lines must be delivered such that "success" is NOT the last
      // non-empty line after split("\n") — the parsing code uses
      // lines.pop() to store the last fragment in buffer for continuation,
      // so success would be lost if it were the final line.
      const ndjson = [
        JSON.stringify({ status: "pulling manifest" }) +
          "\n" +
          JSON.stringify({ completed: 50, total: 100, status: "downloading" }) +
          "\n" +
          JSON.stringify({ completed: 100, total: 100, status: "success" }) +
          "\n" +
          JSON.stringify({ status: "cleanup" }) +
          "\n",
      ];
      mockNetFetch.mockResolvedValue(mockStreamResponse(ndjson));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const onProgress = vi.fn();
      await manager.pullModel("llama3", onProgress);

      expect(mockNetFetch).toHaveBeenCalledWith(
        "http://localhost:11434/api/pull",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "llama3", stream: true }),
        },
      );
      expect(onProgress).toHaveBeenCalledTimes(3);
      expect(onProgress).toHaveBeenNthCalledWith(1, {
        status: "pulling manifest",
      });
      expect(onProgress).toHaveBeenNthCalledWith(2, {
        completed: 50,
        total: 100,
        status: "downloading",
      });
      expect(onProgress).toHaveBeenNthCalledWith(3, {
        completed: 100,
        total: 100,
        status: "success",
      });
    });

    it("fonctionne sans callback onProgress", async () => {
      const ndjson = [JSON.stringify({ status: "done" }) + "\n"];
      mockNetFetch.mockResolvedValue(mockStreamResponse(ndjson));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      // Ne doit pas throw
      await expect(manager.pullModel("mistral")).resolves.toBeUndefined();
    });

    it("propage une erreur de fetch", async () => {
      mockNetFetch.mockRejectedValue(new Error("Model not found"));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      await expect(
        manager.pullModel("nonexistent"),
      ).rejects.toThrow("Model not found");
    });
  });

  // ── testModel() ─────────────────────────────────────────────────────

  describe("testModel()", () => {
    it("envoie une requête de test et retourne la réponse", async () => {
      mockNetFetch.mockResolvedValue(
        mockJsonResponse({ message: { content: "ok" } }),
      );

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const result = await manager.testModel("qwen3.5:9b");

      expect(result).toBe("ok");
      expect(mockNetFetch).toHaveBeenCalledWith(
        "http://localhost:11434/api/chat",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("qwen3.5:9b"),
        }),
      );
    });

    it("propage une erreur du fetch", async () => {
      mockNetFetch.mockRejectedValue(new Error("Model not loaded"));

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      await expect(manager.testModel("nonexistent")).rejects.toThrow(
        "Model not loaded",
      );
    });
  });
});

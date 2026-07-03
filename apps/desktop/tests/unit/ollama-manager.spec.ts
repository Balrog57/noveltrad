/**
 * Tests pour OllamaManager (SDD §19)
 *
 * R3. Teste isAvailable, listModels, pullModel avec mock du package ollama.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

/** Mock pour Ollama.list() */
const mockList = vi.fn();
/** Mock pour Ollama.chat() */
const mockChat = vi.fn();
/** Mock pour Ollama.pull() — retourne un AsyncIterable de chunks */
const mockPull = vi.fn();

vi.mock("ollama", () => ({
  Ollama: vi.fn().mockImplementation(() => ({
    list: mockList,
    chat: mockChat,
    pull: mockPull,
  })),
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
      mockList.mockResolvedValue({ models: [] });

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const result = await manager.isAvailable();
      expect(result).toBe(true);
      expect(mockList).toHaveBeenCalledTimes(1);
    });

    it("retourne false quand le service Ollama est indisponible", async () => {
      mockList.mockRejectedValue(new Error("Connection refused"));

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
      mockList.mockRejectedValue(new Error("ECONNREFUSED"));

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
      mockList.mockResolvedValue({
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
      });

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
      mockList.mockResolvedValue({ models: [] });

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

    it("propage une erreur de list()", async () => {
      mockList.mockRejectedValue(new Error("Ollama not running"));

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
      async function* fakePullStream(): AsyncIterable<{
        completed?: number;
        total?: number;
        status: string;
      }> {
        yield { status: "pulling manifest" };
        yield { completed: 50, total: 100, status: "downloading" };
        yield { completed: 100, total: 100, status: "success" };
      }
      mockPull.mockResolvedValue(fakePullStream());

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const onProgress = vi.fn();
      await manager.pullModel("llama3", onProgress);

      expect(mockPull).toHaveBeenCalledWith({
        model: "llama3",
        stream: true,
      });
      expect(onProgress).toHaveBeenCalledTimes(3);
      expect(onProgress).toHaveBeenNthCalledWith(1, { status: "pulling manifest" });
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
      async function* fakePullStream(): AsyncIterable<{
        status: string;
      }> {
        yield { status: "done" };
      }
      mockPull.mockResolvedValue(fakePullStream());

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

    it("propage une erreur de pull()", async () => {
      mockPull.mockRejectedValue(new Error("Model not found"));

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
      mockChat.mockResolvedValue({
        message: { content: "ok" },
      });

      const { OllamaManager } = await import(
        "../../src/main/managers/OllamaManager.js"
      );
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const manager = new OllamaManager(new SettingsManager());

      const result = await manager.testModel("qwen3.5:9b");

      expect(result).toBe("ok");
      expect(mockChat).toHaveBeenCalledWith({
        model: "qwen3.5:9b",
        messages: [{ role: "user", content: "Réponds uniquement par 'ok'." }],
        stream: false,
      });
    });

    it("propage une erreur du chat", async () => {
      mockChat.mockRejectedValue(new Error("Model not loaded"));

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

/**
 * Tests pour les handlers IPC (SDD §16, §19)
 *
 * R1. Teste le handler ai:stream-chat avec mock ipcMain + AiRouter.streamChat mock.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockIpcMainHandle = vi.fn();

vi.mock("electron", () => ({
  ipcMain: { handle: mockIpcMainHandle },
}));

const mockStreamChat = vi.fn();

vi.mock("../../src/main/services/AiRouter.js", () => ({
  AiRouter: vi.fn().mockImplementation(() => ({
    streamChat: mockStreamChat,
    register: vi.fn(),
  })),
}));

vi.mock("../../src/main/services/providers/OllamaProvider.js", () => ({
  OllamaProvider: vi.fn().mockImplementation(() => ({})),
}));

vi.mock("../../src/main/managers/SettingsManager.js", () => ({
  SettingsManager: vi.fn().mockImplementation(() => ({
    get: vi.fn((key: string) => {
      if (key === "defaultModel") {return "qwen3.5:9b";}
      if (key === "ollamaHost") {return "http://localhost:11434";}
      return "";
    }),
  })),
}));

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("IPC handlers — ai:stream-chat (SDD §16, §22.2)", () => {
  let handlerFn: (event: unknown, payload: unknown) => Promise<{ success: boolean }>;

  beforeEach(async () => {
    vi.clearAllMocks();
    const { registerAiHandlers } = await import(
      "../../src/main/ipc/handlers/ai.js"
    );
    registerAiHandlers();
    handlerFn = mockIpcMainHandle.mock.calls[0][1] as (
      event: unknown,
      payload: unknown,
    ) => Promise<{ success: boolean }>;
  });

  // ── Validation Zod ─────────────────────────────────────────────────

  it("enregistre le handler sous le canal ai:stream-chat", () => {
    expect(mockIpcMainHandle).toHaveBeenCalledWith(
      "ai:stream-chat",
      expect.any(Function),
    );
  });

  it("valide le payload — rejette payload null", async () => {
    const mockSend = vi.fn();
    const result = await handlerFn({ sender: { send: mockSend } }, null);
    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: expect.any(String),
    });
    expect(result.success).toBe(false);
  });

  it("valide le payload — rejette payload undefined", async () => {
    const mockSend = vi.fn();
    const result = await handlerFn({ sender: { send: mockSend } }, undefined);
    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: expect.any(String),
    });
    expect(result.success).toBe(false);
  });

  it("valide le payload — rejette messages vides", async () => {
    const mockSend = vi.fn();
    const result = await handlerFn(
      { sender: { send: mockSend } },
      { providerId: "ollama-default", messages: [] },
    );
    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: expect.any(String),
    });
    expect(result.success).toBe(false);
  });

  it("valide le payload — rejette providerId vide", async () => {
    const mockSend = vi.fn();
    const result = await handlerFn(
      { sender: { send: mockSend } },
      { providerId: "", messages: [{ role: "user", content: "Hi" }] },
    );
    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: expect.any(String),
    });
    expect(result.success).toBe(false);
  });

  it("valide le payload — rejette role invalide", async () => {
    const mockSend = vi.fn();
    const result = await handlerFn(
      { sender: { send: mockSend } },
      {
        providerId: "ollama-default",
        messages: [{ role: "admin", content: "Hi" }],
      },
    );
    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: expect.any(String),
    });
    expect(result.success).toBe(false);
  });

  it("valide le payload — rejette temperature hors limite", async () => {
    const mockSend = vi.fn();
    const result = await handlerFn(
      { sender: { send: mockSend } },
      {
        providerId: "ollama-default",
        messages: [{ role: "user", content: "Hi" }],
        options: { temperature: 99 },
      },
    );
    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: expect.any(String),
    });
    expect(result.success).toBe(false);
  });

  // ── Streaming — chunks ─────────────────────────────────────────────

  it("stream produit des chunks et émet ai:stream-chunk", async () => {
    async function* fakeStream(): AsyncIterable<string> {
      yield "Hello ";
      yield "World";
    }
    mockStreamChat.mockReturnValue(fakeStream());

    const mockSend = vi.fn();
    const result = await handlerFn(
      { sender: { send: mockSend } },
      {
        providerId: "ollama-default",
        messages: [{ role: "user", content: "Hi" }],
      },
    );

    expect(mockStreamChat).toHaveBeenCalledWith(
      "ollama-default",
      [{ role: "user", content: "Hi" }],
      undefined,
    );
    expect(mockSend).toHaveBeenNthCalledWith(1, "ai:stream-chunk", "Hello ");
    expect(mockSend).toHaveBeenNthCalledWith(2, "ai:stream-chunk", "World");
    expect(result.success).toBe(true);
  });

  it("stream émet ai:stream-end après le dernier chunk", async () => {
    async function* fakeStream(): AsyncIterable<string> {
      yield "Done";
    }
    mockStreamChat.mockReturnValue(fakeStream());

    const mockSend = vi.fn();
    await handlerFn(
      { sender: { send: mockSend } },
      {
        providerId: "ollama-default",
        messages: [{ role: "user", content: "Hi" }],
      },
    );

    expect(mockSend).toHaveBeenCalledWith("ai:stream-end", { done: true });
  });

  it("stream émet ai:stream-error en cas d'erreur provider", async () => {
    // Renvoie un AsyncIterable dont l'itérateur rejette
    mockStreamChat.mockReturnValue({
      [Symbol.asyncIterator](): AsyncIterator<string> {
        return {
          next(): Promise<IteratorResult<string>> {
            return Promise.reject(new Error("Network error"));
          },
        };
      },
    });

    const mockSend = vi.fn();
    const result = await handlerFn(
      { sender: { send: mockSend } },
      {
        providerId: "ollama-default",
        messages: [{ role: "user", content: "Hi" }],
      },
    );

    expect(mockSend).toHaveBeenCalledWith("ai:stream-error", {
      message: "Network error",
    });
    expect(result.success).toBe(false);
  });

  it("stream gère les options (temperature, maxTokens, jsonMode)", async () => {
    async function* fakeStream(): AsyncIterable<string> {
      yield "Hello";
    }
    mockStreamChat.mockReturnValue(fakeStream());

    const mockSend = vi.fn();
    await handlerFn(
      { sender: { send: mockSend } },
      {
        providerId: "ollama-default",
        messages: [{ role: "user", content: "Hi" }],
        options: { temperature: 0.5, maxTokens: 100, jsonMode: true },
      },
    );

    expect(mockStreamChat).toHaveBeenCalledWith(
      "ollama-default",
      [{ role: "user", content: "Hi" }],
      { temperature: 0.5, maxTokens: 100, jsonMode: true },
    );
  });
});

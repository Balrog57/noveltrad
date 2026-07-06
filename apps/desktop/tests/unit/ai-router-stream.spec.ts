import { describe, it, expect, vi } from "vitest";
import { AbortError } from "p-retry";

// Mock electron-log pour les tests qui importent des modules utilisant le logger
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    transports: { console: { format: vi.fn() } },
  },
  initialize: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  debug: vi.fn(),
}));

import { AiRouter } from "../../src/main/services/AiRouter";

describe("AiRouter.streamChat", () => {
  it("devrait yield les chunks du provider dans l'ordre", async () => {
    const router = new AiRouter();
    const chunks = ["Hello", ", ", "World", "!"];

    router.register({
      id: "test-provider",
      name: "Test",
      model: "test-model",
      chat: vi.fn(),
      async *streamChat() {
        for (const c of chunks) {
          yield c;
        }
      },
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
      host: "http://localhost:11434",
    });

    const collected: string[] = [];
    for await (const chunk of router.streamChat("test-provider", [])) {
      collected.push(chunk);
    }
    expect(collected).toEqual(["Hello", ", ", "World", "!"]);
  });

  it("devrait gérer un stream vide", async () => {
    const router = new AiRouter();
    router.register({
      id: "empty-provider",
      name: "Empty",
      model: "empty-model",
      chat: vi.fn(),
      async *streamChat() {
        // Ne yield rien
      },
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
      host: "http://localhost:11434",
    });

    const collected: string[] = [];
    for await (const chunk of router.streamChat("empty-provider", [])) {
      collected.push(chunk);
    }
    expect(collected).toEqual([]);
  });

  it("devrait lever une erreur pour un provider inconnu", async () => {
    const router = new AiRouter();

    await expect(async () => {
      for await (const _chunk of router.streamChat("unknown-provider", [])) {
        // ne devrait jamais arriver
      }
    }).rejects.toThrow("Provider inconnu");
  });

  it("devrait passer les messages et options au provider", async () => {
    const router = new AiRouter();
    const streamChatMock = vi.fn().mockImplementation(async function* () {
      yield "réponse";
    });

    router.register({
      id: "opt-provider",
      name: "Opt",
      model: "opt-model",
      chat: vi.fn(),
      streamChat: streamChatMock,
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
      host: "http://localhost:11434",
    });

    const messages = [
      { role: "system" as const, content: "Sois utile" },
      { role: "user" as const, content: "Bonjour" },
    ];
    const options = { temperature: 0.5 };

    const collected: string[] = [];
    for await (const chunk of router.streamChat("opt-provider", messages, options)) {
      collected.push(chunk);
    }
    expect(collected).toEqual(["réponse"]);
    expect(streamChatMock).toHaveBeenCalledWith(messages, options);
  });

  it("devrait résoudre un provider enregistré via setPluginProviderResolver", async () => {
    const router = new AiRouter();
    router.setPluginProviderResolver((id: string) => {
      if (id === "plugin-provider") {
        return {
          id: "plugin-provider",
          name: "Plugin",
          model: "plugin-model",
          chat: vi.fn(),
          async *streamChat() {
            yield "chunk from plugin";
          },
          listModels: vi.fn(),
          embeddings: vi.fn(),
          isAvailable: vi.fn(),
          host: "http://localhost:11434",
        };
      }
      return undefined;
    });

    const collected: string[] = [];
    for await (const chunk of router.streamChat("plugin-provider", [])) {
      collected.push(chunk);
    }
    expect(collected).toEqual(["chunk from plugin"]);
  });

  // ── Tests T3 fix : retry centralisé au niveau AiRouter ────────────────

  it("devrait retry 3 fois sur erreur 5xx via chat() (4 appels total max)", async () => {
    // T3 fix : le retry réseau est centralisé dans AiRouter, pas dans le provider.
    // On vérifie qu'un provider qui throw sur 5xx est appelé 4 fois (1 + 3 retries),
    // et non 16 fois (ce qui serait le cas avec un double-retry provider × router).
    const router = new AiRouter();
    const chatMock = vi.fn().mockRejectedValue(new Error("HTTP 500"));
    router.register({
      id: "flaky-provider",
      name: "Flaky",
      model: "flaky-model",
      chat: chatMock,
      streamChat: vi.fn(),
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
      host: "http://localhost:11434",
    });

    await expect(
      router.chat("flaky-provider", [{ role: "user", content: "Hi" }]),
    ).rejects.toThrow("HTTP 500");
    // 1 tentative + 3 retries = 4 appels (pas 16)
    expect(chatMock).toHaveBeenCalledTimes(4);
  }, 15000);

  it("ne devrait pas retry sur erreur 4xx (AbortError) via chat()", async () => {
    // T3 fix : les erreurs 4xx doivent être propagées immédiatement (AbortError).
    // p-retry v8 vérifie instanceof AbortError — on instancie la vraie classe.
    const router = new AiRouter();
    const chatMock = vi.fn().mockRejectedValue(new AbortError("HTTP 404"));
    router.register({
      id: "not-found-provider",
      name: "NotFound",
      model: "nf-model",
      chat: chatMock,
      streamChat: vi.fn(),
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
      host: "http://localhost:11434",
    });

    await expect(
      router.chat("not-found-provider", [{ role: "user", content: "Hi" }]),
    ).rejects.toThrow("HTTP 404");
    // 1 seul appel — pas de retry sur 4xx
    expect(chatMock).toHaveBeenCalledTimes(1);
  });
});

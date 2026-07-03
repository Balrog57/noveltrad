import { describe, it, expect, vi } from "vitest";

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
      for await (const _ of router.streamChat("unknown-provider", [])) {
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
});

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock electron/net.fetch for OllamaProvider
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Mock OpenAI — une seule fois au niveau du fichier
// ---------------------------------------------------------------------------

const openaiMockModelsList = vi.fn();
const openaiMockChatCreate = vi.fn();
const openaiMockEmbeddingsCreate = vi.fn();

vi.mock("openai", () => ({
  default: vi.fn().mockImplementation(() => ({
    models: { list: openaiMockModelsList },
    chat: { completions: { create: openaiMockChatCreate } },
    embeddings: { create: openaiMockEmbeddingsCreate },
  })),
}));

// ---------------------------------------------------------------------------
// OllamaProvider
// ---------------------------------------------------------------------------

describe("OllamaProvider", () => {
  beforeEach(() => {
    mockNetFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("devrait retourner l'id, le nom et le modèle", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider(
      "ollama",
      "Ollama local",
      "qwen3.5:9b",
    );
    expect(provider.id).toBe("ollama");
    expect(provider.name).toBe("Ollama local");
    expect(provider.model).toBe("qwen3.5:9b");
    expect(provider.host).toBe("http://localhost:11434");
  });

  it("devrait lister les modèles disponibles", async () => {
    mockNetFetch.mockResolvedValue(
      mockJsonResponse({
        models: [
          { name: "qwen3.5:9b" },
          { name: "nomic-embed-text:latest" },
        ],
      }),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const models = await provider.listModels();
    expect(models).toContain("qwen3.5:9b");
    expect(models).toContain("nomic-embed-text:latest");
  });

  it("devrait envoyer un chat et retourner le contenu", async () => {
    mockNetFetch.mockResolvedValue(
      mockJsonResponse({ message: { content: "Bonjour le monde" } }),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const result = await provider.chat([
      { role: "user", content: "Bonjour" },
    ]);
    expect(result).toBe("Bonjour le monde");
  });

  it("devrait streamer un chat", async () => {
    mockNetFetch.mockResolvedValue(
      mockStreamResponse([
        JSON.stringify({ message: { content: "Bonjour le monde" } }) +
          "\n" +
          JSON.stringify({ message: { content: "" } }) +
          "\n",
      ]),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const chunks: string[] = [];
    for await (const chunk of provider.streamChat([
      { role: "user", content: "Hi" },
    ])) {
      chunks.push(chunk);
    }
    expect(chunks).toEqual(["Bonjour le monde"]);
  });

  it("devrait générer des embeddings", async () => {
    mockNetFetch.mockResolvedValue(
      mockJsonResponse({ embedding: [0.1, 0.2, 0.3] }),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider(
      "ollama",
      "Ollama",
      "nomic-embed-text",
    );
    const embeddings = await provider.embeddings(["Hello world"]);
    expect(embeddings).toHaveLength(1);
    expect(embeddings[0]).toEqual([0.1, 0.2, 0.3]);
  });

  it("devrait retourner true si Ollama est disponible", async () => {
    mockNetFetch.mockResolvedValue(
      mockJsonResponse({ models: [{ name: "qwen3.5:9b" }] }),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const available = await provider.isAvailable();
    expect(available).toBe(true);
  });

  it("devrait supporter l'option jsonMode", async () => {
    mockNetFetch.mockResolvedValue(
      mockJsonResponse({ message: { content: "ok" } }),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    await provider.chat([{ role: "user", content: "JSON" }], {
      jsonMode: true,
    });

    expect(mockNetFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({
        body: expect.stringContaining('"json"'),
      }),
    );
  });

  it("devrait retourner false si Ollama est indisponible", async () => {
    mockNetFetch.mockRejectedValue(new Error("Connexion refusée"));

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const available = await provider.isAvailable();
    expect(available).toBe(false);
  });

  // ── Tests ajoutés Phase 0 validation ─────────────────────────────

  it("devrait gérer le timeout réseau sur listModels", async () => {
    const abortError = new DOMException("The operation was aborted", "AbortError");
    mockNetFetch.mockRejectedValue(abortError);

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    await expect(provider.listModels()).rejects.toThrow("aborted");
  });

  it("devrait retry 3 fois sur erreur HTTP 500 (chat) puis abandonner", async () => {
    mockNetFetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal Server Error"),
      json: () => Promise.reject(new Error("Not JSON")),
      body: null,
    });

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    await expect(
      provider.chat([{ role: "user", content: "Hi" }]),
    ).rejects.toThrow("HTTP 500");
    // 1 tentative + 3 retries = 4 appels
    expect(mockNetFetch).toHaveBeenCalledTimes(4);
  }, 15000);

  it("devrait gérer un message.content undefined dans chat", async () => {
    mockNetFetch.mockResolvedValue(
      mockJsonResponse({ message: {} }),
    );

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    // OllamaProvider.chat() returns data.message.content — undefined when missing
    const result = await provider.chat([{ role: "user", content: "Hi" }]);
    expect(result).toBeUndefined();
  });

  it("devrait retry 3 fois sur erreur HTTP 500 (streamChat) puis abandonner", async () => {
    mockNetFetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal Server Error"),
      json: () => Promise.reject(new Error("Not JSON")),
      body: null,
    });

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    const gen = provider.streamChat([{ role: "user", content: "Hi" }]);
    await expect(gen[Symbol.asyncIterator]().next()).rejects.toThrow("HTTP 500");
    // 1 tentative + 3 retries = 4 appels
    expect(mockNetFetch).toHaveBeenCalledTimes(4);
  }, 15000);

  it("devrait gérer reader null sur streamChat", async () => {
    mockNetFetch.mockResolvedValue({
      ok: true,
      status: 200,
      text: () => Promise.resolve(""),
      json: () => Promise.reject(new Error("Not JSON")),
      body: null,
    });

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");

    const gen = provider.streamChat([{ role: "user", content: "Hi" }]);
    await expect(gen[Symbol.asyncIterator]().next()).rejects.toThrow("No response body");
  });

  it("devrait streamer plusieurs chunks correctement", async () => {
    // All NDJSON lines in a single string — the parser splits by \n
    const ndjson =
      JSON.stringify({ message: { content: "Hello" } }) + "\n" +
      JSON.stringify({ message: { content: " " } }) + "\n" +
      JSON.stringify({ message: { content: "World" } }) + "\n" +
      JSON.stringify({ message: { content: "" } }) + "\n";
    mockNetFetch.mockResolvedValue(mockStreamResponse([ndjson]));

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const result: string[] = [];
    for await (const chunk of provider.streamChat([
      { role: "user", content: "Hi" },
    ])) {
      result.push(chunk);
    }
    expect(result).toEqual(["Hello", " ", "World"]);
  });

  it("devrait retry 3 fois sur erreur HTTP 500 (embeddings) puis abandonner", async () => {
    mockNetFetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal Server Error"),
      json: () => Promise.reject(new Error("Not JSON")),
      body: null,
    });

    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "nomic-embed-text");

    await expect(provider.embeddings(["test"])).rejects.toThrow("HTTP 500");
    // 1 tentative + 3 retries = 4 appels
    expect(mockNetFetch).toHaveBeenCalledTimes(4);
  }, 15000);

  it("devrait gérer un tableau vide sur embeddings", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "nomic-embed-text");

    const result = await provider.embeddings([]);
    expect(result).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// OpenAiCompatibleProvider
// ---------------------------------------------------------------------------

describe("OpenAiCompatibleProvider", () => {
  beforeEach(() => {
    openaiMockModelsList.mockResolvedValue({
      data: [{ id: "gpt-4" }, { id: "gpt-3.5-turbo" }],
    });
    openaiMockChatCreate.mockResolvedValue({
      choices: [{ message: { content: "Bonjour le monde" } }],
    });
    openaiMockEmbeddingsCreate.mockResolvedValue({
      data: [
        { embedding: [0.1, 0.2, 0.3] },
        { embedding: [0.4, 0.5, 0.6] },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("devrait retourner l'id, le nom et le modèle", async () => {
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
      "sk-test",
    );
    expect(provider.id).toBe("openai");
    expect(provider.name).toBe("OpenAI");
    expect(provider.model).toBe("gpt-4");
    expect(provider.apiKey).toBe("sk-test");
  });

  it("devrait lister les modèles", async () => {
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
    );
    const models = await provider.listModels();
    expect(models).toEqual(["gpt-4", "gpt-3.5-turbo"]);
  });

  it("devrait envoyer un chat et retourner le contenu", async () => {
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
    );
    const result = await provider.chat([{ role: "user", content: "Bonjour" }]);
    expect(result).toBe("Bonjour le monde");
  });

  it("devrait retourner une chaîne vide si le message est absent", async () => {
    openaiMockChatCreate.mockResolvedValue({
      choices: [{ message: { content: null } }],
    });
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
    );
    const result = await provider.chat([{ role: "user", content: "test" }]);
    expect(result).toBe("");
  });

  it("devrait générer des embeddings", async () => {
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "text-embedding-3-small",
      "https://api.openai.com/v1",
    );
    const embeddings = await provider.embeddings(["Hello", "World"]);
    expect(embeddings).toHaveLength(2);
    expect(embeddings[0]).toEqual([0.1, 0.2, 0.3]);
  });

  it("devrait retourner true si disponible", async () => {
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
    );
    const available = await provider.isAvailable();
    expect(available).toBe(true);
  });

  it("devrait retourner false si indisponible", async () => {
    openaiMockModelsList.mockRejectedValue(new Error("API key invalide"));
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
    );
    const available = await provider.isAvailable();
    expect(available).toBe(false);
  });

  it("devrait supporter l'option jsonMode", async () => {
    const { OpenAiCompatibleProvider } = await import(
      "../../src/main/services/providers/OpenAiCompatibleProvider"
    );
    const provider = new OpenAiCompatibleProvider(
      "openai",
      "OpenAI",
      "gpt-4",
      "https://api.openai.com/v1",
    );
    await provider.chat([{ role: "user", content: "JSON" }], {
      jsonMode: true,
    });
    expect(openaiMockChatCreate).toHaveBeenCalledWith(
      expect.objectContaining({ response_format: { type: "json_object" } }),
    );
  });
});

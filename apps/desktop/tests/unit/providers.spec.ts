import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock Ollama — une seule fois au niveau du fichier
// ---------------------------------------------------------------------------

const ollamaMockChat = vi.fn().mockImplementation((opts: { stream?: boolean }) => {
  if (opts.stream) {
    return (async function* () {
      yield { message: { content: "Bonjour le monde" } };
    })();
  }
  return Promise.resolve({
    message: { content: "Bonjour le monde" },
  });
});
const ollamaMockList = vi.fn();
const ollamaMockEmbeddings = vi.fn();

vi.mock("ollama", () => ({
  Ollama: vi.fn().mockImplementation(() => ({
    chat: ollamaMockChat,
    list: ollamaMockList,
    embeddings: ollamaMockEmbeddings,
  })),
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
    // ollamaMockChat a déjà une implémentation par défaut qui gère stream et non-stream
    // On remet juste les autres mocks
    ollamaMockChat.mockClear();
    ollamaMockList.mockResolvedValue({
      models: [{ name: "qwen3.5:9b" }, { name: "nomic-embed-text:latest" }],
    });
    ollamaMockEmbeddings.mockResolvedValue({
      embedding: [0.1, 0.2, 0.3],
    });
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
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const models = await provider.listModels();
    expect(models).toContain("qwen3.5:9b");
    expect(models).toContain("nomic-embed-text:latest");
  });

  it("devrait envoyer un chat et retourner le contenu", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const result = await provider.chat([{ role: "user", content: "Bonjour" }]);
    expect(result).toBe("Bonjour le monde");
  });

  it("devrait streamer un chat", async () => {
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
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    const available = await provider.isAvailable();
    expect(available).toBe(true);
  });

  it("devrait supporter l'option jsonMode", async () => {
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider("ollama", "Ollama", "qwen3.5:9b");
    await provider.chat([{ role: "user", content: "JSON" }], {
      jsonMode: true,
    });
    expect(ollamaMockChat).toHaveBeenCalledWith(
      expect.objectContaining({ format: "json" }),
    );
  });

  it("devrait retourner false si Ollama est indisponible", async () => {
    ollamaMockList.mockRejectedValue(new Error("Connexion refusée"));
    const { OllamaProvider } = await import(
      "../../src/main/services/providers/OllamaProvider"
    );
    const provider = new OllamaProvider(
      "ollama",
      "Ollama",
      "qwen3.5:9b",
    );
    const available = await provider.isAvailable();
    expect(available).toBe(false);
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

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock electron/net.fetch (must be hoisted with vi.hoisted)
// ---------------------------------------------------------------------------

const { mockNetFetch } = vi.hoisted(() => ({
  mockNetFetch: vi.fn(),
}));

vi.mock("electron", () => ({
  net: { fetch: mockNetFetch },
}));

// Mock electron-log avant d'importer quoi que ce soit qui l'utilise
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

import { RagEngine } from "../../src/main/services/RagEngine";

// ---------------------------------------------------------------------------
// Mock DB
// ---------------------------------------------------------------------------

class MockRagDatabase {
  private embeddings: Map<
    string,
    {
      id: string;
      chapter_id: string;
      paragraph_id: string;
      embedding_json: string;
      created_at: string;
    }
  > = new Map();

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    run: (params: unknown[]) => void;
    all: (params: unknown[]) => unknown[];
  } {
    return {
      get: (params: unknown[]): unknown => {
        if (sql.includes("SELECT id FROM embeddings")) {
          const paragraphId = params[0] as string;
          for (const [, row] of this.embeddings) {
            if (row.paragraph_id === paragraphId) return { id: row.id };
          }
          return undefined;
        }
        return undefined;
      },
      run: (params: unknown[]): void => {
        if (sql.includes("INSERT INTO embeddings")) {
          const [id, chapterId, paragraphId, embeddingJson, createdAt] =
            params as [string, string, string, string, string];
          this.embeddings.set(id, {
            id,
            chapter_id: chapterId,
            paragraph_id: paragraphId,
            embedding_json: embeddingJson,
            created_at: createdAt,
          });
          return;
        }
      },
      all: (params: unknown[]): unknown[] => {
        if (sql.includes("JOIN chapters c ON e.chapter_id = c.id")) {
          const projectId = params[0] as string;
          const rows: Array<{
            paragraph_id: string;
            embedding_json: string;
            source_text: string;
            translated_text: string | null;
          }> = [];
          for (const [, row] of this.embeddings) {
            if (row.chapter_id.startsWith(projectId)) {
              rows.push({
                paragraph_id: row.paragraph_id,
                embedding_json: row.embedding_json,
                source_text: "The dragon flew.",
                translated_text: "Le dragon volait.",
              });
            }
          }
          return rows;
        }
        return [];
      },
    };
  }
}

// ---------------------------------------------------------------------------
// Tests RagEngine
// ---------------------------------------------------------------------------

describe("RagEngine", () => {
  let db: MockRagDatabase;
  let engine: RagEngine;
  const OLLAMA_HOST = "http://localhost:11434";

  beforeEach(() => {
    db = new MockRagDatabase();
    engine = new RagEngine(db as never, OLLAMA_HOST, "nomic-embed-text");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockNetFetch.mockReset();
  });

  // ── computeEmbedding ──

  describe("computeEmbedding", () => {
    it("devrait calculer un embedding via l'API Ollama", async () => {
      const fakeEmbedding = [0.1, 0.2, 0.3, 0.4, 0.5];
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ embedding: fakeEmbedding }),
      });

      const result = await engine.computeEmbedding("Hello world");
      expect(result).toEqual(fakeEmbedding);
      expect(mockNetFetch).toHaveBeenCalledWith(
        `${OLLAMA_HOST}/api/embeddings`,
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: expect.stringContaining("nomic-embed-text"),
        }),
      );
    });

    it("devrait lancer une erreur si l'API répond avec un statut d'erreur", async () => {
      mockNetFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });

      await expect(engine.computeEmbedding("test")).rejects.toThrow(
        "Erreur Ollama embeddings (500)",
      );
    });

    it("devrait propager les erreurs réseau", async () => {
      mockNetFetch.mockRejectedValue(new Error("Connexion refusée"));

      await expect(engine.computeEmbedding("test")).rejects.toThrow(
        "Connexion refusée",
      );
    });
  });

  // ── storeEmbedding ──

  describe("storeEmbedding", () => {
    it("devrait stocker un embedding en base", () => {
      const embedding = [0.1, 0.2, 0.3];
      engine.storeEmbedding("ch1", "p1", embedding);
      // Pas d'erreur = succès
    });

    it("devrait ignorer l'insertion si l'embedding existe déjà", () => {
      engine.storeEmbedding("ch1", "p1", [0.1, 0.2]);
      // Deuxième appel avec le même paragraphId ne devrait pas planter
      engine.storeEmbedding("ch1", "p1", [0.3, 0.4]);
    });
  });

  // ── cosineSimilarity ──

  describe("cosineSimilarity", () => {
    it("devrait retourner 1 pour deux vecteurs identiques", () => {
      const result = engine.cosineSimilarity([1, 2, 3], [1, 2, 3]);
      expect(result).toBe(1);
    });

    it("devrait retourner 0 pour deux vecteurs orthogonaux", () => {
      const result = engine.cosineSimilarity([1, 0], [0, 1]);
      expect(result).toBe(0);
    });

    it("devrait retourner 0 si les dimensions diffèrent", () => {
      const result = engine.cosineSimilarity([1, 2], [1, 2, 3]);
      expect(result).toBe(0);
    });

    it("devrait retourner 0 si la norme est nulle", () => {
      const result = engine.cosineSimilarity([0, 0], [1, 2]);
      expect(result).toBe(0);
    });

    it("devrait calculer la similarité entre deux vecteurs non normalisés", () => {
      // a = [1, 2, 3], b = [4, 5, 6]
      // dot = 4 + 10 + 18 = 32
      // normA = sqrt(1+4+9) = sqrt(14) ≈ 3.742
      // normB = sqrt(16+25+36) = sqrt(77) ≈ 8.775
      // cos = 32 / (3.742 * 8.775) ≈ 0.974
      const result = engine.cosineSimilarity([1, 2, 3], [4, 5, 6]);
      expect(result).toBeCloseTo(0.974, 2);
    });
  });

  // ── findSimilar ──

  describe("findSimilar", () => {
    it("devrait retourner les K paragraphes les plus similaires", async () => {
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          embedding: [0.1, 0.2, 0.3],
        }),
      });

      // Pré-remplir la DB avec des embeddings
      engine.storeEmbedding("proj-1_ch1", "p1", [0.1, 0.2, 0.3]);
      engine.storeEmbedding("proj-1_ch1", "p2", [0.4, 0.5, 0.6]);
      engine.storeEmbedding("proj-1_ch1", "p3", [0.7, 0.8, 0.9]);

      const results = await engine.findSimilar("test text", "proj-1", 2);
      expect(results).toHaveLength(2);
      expect(results[0]).toHaveProperty("paragraphId");
      expect(results[0]).toHaveProperty("sourceText");
      expect(results[0]).toHaveProperty("translatedText");
      expect(results[0]).toHaveProperty("similarity");
    });

    it("devrait retourner un tableau vide si aucun embedding n'existe", async () => {
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ embedding: [0.1, 0.2] }),
      });

      const results = await engine.findSimilar("test", "empty-project");
      expect(results).toEqual([]);
    });
  });

  // ── isAvailable ──

  describe("isAvailable", () => {
    it("devrait retourner true si le modèle d'embedding est trouvé", async () => {
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          models: [{ name: "nomic-embed-text:latest" }],
        }),
      });

      const available = await engine.isAvailable();
      expect(available).toBe(true);
    });

    it("devrait retourner false si le modèle d'embedding est absent", async () => {
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          models: [{ name: "qwen3.5:9b" }],
        }),
      });

      const available = await engine.isAvailable();
      expect(available).toBe(false);
    });

    it("devrait retourner false si Ollama est injoignable", async () => {
      mockNetFetch.mockRejectedValue(new Error("Connexion refusée"));

      const available = await engine.isAvailable();
      expect(available).toBe(false);
    });

    it("devrait retourner false si la réponse Ollama n'est pas OK", async () => {
      mockNetFetch.mockResolvedValue({
        ok: false,
        status: 503,
      });

      const available = await engine.isAvailable();
      expect(available).toBe(false);
    });
  });
});

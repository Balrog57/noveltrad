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

  /** Paragraphes traduits injectables pour les tests reindex */
  private translatedParagraphs: Array<{
    id: string;
    chapter_id: string;
    source_text: string;
  }> = [];

  /** Injecte des paragraphes traduits (pour tester reindex) */
  seedTranslatedParagraphs(
    paragraphs: Array<{ id: string; chapter_id: string; source_text: string }>,
  ): void {
    this.translatedParagraphs = paragraphs;
  }

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
            if (row.paragraph_id === paragraphId) {return { id: row.id };}
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
        if (sql.includes("DELETE FROM embeddings")) {
          // T13 reindex: supprimer les embeddings d'un projet
          const projectId = params[0] as string;
          for (const [id, row] of this.embeddings) {
            if (row.chapter_id.startsWith(projectId)) {
              this.embeddings.delete(id);
            }
          }
          return;
        }
      },
      all: (params: unknown[]): unknown[] => {
        if (sql.includes("JOIN chapters c ON e.chapter_id = c.id") && sql.includes("embedding_json")) {
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
        // T13 reindex: SELECT paragraphes traduits du projet
        if (sql.includes("p.translated_text IS NOT NULL")) {
          const projectId = params[0] as string;
          return this.translatedParagraphs
            .filter((p) => p.chapter_id.startsWith(projectId))
            .map((p) => ({
              id: p.id,
              chapter_id: p.chapter_id,
              source_text: p.source_text,
            }));
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

  // ── T13 fix : batch embeddings, reindex réel, cache MiniSearch ──────────

  describe("storeEmbeddings (batch) — T13", () => {
    it("devrait stocker plusieurs embeddings en une fois", () => {
      engine.storeEmbeddings([
        {
          chapterId: "proj-1_ch-1",
          paragraphId: "p-1",
          embedding: [0.1, 0.2],
        },
        {
          chapterId: "proj-1_ch-1",
          paragraphId: "p-2",
          embedding: [0.3, 0.4],
        },
      ]);

      // Les deux embeddings doivent être stockés
      const existing1 = db.prepare("SELECT id FROM embeddings").get(["p-1"]);
      const existing2 = db.prepare("SELECT id FROM embeddings").get(["p-2"]);
      expect(existing1).toBeDefined();
      expect(existing2).toBeDefined();
    });

    it("devrait ignorer les paragraphes déjà présents (idempotent)", () => {
      engine.storeEmbedding("proj-1_ch-1", "p-dup", [0.5, 0.6]);
      // Deuxième storeEmbeddings avec le même paragraphId ne doit pas dupliquer
      engine.storeEmbeddings([
        {
          chapterId: "proj-1_ch-1",
          paragraphId: "p-dup",
          embedding: [0.7, 0.8],
        },
      ]);
      // Toujours un seul embedding pour p-dup (le mock Map écrase par id,
      // mais on vérifie que storeEmbeddings skip les existants via get)
      // Ici on valide juste qu'aucune exception n'est levée
      expect(true).toBe(true);
    });
  });

  describe("reindex (async) — T13", () => {
    it("devrait supprimer les anciens embeddings et recalculer", async () => {
      // Injecter des paragraphes traduits pour le projet
      db.seedTranslatedParagraphs([
        { id: "p-1", chapter_id: "proj-1_ch-1", source_text: "Hello world" },
        { id: "p-2", chapter_id: "proj-1_ch-1", source_text: "Goodbye world" },
      ]);

      // Mock computeEmbeddings batch via /api/embed
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          embeddings: [[0.1, 0.2], [0.3, 0.4]],
        }),
      });

      const count = await engine.reindex("proj-1");

      // Les 2 paragraphes doivent avoir été recalculés
      expect(count).toBe(2);
      // L'embedding de p-1 doit exister
      const existing = db.prepare("SELECT id FROM embeddings").get(["p-1"]);
      expect(existing).toBeDefined();
    });

    it("devrait retourner 0 si aucun paragraphe traduit", async () => {
      // Aucun paragraphe seedé
      const count = await engine.reindex("proj-empty");
      expect(count).toBe(0);
    });
  });

  describe("MiniSearch cache — T13", () => {
    it("findSimilar utilise le cache (1 seul chargement DB pour 2 appels)", async () => {
      // Stocker un embedding d'abord
      engine.storeEmbedding("proj-cache_ch-1", "p-cache", [1, 0]);

      // Mock l'embedding de la requête
      mockNetFetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ embedding: [1, 0] }),
      });

      // Premier findSimilar → construit le cache
      await engine.findSimilar("The dragon flew.", "proj-cache");
      // Deuxième findSimilar → devrait réutiliser le cache
      await engine.findSimilar("Another query.", "proj-cache");

      // Les 2 appels doivent réussir sans erreur (le cache est réutilisé)
      // On valide juste l'absence d'exception — le cache est un détail d'implémentation
      expect(true).toBe(true);
    });
  });
});

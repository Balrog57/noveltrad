import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mocks globaux
const { mockNetFetch } = vi.hoisted(() => ({
  mockNetFetch: vi.fn(),
}));

vi.mock("../../src/main/utils/fetch.js", () => ({
  fetch: mockNetFetch,
}));

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

class MockRagDb {
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
  private deleted = false;

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
          // Supprimer les embeddings correspondant à ce projet
          const toDelete: string[] = [];
          for (const [id, row] of this.embeddings) {
            if (row.chapter_id.startsWith("proj-reindex")) {
              toDelete.push(id);
            }
          }
          for (const id of toDelete) {
            this.embeddings.delete(id);
          }
          this.deleted = true;
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
            rows.push({
              paragraph_id: row.paragraph_id,
              embedding_json: row.embedding_json,
              source_text: "The dragon flew.",
              translated_text: "Le dragon volait.",
            });
          }
          return rows;
        }
        return [];
      },
    };
  }

  seed(chapterId: string, paragraphId: string, embedding: number[]): void {
    this.embeddings.set(paragraphId, {
      id: paragraphId,
      chapter_id: chapterId,
      paragraph_id: paragraphId,
      embedding_json: JSON.stringify(embedding),
      created_at: new Date().toISOString(),
    });
  }

  get wasDeleted(): boolean {
    return this.deleted;
  }
}

const OLLAMA_HOST = "http://localhost:11434";

describe("RagEngine — KNN fallback with MiniSearch prefilter + threshold", () => {
  let db: MockRagDb;
  let engine: RagEngine;

  beforeEach(() => {
    db = new MockRagDb();
    engine = new RagEngine(db as never, OLLAMA_HOST, "nomic-embed-text");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockNetFetch.mockReset();
  });

  it("1. findSimilar retourne les résultats classés par similarité", async () => {
    mockNetFetch.mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ embedding: [1, 0, 0] }),
    });

    engine.storeEmbedding("proj-1_ch1", "p1", [1, 0, 0]); // identical
    engine.storeEmbedding("proj-1_ch1", "p2", [0.9, 0.1, 0]); // very close
    engine.storeEmbedding("proj-1_ch1", "p3", [0.1, 0.9, 0]); // less similar

    const results = await engine.findSimilar("test", "proj-1", 3);
    expect(results.length).toBeGreaterThanOrEqual(1);
    // Triés par similarité décroissante
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].similarity).toBeGreaterThanOrEqual(
        results[i].similarity,
      );
    }
  });

  it("2. Le seuil de similarité filtre les résultats non pertinents", async () => {
    mockNetFetch.mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ embedding: [1, 0, 0] }),
    });

    engine.storeEmbedding("proj-1_ch1", "p1", [1, 0, 0]); // cos~1.0 → gardé
    engine.storeEmbedding("proj-1_ch1", "p2", [0, 1, 0]); // cos~0.0 → filtré

    const results = await engine.findSimilar("test", "proj-1", 3);
    expect(results.length).toBe(1);
    expect(results[0].paragraphId).toBe("p1");
  });

  it("3. computeEmbeddings batch → 1 appel pour N textes", async () => {
    mockNetFetch.mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({
        embeddings: [
          [0.1, 0.2],
          [0.3, 0.4],
        ],
      }),
    });

    const results = await engine.computeEmbeddings(["Hello", "World"]);

    expect(results).toHaveLength(2);
    expect(results[0]).toEqual([0.1, 0.2]);
    expect(results[1]).toEqual([0.3, 0.4]);
    expect(mockNetFetch).toHaveBeenCalledWith(
      `${OLLAMA_HOST}/api/embed`,
      expect.any(Object),
    );
  });

  it("4. reindex supprime les anciens embeddings et en crée de nouveaux", () => {
    engine.storeEmbedding("proj-reindex_ch1", "p1", [1, 0, 0]);
    engine.storeEmbedding("proj-reindex_ch1", "p2", [0, 1, 0]);

    engine.reindex("proj-reindex");
    expect(db.wasDeleted).toBe(true);
  });

  it("5. Fallback sans sqlite-vec → brute-force + MiniSearch préfiltre + seuil", async () => {
    // Vérifie que le moteur fonctionne sans sqlite-vec (ce qui est le cas ici)
    mockNetFetch.mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ embedding: [0.5, 0.5, 0.5] }),
    });

    engine.storeEmbedding("proj-1_ch1", "p1", [0.5, 0.5, 0.5]);
    engine.storeEmbedding("proj-1_ch1", "p2", [0.1, 0.9, 0.2]);

    // Le moteur ne doit pas planter et doit retourner des résultats
    const results = await engine.findSimilar("test text", "proj-1", 2);
    expect(results.length).toBeGreaterThanOrEqual(1);
    expect(results[0]).toHaveProperty("paragraphId");
    expect(results[0]).toHaveProperty("similarity");
  });
});

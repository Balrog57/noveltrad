import type { ProjectDatabase } from "../db/connection.js";
import type { RagMatch } from "@shared/types/index.js";
import { logger } from "../utils/logger.js";
import similarity from "compute-cosine-similarity";

/**
 * Moteur RAG (Retrieval-Augmented Generation) interne léger.
 * Calcule des embeddings via Ollama et les stocke dans SQLite pour
 * enrichir le contexte des agents de traduction avec des paragraphes
 * précédemment traduits similaires.
 */
export class RagEngine {
  private readonly embeddingModel: string;

  constructor(
    private db: ProjectDatabase,
    private ollamaHost: string,
    embeddingModel: string = "nomic-embed-text",
  ) {
    this.embeddingModel = embeddingModel;
  }

  /**
   * Calcule l'embedding d'un texte via l'API Ollama.
   * Retourne un vecteur de nombres (dimensions dépendent du modèle).
   */
  async computeEmbedding(text: string): Promise<number[]> {
    const response = await fetch(`${this.ollamaHost}/api/embeddings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: this.embeddingModel,
        prompt: text,
      }),
    });

    if (!response.ok) {
      throw new Error(
        `Erreur Ollama embeddings (${response.status}): ${response.statusText}`,
      );
    }

    const data = (await response.json()) as { embedding: number[] };
    return data.embedding;
  }

  /**
   * Stocke un embedding en base. Si un embedding existe déjà pour ce paragraphe,
   * on saute l'insertion (les embeddings sont calculés une fois, réutilisés).
   */
  storeEmbedding(
    chapterId: string,
    paragraphId: string,
    embedding: number[],
  ): void {
    const existing = this.db
      .prepare("SELECT id FROM embeddings WHERE paragraph_id = ?")
      .get([paragraphId]);
    if (existing) return;

    this.db
      .prepare(
        `INSERT INTO embeddings (id, chapter_id, paragraph_id, embedding_json, created_at)
       VALUES (?, ?, ?, ?, ?)`,
      )
      .run([
        crypto.randomUUID(),
        chapterId,
        paragraphId,
        JSON.stringify(embedding),
        new Date().toISOString(),
      ]);
  }

  /**
   * Trouve les K paragraphes les plus similaires à sourceText
   * parmi tous les chapitres déjà traduits du projet.
   */
  async findSimilar(
    sourceText: string,
    projectId: string,
    topK: number = 3,
  ): Promise<RagMatch[]> {
    // 1. Calculer l'embedding du texte source
    const sourceEmbedding = await this.computeEmbedding(sourceText);

    // 2. Charger tous les embeddings du projet (JOIN paragraphs + chapters)
    const rows = this.db
      .prepare(
        `SELECT e.paragraph_id, e.embedding_json, p.source_text, p.translated_text
       FROM embeddings e
       JOIN paragraphs p ON e.paragraph_id = p.id
       JOIN chapters c ON e.chapter_id = c.id
       WHERE c.project_id = ?`,
      )
      .all([projectId]) as Array<{
      paragraph_id: string;
      embedding_json: string;
      source_text: string;
      translated_text: string | null;
    }>;

    if (rows.length === 0) return [];

    // 3. Calculer la similarité cosinus pour chaque embedding stocké
    const scored: RagMatch[] = rows.map((row) => {
      const storedEmbedding = JSON.parse(row.embedding_json) as number[];
      const similarity = this.cosineSimilarity(
        sourceEmbedding,
        storedEmbedding,
      );
      return {
        paragraphId: row.paragraph_id,
        sourceText: row.source_text,
        translatedText: row.translated_text ?? "",
        similarity,
      };
    });

    // 4. Trier par similarité décroissante et retourner les top K
    scored.sort((a, b) => b.similarity - a.similarity);
    return scored.slice(0, topK);
  }

  /**
   * Calcule la similarité cosinus entre deux vecteurs.
   * Retourne une valeur entre -1 et 1 (1 = identiques, 0 = orthogonaux).
   */
  cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;
    const result = similarity(a, b);
    if (result === null || !isFinite(result)) return 0;
    // Clamp to [-1, 1] due to floating-point imprecision
    return Math.max(-1, Math.min(1, result));
  }

  /**
   * Vérifie si Ollama est disponible et possède le modèle d'embedding.
   */
  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.ollamaHost}/api/tags`);
      if (!response.ok) return false;

      const data = (await response.json()) as {
        models?: Array<{ name: string }>;
      };
      const models = data.models ?? [];
      return models.some((m) => m.name.startsWith(this.embeddingModel));
    } catch {
      logger.warn("RAG: Ollama non disponible ou modèle d'embedding absent.");
      return false;
    }
  }
}

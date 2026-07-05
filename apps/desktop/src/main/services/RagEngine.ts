import type { ProjectDatabase } from "../db/connection.js";
import type { RagMatch } from "@shared/types/index.js";
import { net } from "electron";
import { logger } from "../utils/logger.js";
import similarity from "compute-cosine-similarity";
import MiniSearch from "minisearch";

/**
 * Moteur RAG (Retrieval-Augmented Generation) interne léger.
 * Calcule des embeddings via Ollama et les stocke dans SQLite pour
 * enrichir le contexte des agents de traduction avec des paragraphes
 * précédemment traduits similaires.
 *
 * Utilise un fallback brute-force + MiniSearch préfiltre + seuil de
 * similarité (sqlite-vec non disponible avec node-sqlite3-wasm).
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
    const response = await net.fetch(`${this.ollamaHost}/api/embeddings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: this.embeddingModel,
        prompt: text,
      }),
      signal: AbortSignal.timeout(30_000),
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
   * Calcule les embeddings de plusieurs textes en un seul appel batch.
   * Utilise /api/embed (Ollama 0.5+) avec fallback individuel.
   */
  async computeEmbeddings(texts: string[]): Promise<number[][]> {
    try {
      const response = await net.fetch(`${this.ollamaHost}/api/embed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: this.embeddingModel,
          input: texts,
        }),
        signal: AbortSignal.timeout(120_000),
      });
      if (response.ok) {
        const data = (await response.json()) as { embeddings: number[][] };
        if (data.embeddings?.length === texts.length) {
          return data.embeddings;
        }
      }
    } catch {
      // Fallback per-text
    }

    // Fallback : un appel par texte
    const results: number[][] = [];
    for (const text of texts) {
      results.push(await this.computeEmbedding(text));
    }
    return results;
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
    if (existing) {return;}

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
   * Stocke plusieurs embeddings en une seule fois (batch).
   * Ignore les paragraphes déjà présents.
   */
  storeEmbeddings(
    entries: Array<{
      chapterId: string;
      paragraphId: string;
      embedding: number[];
    }>,
  ): void {
    for (const entry of entries) {
      this.storeEmbedding(entry.chapterId, entry.paragraphId, entry.embedding);
    }
  }

  /**
   * Trouve les K paragraphes les plus similaires à sourceText
   * parmi tous les chapitres déjà traduits du projet.
   *
   * Utilise un préfiltre MiniSearch pour réduire le nombre de candidats,
   * puis calcule la similarité cosinus uniquement sur les candidats retenus.
   * Un seuil de similarité supprime les résultats non pertinents.
   */
  async findSimilar(
    sourceText: string,
    projectId: string,
    topK: number = 3,
  ): Promise<RagMatch[]> {
    // 1. Calculer l'embedding du texte source
    const sourceEmbedding = await this.computeEmbedding(sourceText);

    // 2. Charger tous les embeddings du projet
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

    if (rows.length === 0) {return [];}

    // 3. Construire un index MiniSearch pour le préfiltre
    const miniSearch = new MiniSearch({
      fields: ["source_text"],
      storeFields: ["source_text"],
      searchOptions: { fuzzy: 0.2, prefix: true },
    });
    miniSearch.addAll(
      rows.map((r, i) => ({
        id: String(i),
        source_text: r.source_text,
      })),
    );

    // 4. Chercher les candidats avec MiniSearch
    const msResults = miniSearch.search(sourceText, {
      fuzzy: 0.2,
      prefix: true,
    });
    const candidateIds = new Set(msResults.slice(0, 50).map((r) => parseInt(r.id, 10)));

    // 5. Calculer la similarité cosinus uniquement pour les candidats
    //    (ou tous si MiniSearch ne trouve rien)
    const scored: RagMatch[] = [];
    const candidates =
      candidateIds.size > 0
        ? rows.filter((_, i) => candidateIds.has(i))
        : rows;

    for (const row of candidates) {
      const storedEmbedding = JSON.parse(row.embedding_json) as number[];
      const cosim = this.cosineSimilarity(sourceEmbedding, storedEmbedding);

      // Seuil de similarité (correspond à distance < 0.3 en espace L2 pour des vecteurs normalisés)
      const SIMILARITY_THRESHOLD = 0.7;
      if (cosim < SIMILARITY_THRESHOLD) {continue;}

      scored.push({
        paragraphId: row.paragraph_id,
        sourceText: row.source_text,
        translatedText: row.translated_text ?? "",
        similarity: cosim,
      });
    }

    // 6. Trier par similarité décroissante et retourner les top K
    scored.sort((a, b) => b.similarity - a.similarity);
    return scored.slice(0, topK);
  }

  /**
   * Supprime et recrée tous les embeddings d'un projet.
   * Utile après un changement de modèle d'embedding.
   */
  reindex(projectId: string): void {
    // Supprimer les anciens embeddings via la jointure avec chapters
    this.db
      .prepare(
        `DELETE FROM embeddings WHERE chapter_id IN (
         SELECT id FROM chapters WHERE project_id = ?
       )`,
      )
      .run([projectId]);
    logger.info(
      `[RagEngine] Embeddings réindexés pour le projet ${projectId}`,
    );
  }

  /**
   * Calcule la similarité cosinus entre deux vecteurs.
   * Retourne une valeur entre -1 et 1 (1 = identiques, 0 = orthogonaux).
   */
  cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) {return 0;}
    const result = similarity(a, b);
    if (result === null || !isFinite(result)) {return 0;}
    // Clamp to [-1, 1] due to floating-point imprecision
    return Math.max(-1, Math.min(1, result));
  }

  /**
   * Vérifie si Ollama est disponible et possède le modèle d'embedding.
   */
  async isAvailable(): Promise<boolean> {
    try {
      const response = await net.fetch(`${this.ollamaHost}/api/tags`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) {return false;}

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

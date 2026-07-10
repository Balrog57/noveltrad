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
 * Utilise un préfiltre MiniSearch + cosinus JS (cache par projet) + seuil de
 * similarité. SDD §9.3 ne requiert aucune lib vectorielle native — cette
 * approche est 100% conforme et suffisante jusqu'à ~10k paragraphes.
 */
export class RagEngine {
  private readonly embeddingModel: string;
  /**
   * T13 fix : cache de l'index MiniSearch par projectId.
   * Évite de reconstruire l'index à chaque findSimilar() (coût O(n) par requête).
   * Invalidé quand des embeddings sont stockés (storeEmbedding/storeEmbeddings).
   */
  private miniSearchCache: Map<string, { index: MiniSearch; rows: Array<{ id: number; paragraphId: string; embeddingJson: string; sourceText: string; translatedText: string }> }> = new Map();

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
        // Bug fix : si l'API retourne ok mais avec un nombre d'embeddings
        // différent du nombre de textes (Ollama tronqué, bug), on logue un
        // warning et on bascule sur le fallback per-text — sans cette garde,
        // le caller ferait embeddings[i] sur le mauvais paragraphe (assignation
        // silencieusement décalée dans storeEmbeddingsForChapter).
        logger.warn(
          `[RagEngine] Batch embeddings mismatch: attendu ${texts.length}, reçu ${data.embeddings?.length ?? 0}. Fallback per-text.`,
        );
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

    // T13 fix : invalider le cache MiniSearch (nouvel embedding disponible)
    this.invalidateMiniSearchCache();
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
    let added = false;

    // ⚡ Bolt: Bulk inserts in node-sqlite3-wasm cause massive N+1 overhead.
    // Wrapping the loop in an explicit transaction forces SQLite to flush to disk only once.
    // Impact: Orders of magnitude faster for storing hundreds of embeddings.
    this.db.exec("BEGIN TRANSACTION");
    try {
      for (const entry of entries) {
        const existing = this.db
          .prepare("SELECT id FROM embeddings WHERE paragraph_id = ?")
          .get([entry.paragraphId]);
        if (existing) {continue;}

        this.db
          .prepare(
            `INSERT INTO embeddings (id, chapter_id, paragraph_id, embedding_json, created_at)
           VALUES (?, ?, ?, ?, ?)`,
          )
          .run([
            crypto.randomUUID(),
            entry.chapterId,
            entry.paragraphId,
            JSON.stringify(entry.embedding),
            new Date().toISOString(),
          ]);
        added = true;
      }
      this.db.exec("COMMIT");
    } catch (error) {
      this.db.exec("ROLLBACK");
      throw error;
    }

    // T13 fix : invalider le cache si au moins un embedding a été ajouté
    if (added) {
      this.invalidateMiniSearchCache();
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

    // 2. Récupérer (ou construire) l'index MiniSearch mis en cache pour le projet
    //    T13 fix : l'index était reconstruit à chaque findSimilar — désormais caché.
    const cached = this.getOrBuildMiniSearchIndex(projectId);
    if (!cached || cached.rows.length === 0) {return [];}

    // 3. Chercher les candidats avec MiniSearch (index en cache)
    const msResults = cached.index.search(sourceText, {
      fuzzy: 0.2,
      prefix: true,
    });
    const candidateIds = new Set(msResults.slice(0, 50).map((r) => parseInt(r.id, 10)));

    // 4. Calculer la similarité cosinus uniquement pour les candidats
    //    (ou tous si MiniSearch ne trouve rien)
    const scored: RagMatch[] = [];
    const candidates =
      candidateIds.size > 0
        ? cached.rows.filter((r) => candidateIds.has(r.id))
        : cached.rows;

    for (const row of candidates) {
      const storedEmbedding = JSON.parse(row.embeddingJson) as number[];
      const cosim = this.cosineSimilarity(sourceEmbedding, storedEmbedding);

      // Seuil de similarité (correspond à distance < 0.3 en espace L2 pour des vecteurs normalisés)
      const SIMILARITY_THRESHOLD = 0.7;
      if (cosim < SIMILARITY_THRESHOLD) {continue;}

      scored.push({
        paragraphId: row.paragraphId,
        sourceText: row.sourceText,
        translatedText: row.translatedText,
        similarity: cosim,
      });
    }

    // 5. Trier par similarité décroissante et retourner les top K
    scored.sort((a, b) => b.similarity - a.similarity);
    return scored.slice(0, topK);
  }

  /**
   * T13 fix : récupère ou construit l'index MiniSearch pour un projet.
   * L'index est mis en cache et réutilisé entre les appels findSimilar().
   * Invalide le cache si de nouveaux embeddings ont été stockés.
   */
  private getOrBuildMiniSearchIndex(projectId: string): {
    index: MiniSearch;
    rows: Array<{
      id: number;
      paragraphId: string;
      embeddingJson: string;
      sourceText: string;
      translatedText: string;
    }>;
  } | null {
    // Vérifier le cache
    const cached = this.miniSearchCache.get(projectId);
    if (cached) {return cached;}

    // Charger tous les embeddings du projet
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

    if (rows.length === 0) {return null;}

    const normalizedRows = rows.map((r, i) => ({
      id: i,
      paragraphId: r.paragraph_id,
      embeddingJson: r.embedding_json,
      sourceText: r.source_text,
      translatedText: r.translated_text ?? "",
    }));

    const miniSearch = new MiniSearch({
      fields: ["source_text"],
      storeFields: ["source_text"],
      searchOptions: { fuzzy: 0.2, prefix: true },
    });
    miniSearch.addAll(
      normalizedRows.map((r) => ({
        id: String(r.id),
        source_text: r.sourceText,
      })),
    );

    const entry = { index: miniSearch, rows: normalizedRows };
    this.miniSearchCache.set(projectId, entry);
    return entry;
  }

  /**
   * T13 fix : invalide le cache MiniSearch pour un projet.
   * Appelé après storeEmbedding/storeEmbeddings/reindex.
   */
  private invalidateMiniSearchCache(projectId?: string): void {
    if (projectId) {
      this.miniSearchCache.delete(projectId);
    } else {
      this.miniSearchCache.clear();
    }
  }

  /**
   * Supprime et recalcule tous les embeddings d'un projet.
   * Utile après un changement de modèle d'embedding.
   *
   * T13 fix : auparavant, reindex() ne faisait que DELETE les embeddings
   * sans les recalculer — laissant le projet sans index vectoriel. Maintenant,
   * après le DELETE, tous les paragraphes traduits du projet sont ré-embeddés
   * en batch (1 appel Ollama /api/embed par chunk de 100 paragraphes).
   *
   * @returns Nombre d'embeddings recalculés
   */
  async reindex(projectId: string): Promise<number> {
    // 1. Supprimer les anciens embeddings du projet
    this.db
      .prepare(
        `DELETE FROM embeddings WHERE chapter_id IN (
         SELECT id FROM chapters WHERE project_id = ?
       )`,
      )
      .run([projectId]);

    // 2. Charger tous les paragraphes traduits du projet
    const paragraphs = this.db
      .prepare(
        `SELECT p.id, p.chapter_id, p.source_text
       FROM paragraphs p
       JOIN chapters c ON p.chapter_id = c.id
       WHERE c.project_id = ? AND p.translated_text IS NOT NULL`,
      )
      .all([projectId]) as Array<{
        id: string;
        chapter_id: string;
        source_text: string;
      }>;

    if (paragraphs.length === 0) {
      logger.info(
        `[RagEngine] reindex: aucun paragraphe traduit pour ${projectId}`,
      );
      return 0;
    }

    // 3. Recalculer les embeddings en batch (chunks de 100 pour éviter les timeouts)
    const BATCH_SIZE = 100;
    let count = 0;
    for (let i = 0; i < paragraphs.length; i += BATCH_SIZE) {
      const batch = paragraphs.slice(i, i + BATCH_SIZE);
      const texts = batch.map((p) => p.source_text);
      try {
        const embeddings = await this.computeEmbeddings(texts);
        const entries = batch.map((p, j) => ({
          chapterId: p.chapter_id,
          paragraphId: p.id,
          embedding: embeddings[j],
        }));
        this.storeEmbeddings(entries);
        count += batch.length;
      } catch (err) {
        logger.warn(
          `[RagEngine] reindex: échec du batch ${i}-${i + batch.length}`,
          err,
        );
      }
    }

    logger.info(
      `[RagEngine] reindex: ${count}/${paragraphs.length} embeddings recalculés pour ${projectId}`,
    );
    return count;
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

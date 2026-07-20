import type { Database } from "node-sqlite3-wasm";
import zlib from "node:zlib";
import type {
  HistorySnapshot,
  Paragraph,
  SnapshotTrigger,
  IncrementalChange,
  IncrementalPayload,
  SnapshotMetadata,
} from "@shared/types/index.js";
import { BaseRepository } from "../base/BaseRepository.js";

/**
 * Seuil de compression : si le JSON du snapshot dépasse 10 Ko,
 * on le compresse avec zlib (SDD §14.3).
 */
const COMPRESSION_THRESHOLD = 10_000;

/** Intervalle pour les snapshots complets : v1, v5, v10, v15... */
const FULL_SNAPSHOT_INTERVAL = 5;

/**
 * WS-1 (clean architecture) : hérite de `BaseRepository<HistorySnapshot>` pour
 * le constructeur et le handle DB. Toutes les méthodes conservent leur SQL
 * spécialisé (JOIN `job_steps` pour `step_score`, snapshots hybrides full/
 * incrémental, compression zlib) — les helpers par défaut de la base ne
 * couvrent pas ces cas. `map()` satisfait l'abstract en déléguant à `mapRow`
 * privé (qui accepte un `versionNumber` optionnel non porté par la signature
 * de la base).
 */
export class HistoryRepository extends BaseRepository<HistorySnapshot> {
  constructor(db: Database) {
    super(db, "history_snapshots");
  }

  /**
   * Crée un nouveau snapshot d'historique avec support hybride (SDD §14.3).
   *
   * - **Snapshots complets** : v1, v5, v10, v15... (tous les 5)
   * - **Snapshots incrémentaux** : versions intermédiaires (stocke seulement
   *   les différences depuis le dernier snapshot complet)
   * - **Compression zlib** : si le JSON > 10 Ko, compression automatique
   *   avec marquage `isCompressed` dans les métadonnées.
   */
  create(snapshot: {
    id: string;
    projectId: string;
    chapterId?: string;
    jobId?: string;
    stepId?: string;
    stage: string;
    paragraphs: Paragraph[];
    triggeredBy: SnapshotTrigger;
  }): void {
    const count = this.getSnapshotCount(
      snapshot.projectId,
      snapshot.chapterId,
    );
    const newVersion = count + 1;
    const isFull =
      newVersion === 1 || newVersion % FULL_SNAPSHOT_INTERVAL === 0;

    let paragraphsJson: string;
    let metadataExtra: Partial<SnapshotMetadata> = {};

    if (isFull) {
      // Stockage complet : tous les paragraphes
      paragraphsJson = JSON.stringify(snapshot.paragraphs);
      metadataExtra = { snapshotType: "full" };
    } else {
      // Stockage incrémental : seulement les changements depuis le dernier complet
      const baseSnapshot = this.getLastFullSnapshot(
        snapshot.projectId,
        snapshot.chapterId,
      );
      if (baseSnapshot) {
        const changes = this.computeIncrementalChanges(
          baseSnapshot.paragraphs,
          snapshot.paragraphs,
        );
        const payload: IncrementalPayload = {
          _type: "incremental",
          baseSnapshotId: baseSnapshot.id,
          changes,
        };
        paragraphsJson = JSON.stringify(payload);
        metadataExtra = { snapshotType: "incremental", baseSnapshotId: baseSnapshot.id };
      } else {
        // Fallback : pas de snapshot complet trouvé, stocker en full
        paragraphsJson = JSON.stringify(snapshot.paragraphs);
        metadataExtra = { snapshotType: "full" };
      }
    }

    // Compression zlib si le JSON dépasse le seuil
    let storedData = paragraphsJson;
    let isCompressed = false;
    if (Buffer.byteLength(paragraphsJson, "utf-8") > COMPRESSION_THRESHOLD) {
      storedData = zlib
        .deflateSync(Buffer.from(paragraphsJson, "utf-8"))
        .toString("base64");
      isCompressed = true;
    }

    const metadataObj: SnapshotMetadata = {
      triggeredBy: snapshot.triggeredBy,
      ...metadataExtra,
      isCompressed,
      versionNumber: newVersion,
    };
    const metadataStr = JSON.stringify(metadataObj);

    this.db
      .prepare(
        `INSERT INTO history_snapshots (id, project_id, chapter_id, job_id, step_id, stage, paragraphs, metadata, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run([
        snapshot.id,
        snapshot.projectId,
        snapshot.chapterId ?? null,
        snapshot.jobId ?? null,
        snapshot.stepId ?? null,
        snapshot.stage,
        storedData,
        metadataStr,
        new Date().toISOString(),
      ]);
  }

  /**
   * Compte le nombre de snapshots existants pour un projet/chapitre.
   * Utilisé pour déterminer le numéro de version.
   */
  private getSnapshotCount(
    projectId: string,
    chapterId?: string,
  ): number {
    let row: { count: number } | undefined;
    if (chapterId) {
      row = this.db
        .prepare(
          "SELECT COUNT(*) AS count FROM history_snapshots WHERE project_id = ? AND chapter_id = ?",
        )
        .get([projectId, chapterId]) as { count: number } | undefined;
    } else {
      row = this.db
        .prepare(
          "SELECT COUNT(*) AS count FROM history_snapshots WHERE project_id = ?",
        )
        .get([projectId]) as { count: number } | undefined;
    }
    return row ? Number(row.count) : 0;
  }

  /**
   * Récupère le dernier snapshot complet pour un projet/chapitre.
   *
   * P1-2 fix : l'ancienne version chargeait TOUS les snapshots du
   * projet/chapitre puis filtrait en JS pour trouver le premier "full" →
   * O(N) rows lus à chaque création de snapshot incrémental, coût croissant
   * avec l'historique. Désormais on filtre en SQL sur la métadonnée
   * `snapshotType` (ou absence du champ = rétrocompatibilité "full") avec
   * LIMIT 1, en s'appuyant sur l'index 018 (project_id, chapter_id, created_at).
   *
   * Le LIKE sur le JSON reste nécessaire car `metadata` est une colonne TEXT
   * sérialisée (pas de JSON1 garanti sur le port wasm). On filtre d'abord par
   * les deux préfixes possibles, puis on re-vérifie la métadonnée exacte en
   * JS sur l'unique ligne retournée.
   */
  private getLastFullSnapshot(
    projectId: string,
    chapterId?: string,
  ): HistorySnapshot | null {
    // P1-2 fix : cf. commentaire de méthode ci-dessus. On utilise deux
    // prepared statements (avec/sans clause chapter) plutôt qu'un array de
    // params construit dynamiquement — plus typé et lisible.
    const fullClause = `
      AND (
        hs.metadata LIKE '%"snapshotType":"full"%'
        OR hs.metadata NOT LIKE '%"snapshotType":%'
      )
      ORDER BY hs.created_at DESC
      LIMIT 1`;
    const row = chapterId
      ? (this.db
          .prepare(
            `SELECT hs.*, js.score AS step_score
             FROM history_snapshots hs
             LEFT JOIN job_steps js ON hs.step_id = js.id
             WHERE hs.project_id = ? AND hs.chapter_id = ? ${fullClause}`,
          )
          .get([projectId, chapterId]) as Record<string, unknown> | undefined)
      : (this.db
          .prepare(
            `SELECT hs.*, js.score AS step_score
             FROM history_snapshots hs
             LEFT JOIN job_steps js ON hs.step_id = js.id
             WHERE hs.project_id = ? ${fullClause}`,
          )
          .get([projectId]) as Record<string, unknown> | undefined);

    if (!row) {return null;}
    const meta = this.parseMetadata(row.metadata);
    const isFull =
      meta.snapshotType === "full" || meta.snapshotType === undefined;
    if (!isFull) {return null;}
    const snapshot = this.mapRow(row);
    snapshot.paragraphs = this.getParagraphsFromRow(row);
    return snapshot;
  }

  /**
   * Calcule les changements incrémentaux entre deux listes de paragraphes.
   * Ne stocke que les paragraphes modifiés.
   */
  private computeIncrementalChanges(
    base: Paragraph[],
    current: Paragraph[],
  ): IncrementalChange[] {
    const changes: IncrementalChange[] = [];
    const maxIndex = Math.max(base.length, current.length);

    for (let i = 0; i < maxIndex; i++) {
      const b = base[i];
      const c = current[i];

      if (!b && c) {
        // Paragraphe ajouté
        changes.push({
          index: c.indexInChapter,
          sourceText: c.sourceText,
          translatedText: c.translatedText,
          status: c.status,
        });
      } else if (b && !c) {
        // Paragraphe supprimé → stocker avec sourceText vide pour marquer la suppression
        changes.push({
          index: b.indexInChapter,
          sourceText: "",
          translatedText: undefined,
          status: "pending",
        });
      } else if (b && c) {
        const changed =
          b.sourceText !== c.sourceText ||
          b.translatedText !== c.translatedText ||
          b.status !== c.status;
        if (changed) {
          changes.push({
            index: c.indexInChapter,
            sourceText: c.sourceText,
            translatedText: c.translatedText,
            status: c.status,
          });
        }
      }
    }

    return changes;
  }

  // ── Méthodes de lecture ──

  /**
   * Liste tous les snapshots pour un projet, triés par date décroissante.
   * Les paragraphes ne sont PAS chargés pour la liste (optimisation).
   * Utiliser `getFullParagraphs()` pour charger les paragraphes d'un snapshot.
   */
  listByProject(projectId: string): HistorySnapshot[] {
    const rows = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
         FROM history_snapshots hs
         LEFT JOIN job_steps js ON hs.step_id = js.id
         WHERE hs.project_id = ?
         ORDER BY hs.created_at DESC`,
      )
      .all([projectId]) as Record<string, unknown>[];
    return this.mapRows(rows);
  }

  /**
   * Liste les snapshots pour un chapitre donné, triés par date décroissante.
   * Les paragraphes ne sont PAS chargés pour la liste (optimisation).
   */
  listByChapter(chapterId: string): HistorySnapshot[] {
    const rows = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
         FROM history_snapshots hs
         LEFT JOIN job_steps js ON hs.step_id = js.id
         WHERE hs.chapter_id = ?
         ORDER BY hs.created_at DESC`,
      )
      .all([chapterId]) as Record<string, unknown>[];
    return this.mapRows(rows);
  }

  /**
   * Récupère un snapshot par son ID.
   * Les paragraphes sont chargés et reconstruits si nécessaire.
   */
  getById(id: string): HistorySnapshot | null {
    const row = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
         FROM history_snapshots hs
         LEFT JOIN job_steps js ON hs.step_id = js.id
         WHERE hs.id = ?`,
      )
      .get([id]) as Record<string, unknown> | undefined;
    if (!row) {return null;}

    const snapshot = this.mapRow(row);
    snapshot.paragraphs = this.getParagraphsFromRow(row);
    return snapshot;
  }

  /**
   * Reconstruit les paragraphes complets pour un snapshot donné.
   * Gère la décompression et la reconstruction incrémentale.
   */
  getFullParagraphs(snapshotId: string): Paragraph[] {
    const row = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
         FROM history_snapshots hs
         LEFT JOIN job_steps js ON hs.step_id = js.id
         WHERE hs.id = ?`,
      )
      .get([snapshotId]) as Record<string, unknown> | undefined;
    if (!row) {return [];}
    return this.getParagraphsFromRow(row);
  }

  /**
   * Récupère les paragraphes actuels les plus récents pour un chapitre.
   */
  getLatest(chapterId: string): HistorySnapshot | null {
    const row = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
         FROM history_snapshots hs
         LEFT JOIN job_steps js ON hs.step_id = js.id
         WHERE hs.chapter_id = ?
         ORDER BY hs.created_at DESC
         LIMIT 1`,
      )
      .get([chapterId]) as Record<string, unknown> | undefined;
    if (!row) {return null;}

    const snapshot = this.mapRow(row);
    snapshot.paragraphs = this.getParagraphsFromRow(row);
    return snapshot;
  }

  // ── Helpers de reconstruction ──

  /**
   * Extrait et décompresse les données de la colonne `paragraphs`.
   * Si le snapshot est incrémental, charge le snapshot de base et applique les changements.
   */
  private getParagraphsFromRow(
    row: Record<string, unknown>,
  ): Paragraph[] {
    const meta = this.parseMetadata(row.metadata);
    const rawData = String(row.paragraphs);
    if (!rawData) {return [];}

    // Décompresser si nécessaire
    const jsonStr = meta.isCompressed
      ? zlib.inflateSync(Buffer.from(rawData, "base64")).toString("utf-8")
      : rawData;

    // Vérifier si c'est un snapshot complet ou incrémental
    if (meta.snapshotType === "incremental" || meta.baseSnapshotId) {
      // Format incrémental
      try {
        const payload = JSON.parse(jsonStr) as IncrementalPayload;
        if (payload._type === "incremental" && payload.baseSnapshotId) {
          return this.applyIncrementalChanges(payload);
        }
      } catch {
        // Fallback : essayer de parser comme tableau
      }
    }

    // Format complet (ou fallback)
    try {
      return JSON.parse(jsonStr) as Paragraph[];
    } catch {
      return [];
    }
  }

  /**
   * Applique les changements incrémentaux sur le snapshot de base.
   */
  private applyIncrementalChanges(payload: IncrementalPayload): Paragraph[] {
    const baseSnapshot = this.getById(payload.baseSnapshotId);
    if (!baseSnapshot) {
      // Snapshot de base introuvable, on ne peut pas reconstruire
      return [];
    }

    const baseParagraphs = baseSnapshot.paragraphs;

    // Performance optimization: Pre-index base paragraphs into a Map for O(1) lookups
    // This reduces the complexity of applying changes from O(N^2) to O(N)
    const paragraphMap = new Map<number, Paragraph>();
    for (const p of baseParagraphs) {
      paragraphMap.set(p.indexInChapter, p);
    }

    for (const change of payload.changes) {
      if (change.sourceText === "") {
        // Suppression
        paragraphMap.delete(change.index);
      } else if (paragraphMap.has(change.index)) {
        // Mise à jour
        const existing = paragraphMap.get(change.index)!;
        paragraphMap.set(change.index, {
          ...existing,
          sourceText: change.sourceText,
          translatedText: change.translatedText,
          status: change.status,
        });
      } else {
        // Ajout
        const baseId = `reconstructed-${payload.baseSnapshotId}-${change.index}`;
        paragraphMap.set(change.index, {
          id: baseId,
          chapterId: baseSnapshot.chapterId ?? "",
          indexInChapter: change.index,
          sourceText: change.sourceText,
          translatedText: change.translatedText,
          status: change.status,
        });
      }
    }

    // Convert map back to array and sort par indexInChapter
    const result = Array.from(paragraphMap.values());
    result.sort((a, b) => a.indexInChapter - b.indexInChapter);
    return result;
  }

  // ── Helpers de mapping ──

  private mapRows(rows: Record<string, unknown>[]): HistorySnapshot[] {
    const total = rows.length;
    return rows.map((row, index) => this.mapRow(row, total - index));
  }

  private mapRow(
    row: Record<string, unknown>,
    versionNumber?: number,
  ): HistorySnapshot {
    const meta = this.parseMetadata(row.metadata);

    const triggeredBy: SnapshotTrigger =
      meta.triggeredBy === "manual" ||
      meta.triggeredBy === "rollback" ||
      meta.triggeredBy === "workflow"
        ? (meta.triggeredBy)
        : "workflow";

    const stepScore = row.step_score;

    // Pour les listes, on ne charge pas les paragraphes (optimisation)
    // Les paragraphes sont vides par défaut, le store les charge via getFullParagraphs
    let paragraphs: Paragraph[] = [];
    // Si le snapshot est complet ET non compressé ET qu'on est pas en mode liste,
    // on charge les paragraphes. Pour les listes bulk, on skip.
    // (détecté par l'absence de versionNumber passé)
    if (versionNumber === undefined && meta.snapshotType !== "incremental") {
      paragraphs = this.getParagraphsFromRow(row);
    }

    const vNumber =
      meta.versionNumber ?? versionNumber;

    return {
      id: String(row.id),
      projectId: String(row.project_id),
      chapterId: row.chapter_id ? String(row.chapter_id) : undefined,
      jobId: row.job_id ? String(row.job_id) : undefined,
      stepId: row.step_id ? String(row.step_id) : undefined,
      stage: String(row.stage),
      paragraphs,
      qualityScore: stepScore != null ? Number(stepScore) : undefined,
      triggeredBy,
      createdAt: String(row.created_at),
      versionNumber: vNumber,
    };
  }

  private parseMetadata(
    rowMetadata: unknown,
  ): SnapshotMetadata {
    if (!rowMetadata) {
      return { triggeredBy: "workflow" };
    }
    try {
      return JSON.parse(String(rowMetadata)) as SnapshotMetadata;
    } catch {
      return { triggeredBy: "workflow" };
    }
  }

  /**
   * Implémentation de l'abstract `map` de BaseRepository.
   * Délègue à `mapRow` privé (qui porte la logique spécialisée snapshots
   * hybrides + step_score JOIN). Version par défaut = undefined → mode liste
   * (paragraphes non chargés).
   */
  protected map(row: Record<string, unknown>): HistorySnapshot {
    return this.mapRow(row);
  }
}

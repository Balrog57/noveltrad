import type { ProjectDatabase } from "../db/connection.js";
import type { AuditEntry } from "@shared/types/index.js";

/** Actions d'audit standardisées */
export const AUDIT_ACTIONS = {
  PROJECT_CREATED: "project:created",
  PROJECT_DELETED: "project:deleted",
  CHAPTER_IMPORTED: "chapter:imported",
  CHAPTER_DELETED: "chapter:deleted",
  WORKFLOW_STARTED: "workflow:started",
  WORKFLOW_COMPLETED: "workflow:completed",
  WORKFLOW_FAILED: "workflow:failed",
  EXPORT_RUN: "export:run",
  SNAPSHOT_MANUAL: "snapshot:manual",
  ROLLBACK_FULL: "rollback:full",
  ROLLBACK_PARTIAL: "rollback:partial",
  LEXICON_IMPORTED: "lexicon:imported",
  LEXICON_EXPORTED: "lexicon:exported",
  TM_IMPORTED: "tm:imported",
  TM_EXPORTED: "tm:exported",
} as const;

export type AuditAction = (typeof AUDIT_ACTIONS)[keyof typeof AUDIT_ACTIONS];

/**
 * Service de journalisation d'audit (SDD §14.6).
 * Enregistre les actions importantes de l'utilisateur dans la table `audit_log`.
 * Chaque entrée stocke l'action, le type d'entité, et des détails JSON.
 */
export class AuditService {
  constructor(private db: ProjectDatabase) {
    this.ensureTable();
  }

  /**
   * Crée la table `audit_log` si elle n'existe pas.
   */
  private ensureTable(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
        action TEXT NOT NULL,
        entity_type TEXT,
        entity_id TEXT,
        details TEXT,
        created_at TEXT NOT NULL
      )
    `);
    this.db.exec(
      "CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_log(project_id)",
    );
    this.db.exec(
      "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
    );
  }

  /**
   * Enregistre une entrée dans le journal d'audit.
   *
   * @param params Action à enregistrer
   * @param params.projectId ID du projet concerné (optionnel)
   * @param params.action Nom de l'action (utiliser AUDIT_ACTIONS)
   * @param params.entityType Type d'entité (chapter, job, lexicon, etc.)
   * @param params.entityId ID de l'entité concernée (optionnel)
   * @param params.details Métadonnées additionnelles (optionnel)
   */
  log(params: {
    projectId?: string;
    action: string;
    entityType?: string;
    entityId?: string;
    details?: Record<string, unknown>;
  }): void {
    this.db
      .prepare(
        `INSERT INTO audit_log (id, project_id, action, entity_type, entity_id, details, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .run([
        crypto.randomUUID(),
        params.projectId ?? null,
        params.action,
        params.entityType ?? null,
        params.entityId ?? null,
        params.details ? JSON.stringify(params.details) : null,
        new Date().toISOString(),
      ]);
  }

  /**
   * Liste les entrées d'audit pour un projet, triées par date décroissante.
   *
   * @param projectId ID du projet
   * @param limit Nombre maximum d'entrées (défaut 100)
   * @returns Liste des entrées d'audit
   */
  list(projectId: string, limit = 100): AuditEntry[] {
    const rows = this.db
      .prepare(
        `SELECT * FROM audit_log
         WHERE project_id = ?
         ORDER BY created_at DESC
         LIMIT ?`,
      )
      .all([projectId, limit]) as Record<string, unknown>[];

    return rows.map((r) => this.mapRow(r));
  }

  /**
   * Liste toutes les entrées d'audit (sans filtre projet), triées par date décroissante.
   *
   * @param limit Nombre maximum d'entrées (défaut 100)
   * @returns Liste des entrées d'audit
   */
  listAll(limit = 100): AuditEntry[] {
    const rows = this.db
      .prepare("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?")
      .all([limit]) as Record<string, unknown>[];

    return rows.map((r) => this.mapRow(r));
  }

  /**
   * Convertit une ligne SQL en objet AuditEntry.
   */
  private mapRow(row: Record<string, unknown>): AuditEntry {
    let details: Record<string, unknown> | undefined;
    if (row.details) {
      try {
        details = JSON.parse(String(row.details)) as Record<string, unknown>;
      } catch {
        details = undefined;
      }
    }

    return {
      id: String(row.id),
      projectId: row.project_id ? String(row.project_id) : undefined,
      action: String(row.action),
      entityType: row.entity_type ? String(row.entity_type) : undefined,
      entityId: row.entity_id ? String(row.entity_id) : undefined,
      details,
      createdAt: String(row.created_at),
    };
  }
}

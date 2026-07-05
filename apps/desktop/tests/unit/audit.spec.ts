import { describe, it, expect, beforeEach } from "vitest";
import { AuditService, AUDIT_ACTIONS } from "../../src/main/services/AuditService";

// ---------------------------------------------------------------------------
// Mock SQLite DB (same pattern as tmx.spec.ts and ai-cache.spec.ts)
// ---------------------------------------------------------------------------

interface AuditRow {
  id: string;
  project_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: string | null;
  created_at: string;
}

class MockAuditDb {
  private rows: Map<string, AuditRow> = new Map();
  execCalls: string[] = [];

  exec(sql: string): void {
    this.execCalls.push(sql);
  }

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    run: (params: unknown[]) => void;
    all: (params: unknown[]) => unknown[];
  } {
    return {
      get: (_params: unknown[]): unknown => {
        return undefined;
      },
      run: (params: unknown[]): void => {
        if (sql.includes("INSERT INTO audit_log")) {
          const row: AuditRow = {
            id: params[0] as string,
            project_id: params[1] as string | null,
            action: params[2] as string,
            entity_type: params[3] as string | null,
            entity_id: params[4] as string | null,
            details: params[5] as string | null,
            created_at: params[6] as string,
          };
          this.rows.set(row.id, row);
        }
      },
      all: (params: unknown[]): unknown[] => {
        // SELECT * FROM audit_log WHERE project_id = ? ORDER BY created_at DESC LIMIT ?
        if (sql.includes("WHERE project_id = ?")) {
          const projectId = params[0] as string;
          const limit = params[1] as number;
          const filtered: AuditRow[] = [];
          for (const row of this.rows.values()) {
            if (row.project_id === projectId) {
              filtered.push(row);
            }
          }
          filtered.sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          );
          return filtered.slice(0, limit);
        }
        // SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?
        if (sql.includes("ORDER BY created_at DESC LIMIT ?")) {
          const limit = params[0] as number;
          const all = Array.from(this.rows.values());
          all.sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          );
          return all.slice(0, limit);
        }
        return [];
      },
    };
  }

  /** Helper to inspect stored rows */
  getAllRows(): AuditRow[] {
    return Array.from(this.rows.values());
  }

  /** Helper to inject a raw row (for edge case testing) */
  injectRawRow(row: AuditRow): void {
    this.rows.set(row.id, row);
  }

  /** Helper to clear all rows */
  clear(): void {
    this.rows.clear();
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AuditService", () => {
  let db: MockAuditDb;
  let audit: AuditService;

  beforeEach(() => {
    db = new MockAuditDb();
    audit = new AuditService(db as unknown as import("node-sqlite3-wasm").Database);
  });

  describe("constructor / ensureTable", () => {
    it("devrait créer la table audit_log et ses index au constructeur", () => {
      const ddlCalls = db.execCalls;
      expect(ddlCalls.length).toBeGreaterThanOrEqual(3);
      expect(ddlCalls.some((s) => s.includes("CREATE TABLE IF NOT EXISTS audit_log"))).toBe(true);
      expect(ddlCalls.some((s) => s.includes("CREATE INDEX IF NOT EXISTS idx_audit_project"))).toBe(true);
      expect(ddlCalls.some((s) => s.includes("CREATE INDEX IF NOT EXISTS idx_audit_action"))).toBe(true);
    });
  });

  describe("log()", () => {
    it("devrait insérer une entrée avec tous les champs", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.PROJECT_CREATED,
        entityType: "project",
        entityId: "proj-1",
        details: { name: "Mon Roman", chapters: 12 },
      });

      const rows = db.getAllRows();
      expect(rows).toHaveLength(1);
      expect(rows[0].action).toBe("project:created");
      expect(rows[0].project_id).toBe("proj-1");
      expect(rows[0].entity_type).toBe("project");
      expect(rows[0].entity_id).toBe("proj-1");
      expect(rows[0].details).toBe('{"name":"Mon Roman","chapters":12}');
      expect(rows[0].id).toBeTruthy();
      expect(rows[0].created_at).toBeTruthy();
    });

    it("devrait gérer les champs optionnels absents", () => {
      audit.log({
        action: AUDIT_ACTIONS.WORKFLOW_STARTED,
      });

      const rows = db.getAllRows();
      expect(rows).toHaveLength(1);
      expect(rows[0].action).toBe("workflow:started");
      expect(rows[0].project_id).toBeNull();
      expect(rows[0].entity_type).toBeNull();
      expect(rows[0].entity_id).toBeNull();
      expect(rows[0].details).toBeNull();
    });

    it("devrait enregistrer des détails nullables", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.WORKFLOW_STARTED,
        details: undefined,
      });

      const rows = db.getAllRows();
      expect(rows[0].details).toBeNull();
    });

    it("devrait accepter différents types d'actions AUDIT_ACTIONS", () => {
      const actions = [
        AUDIT_ACTIONS.PROJECT_CREATED,
        AUDIT_ACTIONS.CHAPTER_IMPORTED,
        AUDIT_ACTIONS.WORKFLOW_STARTED,
        AUDIT_ACTIONS.WORKFLOW_COMPLETED,
        AUDIT_ACTIONS.WORKFLOW_FAILED,
        AUDIT_ACTIONS.EXPORT_RUN,
        AUDIT_ACTIONS.SNAPSHOT_MANUAL,
        AUDIT_ACTIONS.ROLLBACK_FULL,
        AUDIT_ACTIONS.LEXICON_IMPORTED,
        AUDIT_ACTIONS.TM_EXPORTED,
      ];

      for (const action of actions) {
        audit.log({ action });
      }

      expect(db.getAllRows()).toHaveLength(actions.length);
      const savedActions = db.getAllRows().map((r) => r.action);
      for (const a of actions) {
        expect(savedActions).toContain(a);
      }
    });

    it("devrait générer un ID unique pour chaque entrée", () => {
      audit.log({ action: AUDIT_ACTIONS.PROJECT_CREATED });
      audit.log({ action: AUDIT_ACTIONS.CHAPTER_IMPORTED });
      audit.log({ action: AUDIT_ACTIONS.WORKFLOW_STARTED });

      const rows = db.getAllRows();
      const ids = new Set(rows.map((r) => r.id));
      expect(ids.size).toBe(3);
    });
  });

  describe("list()", () => {
    it("devrait filtrer les entrées par projectId", () => {
      audit.log({ projectId: "proj-1", action: "project:created" });
      audit.log({ projectId: "proj-1", action: "chapter:imported" });
      audit.log({ projectId: "proj-2", action: "project:created" });

      const entriesProj1 = audit.list("proj-1");
      expect(entriesProj1).toHaveLength(2);

      const entriesProj2 = audit.list("proj-2");
      expect(entriesProj2).toHaveLength(1);
    });

    it("devrait retourner les entrées les plus récentes en premier", () => {
      // Use fake timers to control created_at order
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2026-07-01T10:00:00.000Z"));
      audit.log({ projectId: "proj-1", action: "workflow:started" });

      vi.setSystemTime(new Date("2026-07-01T11:00:00.000Z"));
      audit.log({ projectId: "proj-1", action: "workflow:completed" });

      vi.setSystemTime(new Date("2026-07-01T12:00:00.000Z"));
      audit.log({ projectId: "proj-1", action: "export:run" });

      vi.useRealTimers();

      const entries = audit.list("proj-1");
      expect(entries).toHaveLength(3);
      expect(entries[0].action).toBe("export:run");
      expect(entries[1].action).toBe("workflow:completed");
      expect(entries[2].action).toBe("workflow:started");
    });

    it("devrait respecter la limite", () => {
      for (let i = 1; i <= 10; i++) {
        audit.log({ projectId: "proj-1", action: `action:${i}` });
      }

      const entries = audit.list("proj-1", 3);
      expect(entries).toHaveLength(3);
    });

    it("devrait retourner un tableau vide si aucune entrée pour le projet", () => {
      const entries = audit.list("proj-inexistant");
      expect(entries).toHaveLength(0);
    });
  });

  describe("listAll()", () => {
    it("devrait retourner toutes les entrées sans filtre projet", () => {
      audit.log({ projectId: "proj-1", action: "project:created" });
      audit.log({ projectId: "proj-2", action: "project:created" });
      audit.log({ projectId: "proj-1", action: "chapter:imported" });

      const entries = audit.listAll();
      expect(entries).toHaveLength(3);
    });

    it("devrait respecter la limite par défaut de 100", () => {
      for (let i = 0; i < 150; i++) {
        audit.log({ action: `action:${i}` });
      }

      const entries = audit.listAll();
      expect(entries).toHaveLength(100);
    });

    it("devrait retourner un tableau vide si aucune entrée", () => {
      const entries = audit.listAll();
      expect(entries).toHaveLength(0);
    });
  });

  describe("mapRow (via list)", () => {
    it("devrait parser correctement les champs en AuditEntry", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.PROJECT_CREATED,
        entityType: "project",
        entityId: "proj-1",
        details: { test: true },
      });

      const entries = audit.list("proj-1");
      const entry = entries[0];

      expect(entry.id).toBeTruthy();
      expect(typeof entry.id).toBe("string");
      expect(entry.projectId).toBe("proj-1");
      expect(entry.action).toBe("project:created");
      expect(entry.entityType).toBe("project");
      expect(entry.entityId).toBe("proj-1");
      expect(entry.details).toEqual({ test: true });
      expect(entry.createdAt).toBeTruthy();
      expect(typeof entry.createdAt).toBe("string");
    });

    it("devrait retourner des champs optionnels undefined si absents", () => {
      audit.log({ action: AUDIT_ACTIONS.WORKFLOW_STARTED });

      const entries = audit.listAll();
      expect(entries[0].projectId).toBeUndefined();
      expect(entries[0].entityType).toBeUndefined();
      expect(entries[0].entityId).toBeUndefined();
      expect(entries[0].details).toBeUndefined();
    });

    it("devrait gérer un JSON invalide dans le champ details (catch mapRow)", () => {
      // Inject raw row with invalid JSON to trigger the try/catch in mapRow
      db.injectRawRow({
        id: "bad-json-1",
        project_id: "proj-1",
        action: "project:created",
        entity_type: "project",
        entity_id: "proj-1",
        details: "pas du json valide{", // Invalid JSON
        created_at: "2026-07-01T12:00:00.000Z",
      });

      const entries = audit.listAll();
      expect(entries).toHaveLength(1);
      expect(entries[0].action).toBe("project:created");
      expect(entries[0].details).toBeUndefined(); // Fallback to undefined on parse error
    });
  });
});

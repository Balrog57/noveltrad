import { describe, it, expect, beforeEach, vi } from "vitest";
import type { AuditEntry } from "@shared/types/index.js";

// ── Mock AuditService ──

class MockAuditService {
  private entries: AuditEntry[] = [];

  log(params: {
    projectId?: string;
    action: string;
    entityType?: string;
    entityId?: string;
    details?: Record<string, unknown>;
  }): void {
    this.entries.push({
      id: `audit-${this.entries.length + 1}`,
      projectId: params.projectId,
      action: params.action,
      entityType: params.entityType,
      entityId: params.entityId,
      details: params.details,
      createdAt: new Date().toISOString(),
    });
  }

  list(projectId: string, limit = 100): AuditEntry[] {
    return this.entries
      .filter((e) => e.projectId === projectId)
      .slice(0, limit)
      .reverse(); // latest first
  }

  listAll(limit = 100): AuditEntry[] {
    return [...this.entries]
      .reverse()
      .slice(0, limit);
  }

  clear(): void {
    this.entries = [];
  }

  get count(): number {
    return this.entries.length;
  }
}

// ── Types d'actions d'audit ──

const AUDIT_ACTIONS = {
  PROJECT_CREATED: "project:created",
  CHAPTER_IMPORTED: "chapter:imported",
  WORKFLOW_STARTED: "workflow:started",
  EXPORT_RUN: "export:run",
  ROLLBACK_FULL: "rollback:full",
  ROLLBACK_PARTIAL: "rollback:partial",
  SNAPSHOT_MANUAL: "snapshot:manual",
} as const;

// ── Tests ──

describe("AuditService", () => {
  let audit: MockAuditService;

  beforeEach(() => {
    audit = new MockAuditService();
  });

  describe("log()", () => {
    it("devrait enregistrer une action avec projet", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.PROJECT_CREATED,
        entityType: "project",
        entityId: "proj-1",
        details: { name: "Mon Roman" },
      });

      expect(audit.count).toBe(1);
      const entries = audit.list("proj-1");
      expect(entries).toHaveLength(1);
      expect(entries[0].action).toBe("project:created");
      expect(entries[0].entityType).toBe("project");
      expect(entries[0].details?.name).toBe("Mon Roman");
    });

    it("devrait enregistrer une action sans entité", () => {
      audit.log({
        action: AUDIT_ACTIONS.WORKFLOW_STARTED,
        details: { model: "qwen3.5:9b" },
      });

      expect(audit.count).toBe(1);
      const entry = audit.listAll()[0];
      expect(entry.action).toBe("workflow:started");
      expect(entry.projectId).toBeUndefined();
      expect(entry.entityType).toBeUndefined();
    });

    it("devrait enregistrer un import de chapitre", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.CHAPTER_IMPORTED,
        entityType: "chapter",
        entityId: "ch-5",
        details: { title: "Chapitre 5", sourceFormat: "docx" },
      });

      const entries = audit.list("proj-1");
      expect(entries).toHaveLength(1);
      expect(entries[0].entityId).toBe("ch-5");
      expect(entries[0].details?.title).toBe("Chapitre 5");
      expect(entries[0].details?.sourceFormat).toBe("docx");
    });

    it("devrait enregistrer un export", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.EXPORT_RUN,
        entityType: "chapter",
        entityId: "ch-3",
        details: { format: "epub", fileSize: 102400 },
      });

      const entries = audit.list("proj-1");
      expect(entries).toHaveLength(1);
      expect(entries[0].action).toBe("export:run");
    });

    it("devrait enregistrer un rollback complet", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.ROLLBACK_FULL,
        entityType: "chapter",
        entityId: "ch-1",
        details: {
          sourceSnapshotId: "snap-5",
          restoredVersion: 5,
          paragraphCount: 12,
        },
      });

      const entries = audit.list("proj-1");
      expect(entries).toHaveLength(1);
      expect(entries[0].action).toBe("rollback:full");
      expect(entries[0].details?.restoredVersion).toBe(5);
      expect(entries[0].details?.paragraphCount).toBe(12);
    });

    it("devrait enregistrer un rollback partiel", () => {
      audit.log({
        projectId: "proj-1",
        action: AUDIT_ACTIONS.ROLLBACK_PARTIAL,
        entityType: "chapter",
        entityId: "ch-1",
        details: {
          sourceSnapshotId: "snap-3",
          paragraphCount: 3,
          paragraphIds: ["p1", "p2", "p3"],
        },
      });

      const entries = audit.list("proj-1");
      expect(entries).toHaveLength(1);
      expect(entries[0].action).toBe("rollback:partial");
      expect(entries[0].details?.paragraphCount).toBe(3);
      expect((entries[0].details?.paragraphIds as string[])).toHaveLength(3);
    });
  });

  describe("list()", () => {
    it("devrait lister les entrées par projet", () => {
      audit.log({ projectId: "proj-1", action: "project:created" });
      audit.log({ projectId: "proj-1", action: "chapter:imported" });
      audit.log({ projectId: "proj-2", action: "project:created" });

      const entriesProj1 = audit.list("proj-1");
      expect(entriesProj1).toHaveLength(2);

      const entriesProj2 = audit.list("proj-2");
      expect(entriesProj2).toHaveLength(1);
    });

    it("devrait retourner les entrées les plus récentes en premier", () => {
      audit.log({
        projectId: "proj-1",
        action: "workflow:started",
      });
      audit.log({
        projectId: "proj-1",
        action: "workflow:completed",
      });

      const entries = audit.list("proj-1");
      // Le MockAuditService.list() inverse l'ordre, donc le dernier ajouté est premier
      expect(entries[0].action).toBe("workflow:completed");
      expect(entries[1].action).toBe("workflow:started");
    });

    it("devrait respecter la limite", () => {
      for (let i = 1; i <= 10; i++) {
        audit.log({
          projectId: "proj-1",
          action: `action:${i}`,
        });
      }

      const entries = audit.list("proj-1", 3);
      expect(entries).toHaveLength(3);
    });
  });

  describe("listAll()", () => {
    it("devrait lister toutes les entrées sans filtre projet", () => {
      audit.log({ projectId: "proj-1", action: "project:created" });
      audit.log({ projectId: "proj-2", action: "project:created" });
      audit.log({ action: "system:startup" });

      const entries = audit.listAll();
      expect(entries).toHaveLength(3);
    });
  });

  describe("AuditEntry type", () => {
    it("devrait valider la structure d'une entrée d'audit complète", () => {
      const entry: AuditEntry = {
        id: "audit-1",
        projectId: "proj-1",
        action: "project:created",
        entityType: "project",
        entityId: "proj-1",
        details: { name: "Mon Roman" },
        createdAt: "2026-07-01T12:00:00.000Z",
      };

      expect(entry.id).toBe("audit-1");
      expect(entry.action).toMatch(/^[a-z]+:[a-z]+$/);
      expect(entry.createdAt).toBeDefined();
    });

    it("devrait accepter une entrée sans projet ni entité", () => {
      const entry: AuditEntry = {
        id: "audit-2",
        action: "system:startup",
        createdAt: "2026-07-01T12:00:00.000Z",
      };

      expect(entry.projectId).toBeUndefined();
      expect(entry.entityType).toBeUndefined();
      expect(entry.details).toBeUndefined();
    });

    it("devrait accepter des détails nullables", () => {
      const entry: AuditEntry = {
        id: "audit-3",
        projectId: "proj-1",
        action: "snapshot:manual",
        createdAt: "2026-07-01T12:00:00.000Z",
      };

      expect(entry.details).toBeUndefined();
      // Le type AuditEntry permet details optionnel
      const testEntry: AuditEntry = {
        ...entry,
        details: undefined,
      };
      expect(testEntry.details).toBeUndefined();
    });
  });
});

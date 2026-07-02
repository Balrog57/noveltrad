/**
 * Tests de validation Zod pour les handlers IPC (SDD §16.3)
 *
 * Teste les schémas de validation directement, en répliquant ceux
 * définis dans les fichiers handlers.
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// ── Schémas (répliqués depuis workflow.ts) ─────────────────────────────

const projectPathSchema = z.string().min(1);
const chapterIdSchema = z.string().min(1).optional();
const jobIdSchema = z.string().min(1);
const stepIdSchema = z.string().min(1);
const chapterIdsSchema = z.array(z.string().min(1)).min(1);

const workflowStageSchema = z.enum([
  "split",
  "pre_translate",
  "translate",
  "consistency",
  "lexicon",
  "grammar",
  "style",
  "polish",
  "qa",
  "export",
]);

const jobSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  chapterId: z.string().optional(),
  chapterIds: z.array(z.string()).optional(),
  type: z.enum(["single", "batch"]),
  status: z.enum([
    "pending",
    "running",
    "paused",
    "completed",
    "failed",
    "cancelled",
  ]),
  startedAt: z.string().optional(),
  finishedAt: z.string().optional(),
  errorMessage: z.string().optional(),
  options: z.object({}).passthrough().optional(),
  metadata: z.record(z.unknown()).optional(),
  createdAt: z.string(),
});

// ── Schémas (répliqués depuis ollama.ts) ───────────────────────────────

const modelNameSchema = z.string().min(1);

// ── Schémas (répliqués depuis update.ts) ───────────────────────────────

const channelSchema = z.enum(["latest", "beta", "alpha"]);

// ── Schémas (répliqués depuis settings.ts) ─────────────────────────────

const settingsKeySchema = z.string().min(1);

// ── Tests Workflow ─────────────────────────────────────────────────────

describe("IPC validation - Workflow (SDD §16.3)", () => {
  describe("workflow:start", () => {
    const schema = z.object({
      projectPath: projectPathSchema,
      chapterId: chapterIdSchema,
    });

    it("accepte projectPath valide", () => {
      const r = schema.parse({ projectPath: "/project/test" });
      expect(r.projectPath).toBe("/project/test");
      expect(r.chapterId).toBeUndefined();
    });

    it("accepte projectPath + chapterId", () => {
      const r = schema.parse({ projectPath: "/project/test", chapterId: "ch1" });
      expect(r.chapterId).toBe("ch1");
    });

    it("rejette projectPath vide", () => {
      expect(() => schema.parse({ projectPath: "" })).toThrow();
    });

    it("rejette projectPath null", () => {
      expect(() => schema.parse({ projectPath: null })).toThrow();
    });

    it("rejette projectPath number", () => {
      expect(() => schema.parse({ projectPath: 123 })).toThrow();
    });
  });

  describe("workflow:start-batch", () => {
    const schema = z.object({
      projectPath: projectPathSchema,
      chapterIds: chapterIdsSchema,
    });

    it("accepte projectPath + chapterIds", () => {
      const r = schema.parse({ projectPath: "/project", chapterIds: ["ch1", "ch2"] });
      expect(r.chapterIds).toHaveLength(2);
    });

    it("rejette chapterIds vide", () => {
      expect(() => schema.parse({ projectPath: "/project", chapterIds: [] })).toThrow();
    });

    it("rejette projectPath null", () => {
      expect(() => schema.parse({ projectPath: null, chapterIds: ["ch1"] })).toThrow();
    });
  });

  describe("workflow:pause / resume / cancel", () => {
    const schema = z.object({ jobId: jobIdSchema });

    it("accepte jobId valide", () => {
      expect(schema.parse({ jobId: "job-1" })).toEqual({ jobId: "job-1" });
    });

    it("rejette jobId vide", () => {
      expect(() => schema.parse({ jobId: "" })).toThrow();
    });

    it("rejette jobId null", () => {
      expect(() => schema.parse({ jobId: null })).toThrow();
    });

    it("rejette jobId undefined", () => {
      expect(() => schema.parse({})).toThrow();
    });
  });

  describe("workflow:retry-step", () => {
    const schema = z.object({ jobId: jobIdSchema, stepId: stepIdSchema });

    it("accepte jobId + stepId valides", () => {
      const r = schema.parse({ jobId: "j1", stepId: "s1" });
      expect(r.jobId).toBe("j1");
      expect(r.stepId).toBe("s1");
    });

    it("rejette stepId vide", () => {
      expect(() => schema.parse({ jobId: "j1", stepId: "" })).toThrow();
    });
  });

  describe("workflow:retry-from", () => {
    const schema = z.object({ jobId: jobIdSchema, stage: workflowStageSchema });

    it("accepte un stage valide", () => {
      const r = schema.parse({ jobId: "j1", stage: "translate" });
      expect(r.stage).toBe("translate");
    });

    it("rejette un stage invalide", () => {
      expect(() => schema.parse({ jobId: "j1", stage: "invalid" })).toThrow();
    });

    it("rejette un stage vide", () => {
      expect(() => schema.parse({ jobId: "j1", stage: "" })).toThrow();
    });
  });

  describe("workflow:list / list-active", () => {
    const schema = z.object({ projectPath: projectPathSchema });

    it("accepte projectPath valide", () => {
      const r = schema.parse({ projectPath: "/project" });
      expect(r.projectPath).toBe("/project");
    });

    it("rejette projectPath vide", () => {
      expect(() => schema.parse({ projectPath: "" })).toThrow();
    });
  });

  describe("workflow:resume-batch", () => {
    const schema = z.object({ projectPath: projectPathSchema, job: jobSchema });

    it("accepte un job valide", () => {
      const r = schema.parse({
        projectPath: "/project",
        job: {
          id: "j1",
          projectId: "p1",
          type: "batch",
          status: "paused",
          createdAt: "2024-01-01",
        },
      });
      expect(r.job.id).toBe("j1");
    });

    it("rejette un job mal formé (sans id)", () => {
      expect(() =>
        schema.parse({
          projectPath: "/project",
          job: { type: "batch", status: "paused" },
        }),
      ).toThrow();
    });

    it("rejette un job avec status invalide", () => {
      expect(() =>
        schema.parse({
          projectPath: "/project",
          job: {
            id: "j1",
            projectId: "p1",
            type: "batch",
            status: "invalid_status",
            createdAt: "2024-01-01",
          },
        }),
      ).toThrow();
    });
  });
});

// ── Tests Ollama ───────────────────────────────────────────────────────

describe("IPC validation - Ollama (SDD §16.3)", () => {
  describe("ollama:pull-model", () => {
    const schema = z.object({ name: modelNameSchema });

    it("accepte un nom valide", () => {
      const r = schema.parse({ name: "llama3" });
      expect(r.name).toBe("llama3");
    });

    it("rejette un nom vide", () => {
      expect(() => schema.parse({ name: "" })).toThrow();
    });

    it("rejette un nom null", () => {
      expect(() => schema.parse({ name: null })).toThrow();
    });
  });
});

// ── Tests Update ───────────────────────────────────────────────────────

describe("IPC validation - Update (SDD §16.3)", () => {
  describe("update:set-channel", () => {
    it("accepte latest", () => {
      expect(channelSchema.parse("latest")).toBe("latest");
    });

    it("accepte beta", () => {
      expect(channelSchema.parse("beta")).toBe("beta");
    });

    it("accepte alpha", () => {
      expect(channelSchema.parse("alpha")).toBe("alpha");
    });

    it("rejette un canal invalide", () => {
      expect(() => channelSchema.parse("invalid")).toThrow();
    });

    it("rejette null", () => {
      expect(() => channelSchema.parse(null)).toThrow();
    });

    it("rejette undefined", () => {
      expect(() => channelSchema.parse(undefined)).toThrow();
    });
  });
});

// ── Tests Settings ─────────────────────────────────────────────────────

describe("IPC validation - Settings (SDD §16.3)", () => {
  describe("settings:set", () => {
    const schema = z.object({ key: settingsKeySchema, value: z.unknown() });

    it("accepte key + value valides", () => {
      const r = schema.parse({ key: "theme", value: "dark" });
      expect(r.key).toBe("theme");
      expect(r.value).toBe("dark");
    });

    it("rejette key vide", () => {
      expect(() => schema.parse({ key: "", value: "dark" })).toThrow();
    });

    it("rejette key null", () => {
      expect(() => schema.parse({ key: null, value: "dark" })).toThrow();
    });

    it("accepte value null", () => {
      const r = schema.parse({ key: "theme", value: null });
      expect(r.value).toBeNull();
    });
  });

  describe("settings:get", () => {
    const schema = z.object({ key: settingsKeySchema.optional() });

    it("accepte sans key", () => {
      const r = schema.parse({});
      expect(r.key).toBeUndefined();
    });

    it("accepte avec key valide", () => {
      const r = schema.parse({ key: "theme" });
      expect(r.key).toBe("theme");
    });
  });
});

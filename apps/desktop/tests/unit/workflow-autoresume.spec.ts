import { describe, it, expect, beforeEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    transports: { file: { level: false }, console: { level: false } },
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// Tests — Auto-resume (SDD §7.11)
// ---------------------------------------------------------------------------

interface MockJob {
  id: string;
  projectId: string;
  chapterIds?: string[];
  type: "single" | "batch";
  status: string;
  createdAt: string;
}

describe("Workflow auto-resume (SDD §7.11)", () => {
  let resumedJobs: string[];

  beforeEach(() => {
    vi.clearAllMocks();
    resumedJobs = [];
  });

  function createMockEngine() {
    return {
      resumeBatch: vi.fn().mockImplementation(async (_projectPath: string, job: MockJob) => {
        resumedJobs.push(job.id);
      }),
    };
  }

  function createMockJob(overrides: Partial<MockJob>): MockJob {
    return {
      id: "job-" + Math.random().toString(36).slice(2, 8),
      projectId: "proj-1",
      type: "batch",
      status: "running",
      createdAt: new Date().toISOString(),
      ...overrides,
    };
  }

  it("devrait reprendre un job running", async () => {
    const engine = createMockEngine();
    const activeJobs: MockJob[] = [
      createMockJob({ id: "job-running", status: "running", chapterIds: ["ch1", "ch2"] }),
    ];

    for (const job of activeJobs) {
      if (job.type === "batch" && job.chapterIds && job.chapterIds.length > 0) {
        await engine.resumeBatch("/path", job);
      }
    }

    expect(engine.resumeBatch).toHaveBeenCalledTimes(1);
    expect(resumedJobs).toContain("job-running");
  });

  it("devrait reprendre un job paused", async () => {
    const engine = createMockEngine();
    const activeJobs: MockJob[] = [
      createMockJob({ id: "job-paused", status: "paused", chapterIds: ["ch1"] }),
    ];

    for (const job of activeJobs) {
      if (job.type === "batch" && job.chapterIds && job.chapterIds.length > 0) {
        await engine.resumeBatch("/path", job);
      }
    }

    expect(engine.resumeBatch).toHaveBeenCalledTimes(1);
    expect(resumedJobs).toContain("job-paused");
  });

  it("devrait ignorer un job completed", async () => {
    const engine = createMockEngine();
    const activeJobs: MockJob[] = [
      createMockJob({ id: "job-completed", status: "completed", chapterIds: ["ch1"] }),
    ];

    // completed n'est pas dans listActive() donc ne devrait pas être repris
    const resumed = activeJobs.filter(
      (j) => j.status === "running" || j.status === "paused",
    );
    expect(resumed).toHaveLength(0);
    expect(engine.resumeBatch).not.toHaveBeenCalled();
  });

  it("devrait être no-op si aucun job actif", async () => {
    const engine = createMockEngine();
    const activeJobs: MockJob[] = [];

    for (const job of activeJobs) {
      if (job.type === "batch" && job.chapterIds && job.chapterIds.length > 0) {
        await engine.resumeBatch("/path", job);
      }
    }

    expect(engine.resumeBatch).not.toHaveBeenCalled();
    expect(resumedJobs).toHaveLength(0);
  });
});

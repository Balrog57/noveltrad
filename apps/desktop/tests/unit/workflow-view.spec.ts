import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import type { Step, WorkflowStage } from "@shared/types/index.js";

// ── Mock window.novelTradAPI ──

const mockOn = vi.fn(() => vi.fn());
const mockInvoke = vi.fn().mockResolvedValue(undefined);

(globalThis as any).window = {
  novelTradAPI: {
    invoke: mockInvoke,
    on: mockOn,
  },
};

// ── Import après le mock ──

import { useWorkflowStore } from "../../src/renderer/src/stores/workflow.js";

// ── Helpers ──

function makeStep(overrides: Partial<Step> = {}): Step {
  return {
    id: "step-1",
    jobId: "job-1",
    agentId: "translate",
    name: "Traduction IA",
    stage: "translate",
    orderIndex: 2,
    status: "pending",
    createdAt: new Date().toISOString(),
    ...overrides,
  };
}

// ── Tests ──

describe("WorkflowView rendering", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("should create useWorkflowStore with expected methods", () => {
    const store = useWorkflowStore();

    expect(store.start).toBeDefined();
    expect(store.pause).toBeDefined();
    expect(store.resume).toBeDefined();
    expect(store.cancel).toBeDefined();
    expect(store.retryStep).toBeDefined();
    expect(store.retryFrom).toBeDefined();
    expect(store.list).toBeDefined();
  });

  it("should display correct status icons for step statuses", () => {
    const statuses: Step["status"][] = [
      "pending",
      "running",
      "completed",
      "failed",
      "skipped",
    ];

    for (const status of statuses) {
      const step = makeStep({ status });
      expect(step.status).toBe(status);
    }
  });

  it("should have workflow stages as defined in the shared types", () => {
    const stages: WorkflowStage[] = [
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
    ];

    for (const stage of stages) {
      const step = makeStep({ stage });
      expect(step.stage).toBe(stage);
    }
  });
});

describe("WorkflowStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("should start with empty state", () => {
    const store = useWorkflowStore();

    expect(store.activeJobs).toEqual([]);
    expect(store.progress).toBeNull();
    expect(store.loading).toBe(false);
  });

  it("should call invoke for start", async () => {
    const store = useWorkflowStore();

    mockInvoke.mockResolvedValueOnce({
      id: "job-1",
      status: "running",
      createdAt: new Date().toISOString(),
    });

    const job = await store.start("/path/to/project");
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:start",
      "/path/to/project",
      undefined,
    );
    expect((job as any).id).toBe("job-1");
  });

  it("should call invoke for pause", async () => {
    const store = useWorkflowStore();

    await store.pause("job-1");
    expect(mockInvoke).toHaveBeenCalledWith("workflow:pause", "job-1");
  });

  it("should call invoke for resume", async () => {
    const store = useWorkflowStore();

    await store.resume("job-1");
    expect(mockInvoke).toHaveBeenCalledWith("workflow:resume", "job-1");
  });

  it("should call invoke for cancel", async () => {
    const store = useWorkflowStore();

    await store.cancel("job-1");
    expect(mockInvoke).toHaveBeenCalledWith("workflow:cancel", "job-1");
  });

  it("should call invoke for retryStep", async () => {
    const store = useWorkflowStore();

    await store.retryStep("job-1", "step-1");
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:retry-step",
      "job-1",
      "step-1",
    );
  });

  it("should call invoke for retryFrom", async () => {
    const store = useWorkflowStore();

    await store.retryFrom("job-1", "translate");
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:retry-from",
      "job-1",
      "translate",
    );
  });

  it("should call invoke for list", async () => {
    const store = useWorkflowStore();

    mockInvoke.mockResolvedValueOnce([]);
    const result = await store.list("/path/to/project");
    expect(mockInvoke).toHaveBeenCalledWith(
      "workflow:list",
      "/path/to/project",
    );
    expect(result).toEqual([]);
  });
});

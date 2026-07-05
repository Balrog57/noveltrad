/**
 * Tests for StructuredLogger (SDD §18.6).
 *
 * Verify JSON-structure output, child loggers, correlationId propagation,
 * backward compatibility, sensitive-data redaction and message truncation.
 */

import { describe, it, expect, vi } from "vitest";
import electronLog from "electron-log";

// We must mock before importing the module under test
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    transports: {
      file: { format: null as unknown as (...args: unknown[]) => unknown },
      console: { format: null as unknown as (...args: unknown[]) => unknown },
    },
  },
}));

// Import the module under test (will trigger configureTransports + initialize)
import { logger, type LogEntry } from "../../src/main/utils/logger";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function lastEntry(level: "info" | "warn" | "error" | "debug" = "info"): LogEntry {
  const mockFn = vi.mocked(electronLog[level]);
  const call = mockFn.mock.lastCall;
  if (!call) {throw new Error(`electronLog.${level} was never called`);}
  return call[0] as LogEntry;
}

function lastInfoEntry(): LogEntry {
  return lastEntry("info");
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("StructuredLogger §18.6", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Basic structure ─────────────────────────────────────────────────

  describe("JSON structure", () => {
    it("includes required fields: timestamp, level, component, message", () => {
      logger.info("Hello world");

      const entry = lastInfoEntry();
      expect(entry).toMatchObject({
        timestamp: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/),
        level: "INFO",
        component: "App",
        message: "Hello world",
      });
    });

    it("supports DEBUG level", () => {
      logger.debug("Debug msg");

      const entry = lastEntry("debug");
      expect(entry.level).toBe("DEBUG");
    });

    it("supports WARN level", () => {
      logger.warn("Warning");

      const entry = lastEntry("warn");
      expect(entry.level).toBe("WARN");
    });

    it("supports ERROR level", () => {
      logger.error("Error!");

      const entry = lastEntry("error");
      expect(entry.level).toBe("ERROR");
    });
  });

  // ── Optional fields (new-style context) ─────────────────────────────

  describe("optional fields via context object", () => {
    it("includes correlationId", () => {
      logger.info("Job done", { correlationId: "job_xyz" });

      const entry = lastInfoEntry();
      expect(entry.correlationId).toBe("job_xyz");
    });

    it("includes durationMs", () => {
      logger.info("Slow step", { durationMs: 12_450 });

      const entry = lastInfoEntry();
      expect(entry.durationMs).toBe(12_450);
    });

    it("includes tokensIn / tokensOut", () => {
      logger.info("API call", { tokensIn: 2048, tokensOut: 512 });

      const entry = lastInfoEntry();
      expect(entry.tokensIn).toBe(2048);
      expect(entry.tokensOut).toBe(512);
    });

    it("includes error string from context", () => {
      logger.info("Something went wrong", { error: "timeout" });

      const entry = lastInfoEntry();
      expect(entry.error).toBe("timeout");
    });

    it("includes projectId and chapterId", () => {
      logger.info("Working", { projectId: "proj_1", chapterId: "ch_42" });

      const entry = lastInfoEntry();
      expect(entry.projectId).toBe("proj_1");
      expect(entry.chapterId).toBe("ch_42");
    });

    it("correlationId from context overrides inherited correlationId", () => {
      const child = logger.child("Worker").withCorrelationId("parent_id");
      child.info("Override", { correlationId: "override_id" });

      const entry = lastInfoEntry();
      expect(entry.correlationId).toBe("override_id");
    });
  });

  // ── Child logger ───────────────────────────────────────────────────

  describe("child()", () => {
    it("sets the component field", () => {
      const wfLogger = logger.child("WorkflowEngine");
      wfLogger.info("Step completed");

      const entry = lastInfoEntry();
      expect(entry.component).toBe("WorkflowEngine");
    });

    it("does not mutate the parent", () => {
      const child = logger.child("Child");
      child.info("test");

      const parentEntry = lastInfoEntry();
      expect(parentEntry.component).toBe("Child");

      logger.info("parent msg");
      const entry = lastInfoEntry();
      expect(entry.component).toBe("App");
    });
  });

  // ── withCorrelationId() ────────────────────────────────────────────

  describe("withCorrelationId()", () => {
    it("includes the correlationId in every log entry", () => {
      const jobLogger = logger.child("JobRunner").withCorrelationId("job_42");

      jobLogger.info("Step 1");
      expect(lastInfoEntry().correlationId).toBe("job_42");

      jobLogger.info("Step 2");
      expect(lastInfoEntry().correlationId).toBe("job_42");

      jobLogger.warn("Retry");
      expect(lastEntry("warn").correlationId).toBe("job_42");
    });

    it("passes correlationId to child loggers", () => {
      const parent = logger.withCorrelationId("parent_abc");
      const child = parent.child("SubModule");

      child.info("Works");
      expect(lastInfoEntry().correlationId).toBe("parent_abc");
    });
  });

  // ── Backward compatibility ─────────────────────────────────────────

  describe("backward compatibility", () => {
    it("accepts simple message with no second arg", () => {
      logger.info("NovelTrad starting...");

      const entry = lastInfoEntry();
      expect(entry.message).toBe("NovelTrad starting...");
      expect(entry.error).toBeUndefined();
    });

    it("accepts message + Error as old-style error() calls", () => {
      const err = new Error("Something broke");
      logger.error("Step failed", err);

      const entry = lastEntry("error");
      expect(entry.message).toBe("Step failed");
      // The error field should contain a stack trace (or at least the message)
      expect(entry.error).toBeTruthy();
      expect(entry.error).toContain("Something broke");
    });

    it("accepts message + Error as old-style warn() calls", () => {
      const err = new Error("Degraded");
      logger.warn("RAG degraded", err);

      const entry = lastEntry("warn");
      expect(entry.message).toBe("RAG degraded");
      expect(entry.error).toContain("Degraded");
    });

    it("accepts message + plain object as old-style info(obj) calls", () => {
      const updateInfo = { version: "2.0.0", releaseDate: "2026-07-01" };
      logger.info("Update available", updateInfo);

      const entry = lastInfoEntry();
      expect(entry.message).toBe("Update available");
      // The plain object fields are merged into the entry directly
      expect(entry.version).toBe("2.0.0");
      expect(entry.releaseDate).toBe("2026-07-01");
    });

    it("works with plugin-context-style prefixed messages", () => {
      const pluginId = "com.example.plugin";
      logger.info(`[${pluginId}] Plugin loaded`);

      const entry = lastInfoEntry();
      expect(entry.message).toBe("[com.example.plugin] Plugin loaded");
    });

    it("works with template messages", () => {
      const name = "test";
      logger.info(`Plugin "${name}" not found`);

      const entry = lastInfoEntry();
      expect(entry.message).toBe(`Plugin "${name}" not found`);
    });
  });

  // ── Sensitive data redaction ────────────────────────────────────────

  describe("sensitive-data redaction (§18.6 rules)", () => {
    it("redacts apiKey in context", () => {
      logger.info("Calling API", {
        correlationId: "abc",
        apiKey: "sk-1234567890abcdef",
      });

      const entry = lastInfoEntry();
      expect(entry.apiKey).toBe("[REDACTED]");
    });

    it("redacts password in context", () => {
      logger.info("Login attempt", {
        password: "super-secret",
      });

      const entry = lastInfoEntry();
      expect(entry.password).toBe("[REDACTED]");
    });

    it("redacts secret in nested objects", () => {
      logger.info("Config loaded", {
        config: {
          clientSecret: "s3cret!",
          normalField: "visible",
        },
      });

      const entry = lastInfoEntry();
      expect(entry.config).toBeDefined();
      const config = entry.config as Record<string, unknown>;
      expect(config.clientSecret).toBe("[REDACTED]");
      expect(config.normalField).toBe("visible");
    });

    it("redacts authorization header", () => {
      logger.info("Request", { authorization: "Bearer tok_xyz" });

      const entry = lastInfoEntry();
      expect(entry.authorization).toBe("[REDACTED]");
    });

    it("does not redact innocent fields", () => {
      logger.info("Safe log", { correlationId: "abc", durationMs: 100 });

      const entry = lastInfoEntry();
      expect(entry.correlationId).toBe("abc");
      expect(entry.durationMs).toBe(100);
    });
  });

  // ── Message truncation ──────────────────────────────────────────────

  describe("message truncation", () => {
    it("truncates messages longer than 1000 characters", () => {
      const longMsg = "A".repeat(2000);
      logger.info(longMsg);

      const entry = lastInfoEntry();
      expect(entry.message.length).toBeLessThanOrEqual(1050); // 1000 + " [truncated]".length
      expect(entry.message).toMatch(/\.\.\. \[truncated\]$/);
    });

    it("keeps short messages intact", () => {
      const shortMsg = "Hello".repeat(100); // 500 chars
      logger.info(shortMsg);

      const entry = lastInfoEntry();
      expect(entry.message).toBe(shortMsg);
    });
  });

  // ── Edge cases ─────────────────────────────────────────────────────

  describe("edge cases", () => {
    it("handles Error object in old-style error() calls with stack > message", () => {
      const err = new Error("Fail");
      err.stack = "Error: Fail\n    at Test.fn (file.ts:10:5)";
      logger.error("Crash", err);

      const entry = lastEntry("error");
      expect(entry.error).toBe(err.stack);
    });

    it("handles empty message gracefully", () => {
      logger.info("");

      const entry = lastInfoEntry();
      expect(entry.message).toBe("");
    });

    it("handles multiple extra args as extra array", () => {
      logger.info("Multi", "arg1", 42, { nested: true });

      const entry = lastInfoEntry();
      expect(entry.extra).toBeDefined();
      expect(entry.extra).toHaveLength(3);
    });
  });
});

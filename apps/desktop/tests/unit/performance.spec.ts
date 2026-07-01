import { describe, it, expect, beforeEach } from "vitest";
import { PerformanceProfiler } from "../../src/main/services/PerformanceProfiler.js";

describe("PerformanceProfiler", () => {
  let profiler: PerformanceProfiler;

  beforeEach(() => {
    profiler = new PerformanceProfiler();
  });

  describe("collect()", () => {
    it("devrait collecter les metriques pour une etape", () => {
      const result = profiler.collect("job-1", "translate", {
        durationMs: 1500,
        tokensIn: 500,
        tokensOut: 300,
      });

      expect(result.jobId).toBe("job-1");
      expect(result.stage).toBe("translate");
      expect(result.durationMs).toBe(1500);
      expect(result.tokensIn).toBe(500);
      expect(result.tokensOut).toBe(300);
      expect(result.memoryPeakMB).toBeGreaterThanOrEqual(0);
      expect(result.collectedAt).toBeTruthy();
    });

    it("devrait collecter sans tokensIn/tokensOut", () => {
      const result = profiler.collect("job-2", "split", {
        durationMs: 200,
      });

      expect(result.jobId).toBe("job-2");
      expect(result.durationMs).toBe(200);
      expect(result.tokensIn).toBeUndefined();
      expect(result.tokensOut).toBeUndefined();
    });

    it("devrait collecter plusieurs etapes pour le meme job", () => {
      profiler.collect("job-3", "split", { durationMs: 100 });
      profiler.collect("job-3", "translate", {
        durationMs: 2000,
        tokensIn: 400,
        tokensOut: 250,
      });
      profiler.collect("job-3", "polish", {
        durationMs: 800,
        tokensIn: 250,
        tokensOut: 180,
      });

      const report = profiler.getReport("job-3");
      expect(report).toHaveLength(3);
      expect(report[0].stage).toBe("split");
      expect(report[1].stage).toBe("translate");
      expect(report[2].stage).toBe("polish");
    });
  });

  describe("getReport()", () => {
    it("devrait retourner un tableau vide pour un job inconnu", () => {
      const report = profiler.getReport("job-inconnu");
      expect(report).toEqual([]);
    });

    it("devrait retourner toutes les metriques d'un job", () => {
      profiler.collect("job-4", "split", { durationMs: 150 });
      profiler.collect("job-4", "grammar", {
        durationMs: 450,
        tokensIn: 100,
        tokensOut: 80,
      });

      const report = profiler.getReport("job-4");
      expect(report).toHaveLength(2);
      expect(report[0].stage).toBe("split");
      expect(report[1].stage).toBe("grammar");
    });
  });

  describe("getJobIds()", () => {
    it("devrait retourner la liste des jobIds", () => {
      profiler.collect("job-a", "split", { durationMs: 100 });
      profiler.collect("job-b", "translate", {
        durationMs: 500,
        tokensIn: 200,
        tokensOut: 150,
      });

      const ids = profiler.getJobIds();
      expect(ids).toEqual(expect.arrayContaining(["job-a", "job-b"]));
      expect(ids).toHaveLength(2);
    });

    it("devrait retourner un tableau vide si aucun job", () => {
      expect(profiler.getJobIds()).toEqual([]);
    });
  });

  describe("getAllMetrics()", () => {
    it("devrait retourner toutes les metriques de tous les jobs", () => {
      profiler.collect("job-x", "split", { durationMs: 100 });
      profiler.collect("job-y", "translate", {
        durationMs: 300,
        tokensIn: 100,
        tokensOut: 50,
      });

      const all = profiler.getAllMetrics();
      expect(all).toHaveLength(2);
    });

    it("devrait retourner un tableau vide si aucune metrique", () => {
      expect(profiler.getAllMetrics()).toEqual([]);
    });
  });

  describe("exportCsv()", () => {
    it("devrait generer un CSV avec en-tetes", () => {
      const csv = profiler.exportCsv();
      const lines = csv.trim().split("\n");
      expect(lines[0]).toBe(
        "jobId,stage,durationMs,tokensIn,tokensOut,memoryPeakMB,collectedAt",
      );
    });

    it("devrait generer un CSV avec une seule ligne de donnees", () => {
      profiler.collect("job-5", "translate", {
        durationMs: 1000,
        tokensIn: 500,
        tokensOut: 300,
      });

      const csv = profiler.exportCsv();
      const lines = csv.trim().split("\n");
      expect(lines).toHaveLength(2); // header + 1 data row
      expect(lines[1]).toContain("job-5");
      expect(lines[1]).toContain("translate");
      expect(lines[1]).toContain("1000");
      expect(lines[1]).toContain("500");
      expect(lines[1]).toContain("300");
    });

    it("devrait generer un CSV avec plusieurs lignes", () => {
      profiler.collect("job-6", "split", { durationMs: 100 });
      profiler.collect("job-6", "translate", {
        durationMs: 2000,
        tokensIn: 400,
        tokensOut: 250,
      });
      profiler.collect("job-7", "polish", {
        durationMs: 600,
        tokensIn: 150,
        tokensOut: 100,
      });

      const csv = profiler.exportCsv();
      const lines = csv.trim().split("\n");
      expect(lines).toHaveLength(4); // header + 3 data rows
    });

    it("devrait echapper les valeurs contenant des virgules", () => {
      profiler.collect('job,with,commas', 'split,test', {
        durationMs: 500,
        tokensIn: 100,
        tokensOut: 50,
      });

      const csv = profiler.exportCsv();
      expect(csv).toContain('"job,with,commas"');
      expect(csv).toContain('"split,test"');
    });
  });

  describe("clear()", () => {
    it("devrait vider toutes les metriques", () => {
      profiler.collect("job-8", "split", { durationMs: 100 });
      profiler.collect("job-8", "translate", {
        durationMs: 500,
        tokensIn: 200,
        tokensOut: 150,
      });

      expect(profiler.getJobIds()).toHaveLength(1);
      profiler.clear();
      expect(profiler.getJobIds()).toEqual([]);
      expect(profiler.getReport("job-8")).toEqual([]);
    });
  });
});

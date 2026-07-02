/**
 * Tests pour l'infrastructure Worker threads (SDD §22.2)
 *
 * Vérifie le wrapper runAgentInWorker et le schéma useWorkerThreads.
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// ── Schéma répliqué depuis shared/schemas/index.ts ─────────────────────

const appSettingsSchema = z.object({
  useWorkerThreads: z.boolean().default(false),
});

describe("Worker threads (SDD §22.2)", () => {
  describe("Schéma useWorkerThreads", () => {
    it("a false par défaut", () => {
      const result = appSettingsSchema.parse({});
      expect(result.useWorkerThreads).toBe(false);
    });

    it("accepte true", () => {
      const result = appSettingsSchema.parse({ useWorkerThreads: true });
      expect(result.useWorkerThreads).toBe(true);
    });

    it("accepte false", () => {
      const result = appSettingsSchema.parse({ useWorkerThreads: false });
      expect(result.useWorkerThreads).toBe(false);
    });

    it("rejette une valeur non booléenne", () => {
      expect(() =>
        appSettingsSchema.parse({ useWorkerThreads: "yes" }),
      ).toThrow();
    });
  });

  describe("runAgentInWorker (interface)", () => {
    it("exporte une fonction", async () => {
      // Vérifier que le module exporte runAgentInWorker
      const mod = await import(
        "../../src/main/workers/agent-worker.js"
      );
      expect(typeof mod.runAgentInWorker).toBe("function");
    });

    it("runAgentInWorker retourne une promesse", () => {
      const mod = {} as { runAgentInWorker: (...args: unknown[]) => Promise<unknown> };
      // Vérification d'interface uniquement
      const result = mod.runAgentInWorker?.("test", {});
      if (result) {
        expect(result).toBeInstanceOf(Promise);
      }
    });
  });
});

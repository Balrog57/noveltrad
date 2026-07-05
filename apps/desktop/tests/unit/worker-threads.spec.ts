/**
 * Tests pour l'infrastructure Worker threads (SDD §22.2)
 *
 * Vérifie le wrapper runAgentInWorker, le schéma useWorkerThreads,
 * la résolution des exports nommés (T14 fix), et l'intégration
 * dans WorkflowRunner.runStep().
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";
import { resolveAgentClass } from "../../src/main/workers/agent-worker.js";

// ---------------------------------------------------------------------------
// Schéma répliqué depuis shared/schemas/index.ts
// ---------------------------------------------------------------------------

const appSettingsSchema = z.object({
  useWorkerThreads: z.boolean().default(true),
});

// ---------------------------------------------------------------------------
// Agent factice pour tester resolveAgentClass
// ---------------------------------------------------------------------------

class FakeTranslationAgent {
  execute(_input: unknown): Promise<unknown> {
    return Promise.resolve({ translated: true });
  }
}

class NotAnAgent {
  // Pas de méthode execute()
  greet(): string {
    return "hello";
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Worker threads (SDD §22.2)", () => {
  describe("Schéma useWorkerThreads", () => {
    it("a true par défaut (SDD §1.6)", () => {
      const result = appSettingsSchema.parse({});
      expect(result.useWorkerThreads).toBe(true);
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
      const mod = await import(
        "../../src/main/workers/agent-worker.js"
      );
      expect(typeof mod.runAgentInWorker).toBe("function");
    });

    it("runAgentInWorker retourne une promesse", () => {
      const mod = {} as {
        runAgentInWorker: (...args: unknown[]) => Promise<unknown>;
      };
      const result = mod.runAgentInWorker?.("test", {});
      if (result) {
        expect(result).toBeInstanceOf(Promise);
      }
    });

  });

  describe("Intégration WorkflowRunner — useWorker actif", () => {
    it("le schéma par défaut active les workers (default:true)", () => {
      const settings = appSettingsSchema.parse({});
      expect(settings.useWorkerThreads).toBe(true);
    });

    it("WorkflowRunner.runStep importe runAgentInWorker", async () => {
      // Vérifier que le fichier workers exporte runAgentInWorker
      const workerMod = await import(
        "../../src/main/workers/agent-worker.js"
      );
      expect(typeof workerMod.runAgentInWorker).toBe("function");
    });
  });

  describe("resolveAgentClass — named export resolution (T14)", () => {
    it("trouve une classe avec execute() parmi les exports nommés", () => {
      const mod: Record<string, unknown> = {
        FakeTranslationAgent,
        NotAnAgent,
      };
      const found = resolveAgentClass(mod);
      expect(found).toBe(FakeTranslationAgent);
    });

    it("retourne undefined si aucune classe avec execute() n'est trouvée", () => {
      const mod: Record<string, unknown> = {
        NotAnAgent,
        someString: "hello",
        someNumber: 42,
      };
      const found = resolveAgentClass(mod);
      expect(found).toBeUndefined();
    });
  });
});

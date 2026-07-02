/**
 * SDD §22.2 — Worker thread pour l'exécution d'agents CPU-bound
 *
 * Reçoit { agentId, input, config } via parentPort, importe dynamiquement
 * l'agent, exécute et retourne le résultat.
 *
 * Agents ciblés : ConsistencyAgent, ExportAgent, SplitAgent
 * (opérations CPU-bound : comparaison, formatage, découpage).
 *
 * Désactivé par défaut en v1.0 (useWorkerThreads = false).
 * Voir WorkflowEngine.ts pour la configuration.
 */

import { parentPort, workerData } from "node:worker_threads";

interface WorkerInput {
  agentId: string;
  input: unknown;
  config?: Record<string, unknown>;
}

if (parentPort) {
  parentPort.on("message", async (message: WorkerInput) => {
    try {
      const { agentId, input, config } = message;

      // Construire le chemin de l'agent
      const agentPath = `../services/agents/${agentId}.js`;

      let agentModule: Record<string, unknown>;
      try {
        agentModule = await import(agentPath);
      } catch {
        parentPort?.postMessage({
          success: false,
          error: `Agent "${agentId}" introuvable (${agentPath})`,
        });
        return;
      }

      const AgentClass = agentModule.default as
        | (new (cfg?: Record<string, unknown>) => { execute: (input: unknown) => unknown })
        | undefined;

      if (typeof AgentClass === "function") {
        const instance = new AgentClass(config);
        if (typeof instance.execute === "function") {
          const output = await instance.execute(input);
          parentPort?.postMessage({ success: true, output });
        } else {
          parentPort?.postMessage({
            success: false,
            error: `Agent "${agentId}" n'a pas de méthode execute()`,
          });
        }
      } else {
        parentPort?.postMessage({
          success: false,
          error: `Agent "${agentId}" non exécutable`,
        });
      }
    } catch (err) {
      parentPort?.postMessage({
        success: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  });
} else if (workerData) {
  // Exécution synchrone si appelé avec workerData (via runWorker)
  // Non utilisé pour l'instant.
}

/**
 * Fonction utilitaire pour exécuter un agent dans un Worker thread.
 * Retourne une promesse avec { success, output, error }.
 *
 * Usage :
 *   const result = await runAgentInWorker('consistency', input);
 *   if (result.success) { ... }
 */
export function runAgentInWorker(
  agentId: string,
  input: unknown,
  config?: Record<string, unknown>,
): Promise<{ success: boolean; output?: unknown; error?: string }> {
  return new Promise((resolve) => {
    import("node:worker_threads")
      .then(({ Worker }) => {
        const worker = new Worker(
          new URL("agent-worker.ts", import.meta.url).href,
          {
            workerData: { agentId, input, config },
            eval: false,
          },
        );

        worker.on("message", (result: unknown) => {
          resolve(result as { success: boolean; output?: unknown; error?: string });
          worker.terminate();
        });

        worker.on("error", (err: Error) => {
          resolve({ success: false, error: err.message });
          worker.terminate();
        });

        worker.on("exit", (code: number) => {
          if (code !== 0) {
            resolve({ success: false, error: `Worker exited with code ${code}` });
          }
        });
      })
      .catch((err: Error) => {
        resolve({ success: false, error: `Failed to create Worker: ${err.message}` });
      });
  });
}

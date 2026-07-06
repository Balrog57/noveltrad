/**
 * SDD §22.2 — Worker thread pour l'exécution d'agents CPU-bound
 *
 * Reçoit { agentId, input, config } via workerData (kick-off initial)
 * ou parentPort.on('message') (fallback), importe dynamiquement
 * l'agent, exécute et retourne le résultat.
 *
 * Agents ciblés : ConsistencyAgent, ExportAgent, SplitAgent
 * (opérations CPU-bound : comparaison, formatage, découpage).
 *
 * Activé par défaut en v1.0 (useWorkerThreads = true).
 * Voir WorkflowEngine.ts pour la configuration.
 */

import { parentPort, workerData } from "node:worker_threads";

interface WorkerInput {
  agentId: string;
  input: unknown;
  config?: Record<string, unknown>;
}

/**
 * T14 fix : registre explicite stage (lowercase) → chemin de module PascalCase.
 *
 * Avant, le worker construisait le chemin par interpolation :
 *   `../services/agents/${agentId}.js`
 * avec agentId = stage lowercase (ex "translate"), mais les fichiers
 * sont PascalCase (TranslateAgent.ts → TranslateAgent.js). Résultat :
 * CHAQUE import worker échouait → fallback silencieux systématique.
 * Les worker threads n'ont jamais réellement fonctionné.
 *
 * Ce registre mappe explicitement chaque stage au bon module. Les imports
 * dynamiques sont gardés paresseux (le worker ne charge que l'agent requis).
 */
const AGENT_MODULES: Record<string, () => Promise<Record<string, unknown>>> = {
  split: () => import("../services/agents/SplitAgent.js"),
  pre_translate: () => import("../services/agents/PreTranslateAgent.js"),
  translate: () => import("../services/agents/TranslateAgent.js"),
  consistency: () => import("../services/agents/ConsistencyAgent.js"),
  lexicon: () => import("../services/agents/LexiconAgent.js"),
  grammar: () => import("../services/agents/GrammarAgent.js"),
  style: () => import("../services/agents/StyleAgent.js"),
  polish: () => import("../services/agents/PolishAgent.js"),
  qa: () => import("../services/agents/QaAgent.js"),
  export: () => import("../services/agents/ExportAgent.js"),
};

/**
 * Exporté pour tests unitaires : permet de vérifier que les 10 stages
 * sont mappés à un module d'agent valide.
 */
export const STAGE_REGISTRY = AGENT_MODULES;

/**
 * Résout la classe d'agent à partir des exports d'un module ESM.
 * Cherche un export nommé qui est une classe avec prototype.execute.
 * Les agents sont exportés en nom (ex: `export class TranslateAgent`),
 * pas en `export default` — le worker doit inspecter toutes les clés.
 *
 * Exporté pour faciliter les tests unitaires.
 */
export function resolveAgentClass(
  agentModule: Record<string, unknown>,
):
  | (new (cfg?: Record<string, unknown>) => { execute: (input: unknown) => Promise<unknown> })
  | undefined {
  return Object.values(agentModule).find(
    (v) => typeof v === "function" && typeof v.prototype?.execute === "function",
  ) as
    | (new (cfg?: Record<string, unknown>) => { execute: (input: unknown) => Promise<unknown> })
    | undefined;
}

/**
 * Exécute un agent identifié par agentId avec les données fournies.
 * Retourne le résultat via parentPort.postMessage().
 */
async function executeAgent(data: WorkerInput): Promise<void> {
  const { agentId, input, config } = data;

  // T14 fix : résoudre le module via le registre explicite (PascalCase).
  const loader = AGENT_MODULES[agentId];

  let agentModule: Record<string, unknown>;
  try {
    if (!loader) {
      throw new Error(`Stage "${agentId}" absent du registre AGENT_MODULES`);
    }
    agentModule = await loader();
  } catch (err) {
    parentPort?.postMessage({
      success: false,
      error: `Agent "${agentId}" introuvable (${err instanceof Error ? err.message : String(err)})`,
    });
    return;
  }

  // Trouver la classe d'agent avec execute() parmi toutes les
  // exportations nommées (les agents sont exportés en nom, pas en default).
  const AgentClass = resolveAgentClass(agentModule);

  if (AgentClass) {
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
      error: `Agent "${agentId}" non exécutable — aucune classe avec execute() trouvée`,
    });
  }
}

// ── Kick-off : lire workerData au démarrage ──────────────────────────
// runAgentInWorker() envoie les données via workerData (pas via postMessage).
// Le Worker les lit ici et exécute directement.
if (workerData) {
  executeAgent(workerData as WorkerInput).catch((err) => {
    parentPort?.postMessage({
      success: false,
      error: err instanceof Error ? err.message : String(err),
    });
  });
}

// ── Fallback : écouter les messages post-initiation ──────────────────
// Permet des cas d'usage où le Worker reçoit des tâches supplémentaires.
if (parentPort) {
  parentPort.on("message", async (message: WorkerInput) => {
    try {
      await executeAgent(message);
    } catch (err) {
      parentPort?.postMessage({
        success: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  });
}

/**
 * Fonction utilitaire pour exécuter un agent dans un Worker thread.
 * Retourne une promesse avec { success, output, error }.
 *
 * Les données sont transmises via workerData (pas postMessage) pour
 * éviter le deadlock : le Worker lit workerData au démarrage et exécute
 * immédiatement.
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

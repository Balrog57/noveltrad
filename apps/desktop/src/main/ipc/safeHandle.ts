import { ipcMain, type IpcMainInvokeEvent } from "electron";
import type { ZodSchema } from "zod";
import { logger } from "../utils/logger.js";

/**
 * WS-2 (clean architecture) : helper optionnel pour standardiser l'enregistrement
 * d'un handler IPC avec validation Zod + try/catch cohérent.
 *
 * ## Pourquoi pas une enveloppe `{ok, data, error}` imposée ?
 *
 * Le contrat IPC actuel est **hétérogène mais intentionnel** :
 *   - La plupart des handlers retournent directement la valeur métier
 *     (`Job[]`, `LexiconEntry`, `Project`, …) et le renderer fait
 *     `const x = await invoke(...)`. Forcer `{ok, data}` casserait tous les
 *     call-sites renderer.
 *   - Quelques handlers retournent un discriminated union légitime sur le
 *     chemin succès (`source:import-files` → per-file `{success}`[],
 *     `dialog:open-file` → `{success, paths}` où un cancel n'est pas une
 *     erreur). Ce ne sont pas des erreurs à standardiser.
 *   - Les erreurs : le preload `invoke()` re-throw, et **tous** les stores
 *     renderer font `catch (err) { error.value = err instanceof Error ?
 *     err.message : … }`. Le canal d'erreur est donc le **throw**, pas une
 *     enveloppe.
 *
 * `safeHandle` standardise donc le chemin ERREUR uniquement :
 *   1. Validation Zod du 1er arg (`rawArgs[0]`) si un schema est fourni.
 *   2. try/catch autour du corps métier.
 *   3. En cas d'erreur : log structuré + re-throw d'un `Error` à message
 *      lisible (le store renderer récupère `.message` via le preload).
 *
 * La valeur de retour du handler passe telle quelle (pas d'enveloppe).
 *
 * ## Usage (handler à 1 payload objet)
 *
 * ```ts
 * // Renderer: invoke("lexicon:list", { projectId })
 * safeHandle("lexicon:list", lexiconListSchema, async (payload) => {
 *   return lexiconRepo.listByProject(payload.projectId);
 * });
 * ```
 *
 * ## Limites — quand NE PAS utiliser safeHandle
 *
 * - **Handlers multi-args positionnels** (ex: `workflow:start(projectPath, chapterId)`) :
 *   le schema ne connaît pas les noms d'args. Utiliser `safeHandleRaw` à la
 *   place, ou garder `ipcMain.handle` direct (déjà testé, fonctionne).
 * - **Handlers avec try/finally sur DB** : safeHandle n'englobe que le handler
 *   body, pas les ressources. Le try/finally reste nécessaire côté caller.
 *
 * L'adoption est progressive et optionnelle — les handlers existants
 * fonctionnent déjà (Zod + try/catch inline). safeHandle standardise juste
 * le logging et le formatage des erreurs Zod.
 */
export function safeHandle<S extends ZodSchema>(
  channel: string,
  schema: S,
  handler: (
    parsed: S["_output"],
    event: IpcMainInvokeEvent,
  ) => Promise<unknown> | unknown,
): void {
  ipcMain.handle(channel, async (event, ...rawArgs) => {
    // safeHandle valide rawArgs[0] (le 1er argument, typiquement un payload
    // objet passé par le renderer via invoke(channel, payload)). Pour les
    // handlers multi-args positionnels, utiliser safeHandleRaw.
    const rawPayload = rawArgs[0];
    let parsed: unknown;
    try {
      parsed = schema.parse(rawPayload);
    } catch (err) {
      const message = formatZodError(err, channel);
      logger.warn(`[IPC ${channel}] validation échouée`, { message });
      throw new Error(message);
    }
    try {
      return await handler(parsed as S["_output"], event);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      logger.error(`[IPC ${channel}] handler échoué`, err);
      throw new Error(message);
    }
  });
}

/**
 * Variante sans validation Zod, mais avec le même try/catch + log cohérent.
 * Utile pour migrer progressivement : d'abord le try/catch, puis ajouter un
 * schema plus tard.
 */
export function safeHandleRaw(
  channel: string,
  handler: (
    args: unknown[],
    event: IpcMainInvokeEvent,
  ) => Promise<unknown> | unknown,
): void {
  ipcMain.handle(channel, async (event, ...args) => {
    try {
      return await handler(args, event);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      logger.error(`[IPC ${channel}] handler échoué`, err);
      throw new Error(message);
    }
  });
}

/**
 * Formate une erreur Zod en message lisible par l'utilisateur.
 * Si ce n'est pas une ZodError, retourne le message d'origine.
 */
function formatZodError(err: unknown, channel: string): string {
  if (err && typeof err === "object" && "issues" in err) {
    const issues = (err as { issues: Array<{ message: string; path: PropertyKey[] }> }).issues;
    if (Array.isArray(issues) && issues.length > 0) {
      const details = issues
        .map((i) =>
          i.path.length > 0
            ? `${i.path.join(".")}: ${i.message}`
            : i.message,
        )
        .join("; ");
      return `Paramètres invalides (${channel}): ${details}`;
    }
  }
  return err instanceof Error ? err.message : String(err);
}

import { ref, type Ref } from "vue";

/**
 * WS-6 (clean architecture) : wrapper pour les actions async des stores.
 *
 * Le pattern suivant était répété 21× à travers les stores renderer :
 *
 * ```ts
 * loading.value = true;
 * error.value = null;
 * try {
 *   // ... corps métier ...
 * } catch (err) {
 *   error.value = err instanceof Error ? err.message : "fallback";
 * } finally {
 *   loading.value = false;
 * }
 * ```
 *
 * `useAsyncAction` encapsule ce scaffolding. Retourne `{ loading, error, run }`
 * où `run(fn, fallback)` exécute `fn` avec la gestion d'erreur standardisée.
 *
 * Usage :
 * ```ts
 * const { loading, error, run } = useAsyncAction();
 * async function loadProject(id: string) {
 *   await run(
 *     async () => { project.value = await invoke("project:open", id); },
 *     "Erreur lors du chargement du projet",
 *   );
 * }
 * ```
 *
 * NOTE : ce composable est mis à disposition pour adoption progressive.
 * Les stores existants ne sont pas migrés massivement dans cette session
 * (le renderer n'a pas de tests unitaires — chaque migration serait non
 * couverte). Adopter au cas par cas quand un store est touché pour autre
 * chose.
 */
export interface AsyncAction {
  loading: Ref<boolean>;
  error: Ref<string | null>;
  /** True uniquement pendant l'exécution de `run`. */
  run<T>(fn: () => Promise<T>, fallbackMessage?: string): Promise<T | undefined>;
  /** Réinitialise l'erreur (utile avant un retry ou un changement de vue). */
  reset(): void;
}

export function useAsyncAction(): AsyncAction {
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function run<T>(
    fn: () => Promise<T>,
    fallbackMessage = "Une erreur est survenue",
  ): Promise<T | undefined> {
    loading.value = true;
    error.value = null;
    try {
      return await fn();
    } catch (err) {
      error.value = err instanceof Error ? err.message : fallbackMessage;
      return undefined;
    } finally {
      loading.value = false;
    }
  }

  function reset(): void {
    error.value = null;
    loading.value = false;
  }

  return { loading, error, run, reset };
}

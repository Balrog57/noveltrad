import { toRaw } from "vue";

/**
 * Convertit une valeur potentiellement réactive (Vue Proxy / ref unwrap) en un
 * POJO clonable structurellement.
 *
 * Indispensable avant tout `window.novelTradAPI.invoke()` : `ipcRenderer.invoke()`
 * d'Electron sérialise ses arguments via le **structured clone algorithm**,
 * qui rejette les Proxy Vue et les Symbols internes (`__v_isRef`, `__v_skip`,
 * `__v_raw`) avec `DataCloneError: An object could not be cloned.`.
 *
 * Note : un round-trip JSON ne conserve que les données sérialisables
 * (objets, tableaux, strings/numbers/booleans/null). Ne pas l'utiliser pour
 * des payloads contenant `Map`, `Set`, `undefined` (clés) ou des fonctions.
 */
export function toPlain<T>(value: T): T {
  return JSON.parse(JSON.stringify(toRaw(value))) as T;
}

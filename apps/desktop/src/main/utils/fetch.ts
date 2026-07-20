/**
 * Shim fetch : utilise `electron.net.fetch` quand l'app tourne dans Electron,
 * sinon `globalThis.fetch` (Node 20+). Les deux API sont compatibles (mêmes
 * Request/Response/Headers, même AbortSignal.timeout).
 *
 * Raison d'être : permettre aux providers (OllamaProvider, RagEngine) et à
 * OllamaManager de fonctionner à la fois dans l'app Electron ET en CLI pure
 * Node (où `electron` n'est pas disponible). Avant ce shim, ces modules
 * importaient `net` depuis "electron" — ce qui crashait au chargement hors
 * Electron (CLI, scripts tsx, tests isolés).
 *
 * Détection Electron : `process.versions.electron` est positionné par le
 * runtime Electron uniquement. En Node pur, il est `undefined`. On fait un
 * `require("electron")` paresseux (dans un try/catch) pour éviter un import
 * statique qui casserait le bundling CLI.
 */

import { createRequire } from "node:module";

type FetchFn = typeof globalThis.fetch;

// createRequire depuis un module ESM permet d'appeler require() tout en
// restant interceptable par vi.mock("electron") de Vitest (qui hook les
// résolutions de modules ESM ET CJS via createRequire).
const esmRequire = createRequire(import.meta.url);

function resolveFetch(): FetchFn {
  // 1. Tenter electron.net.fetch en priorité. createRequire (et non require
  //    direct) pour rester compatible ESM et interceptable par les mocks
  //    Vitest. En CLI pure Node, "electron" n'est pas installé → require
  //    lève et on tombe sur le fallback.
  try {
    const electron = esmRequire("electron");
    if (electron?.net?.fetch) {
      return electron.net.fetch as FetchFn;
    }
  } catch {
    // "electron" non disponible (CLI pure Node, tsx) → fallback ci-dessous.
  }
  // 2. Fallback : globalThis.fetch (Node 20+ natif, API-compatible avec
  //    electron.net.fetch). Permet aux providers de fonctionner en CLI.
  if (typeof globalThis.fetch === "function") {
    return globalThis.fetch;
  }
  throw new Error(
    "Aucune implémentation de fetch disponible. Sous Electron, 'electron.net.fetch' est attendu ; sous Node, globalThis.fetch (Node 20+).",
  );
}

export const fetch: FetchFn = resolveFetch();

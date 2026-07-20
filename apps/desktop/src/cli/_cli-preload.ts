/**
 * Preload CLI : stubs pour modules Electron-only chargés au démarrage.
 *
 * tsx charge ce fichier via --import AVANT le code Noveltrad. Il intercepte
 * les imports de modules qui crashent hors Electron (electron-log notamment).
 *
 * Sans ça, utils/logger.ts appelle electronLog.initialize() au chargement du
 * module → TypeError hors runtime Electron.
 *
 * Usage : `tsx --import ./apps/desktop/src/cli/_cli-preload.ts apps/desktop/src/cli/index.ts`
 *
 * Implémentation : on crée un module stub physique (pas un data URL, car les
 * fonctions seraient perdues par JSON.stringify) + un resolver ESM qui
 * redirige "electron-log" vers ce fichier.
 */

import { register } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

// Dossier temporaire pour les stubs CLI de ce process.
const stubDir = path.join(os.tmpdir(), `noveltrad-cli-${process.pid}`);
fs.mkdirSync(stubDir, { recursive: true });

// ── Stub electron-log ───────────────────────────────────────────────────
// Logger console API-compatible. Le StructuredLogger Noveltrad appelle
// info/warn/error/debug/transports.file.format/transports.console.format
// dessus sans crasher.
const electronLogStubSource = `// Auto-generated stub for CLI mode (electron-log n'est pas disponible hors Electron).
// Logs vont sur STDERR pour ne pas polluer stdout (réservé au JSON résultat).
const noop = () => {};
const logFn = (level) => (...args) => console.error("[noveltrad][" + level + "]", ...args);
const stub = {
  initialize: noop,
  transports: {
    console: { level: "info", format: noop, writeFn: noop },
    file: { level: "info", format: noop, writeFn: noop, resolvePathFn: () => "noveltrad-cli.log" },
    ipc: noop,
  },
  functions: {},
  log: logFn("log"),
  info: logFn("info"),
  warn: logFn("warn"),
  error: logFn("error"),
  debug: noop,
};
export default stub;
`;

const stubFile = path.join(stubDir, "electron-log-stub.mjs");
fs.writeFileSync(stubFile, electronLogStubSource);
const stubUrl = pathToFileURL(stubFile).href;

// ── Resolver ESM ────────────────────────────────────────────────────────
const hookCode = `
export function resolve(specifier, context, nextResolve) {
  if (specifier === "electron-log") {
    return { url: ${JSON.stringify(stubUrl)}, shortCircuit: true };
  }
  return nextResolve(specifier, context);
}
`;

const hookFile = path.join(stubDir, "resolver.mjs");
fs.writeFileSync(hookFile, hookCode);
register(pathToFileURL(hookFile).href);

// Nettoyer le dossier temporaire à la sortie.
process.on("exit", () => {
  try {
    fs.rmSync(stubDir, { recursive: true, force: true });
  } catch {
    /* best-effort */
  }
});


/**
 * Helpers de sortie pour la CLI Noveltrad.
 *
 * Convention "agent IA friendly" :
 *   - Sans --json : sortie lisible (texte simple, tables alignées).
 *   - Avec --json : un unique objet JSON sur stdout, structuré et stable.
 *   - Les logs de progrès (workflow) vont sur stderr pour ne pas polluer stdout.
 *
 * Toutes les fonctions d'output passent par ici pour garantir la cohérence du
 * format JSON consommable par un agent IA.
 */

export interface OkResult<T> {
  ok: true;
  data: T;
}

export interface ErrorResult {
  ok: false;
  error: {
    /** Code court stable (pour brancher un agent IA : "NOT_FOUND", "OLLAMA_DOWN"...). */
    code: string;
    /** Message lisible par un humain (français, comme l'UI). */
    message: string;
    /** Détails optionnels (structure libre). */
    details?: unknown;
  };
}

export type Result<T> = OkResult<T> | ErrorResult;

/** Affiche un résultat (succès ou erreur) au format JSON ou texte selon le flag. */
export function printResult<T>(result: Result<T>, json: boolean): void {
  if (json) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
    return;
  }
  if (result.ok) {
    // Pour le mode texte, on laisse chaque commande formater son propre data.
    // Si data est une string, on l'affiche directement.
    if (typeof result.data === "string") {
      process.stdout.write(result.data + "\n");
    } else if (Array.isArray(result.data)) {
      process.stdout.write(formatList(result.data) + "\n");
    }
  } else {
    process.stderr.write(`Erreur [${result.error.code}]: ${result.error.message}\n`);
    if (result.error.details) {
      process.stderr.write(JSON.stringify(result.error.details, null, 2) + "\n");
    }
  }
}

/** Formatage basique d'une liste d'objets en table texte. */
function formatList(items: unknown[]): string {
  if (items.length === 0) {return "(aucun élément)";}
  const rows = items.map((item) => {
    if (typeof item === "string") {return item;}
    if (item && typeof item === "object") {
      return Object.entries(item as Record<string, unknown>)
        .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
        .join("  ");
    }
    return String(item);
  });
  return rows.join("\n");
}

/**
 * Affiche un event de progrès workflow sur stderr (une ligne JSON par event).
 * Format NDJSON (Newline-Delimited JSON) — un agent IA peut parser ligne par
 * ligne au fur et à mesure sans attendre la fin du process.
 */
export function printProgress(payload: unknown): void {
  process.stderr.write(JSON.stringify({ type: "progress", payload }) + "\n");
}

/** Helpers pour construire des Result sans répéter la structure. */
export const ok = <T>(data: T): OkResult<T> => ({ ok: true, data });
export const err = (code: string, message: string, details?: unknown): ErrorResult => ({
  ok: false,
  error: { code, message, details },
});

/**
 * Codes d'erreur normalisés → exit codes sémantiques pour la CLI.
 *
 *   0 = succès
 *   1 = erreur utilisateur (projet existe, fichier absent, args invalides)
 *   2 = Ollama inaccessible (réseau, modèle absent)
 *   3 = erreur DB (migration, corruption)
 *   4 = traduction échouée (QA trop bas, timeout step)
 *   5 = erreur inconnue
 */
export const EXIT_CODES = {
  OK: 0,
  USER_ERROR: 1,
  OLLAMA_DOWN: 2,
  DB_ERROR: 3,
  TRANSLATION_FAILED: 4,
  UNKNOWN: 5,
} as const;

/**
 * Mappe un code d'erreur logique vers un exit code.
 * Permet à un script shell / agent IA de distinguer les causes d'échec.
 */
export function errorCodeToExit(code: string): number {
  switch (code) {
    case "NOT_FOUND":
    case "ALREADY_EXISTS":
    case "INVALID_ARGS":
    case "FILE_NOT_FOUND":
      return EXIT_CODES.USER_ERROR;
    case "OLLAMA_DOWN":
    case "MODEL_NOT_FOUND":
      return EXIT_CODES.OLLAMA_DOWN;
    case "DB_ERROR":
    case "MIGRATION_ERROR":
      return EXIT_CODES.DB_ERROR;
    case "QA_FAILED":
    case "STEP_TIMEOUT":
      return EXIT_CODES.TRANSLATION_FAILED;
    default:
      return EXIT_CODES.UNKNOWN;
  }
}

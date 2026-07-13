import path from "node:path";
import os from "node:os";

export function expandHome(input: string): string {
  if (input.startsWith("~/") || input.startsWith("~\\")) {
    return path.join(os.homedir(), input.slice(2));
  }
  return input;
}

export function getGlobalConfigDir(): string {
  const appData = process.env.APPDATA || path.join(os.homedir(), ".config");
  return path.join(appData, "NovelTrad");
}

/**
 * SDD §21.3 — Protection contre le path traversal.
 * Vérifie que `targetPath` réside bien dans `basePath`.
 * Lance une erreur si une tentative de sortie du répertoire est détectée.
 */
export function assertWithinProject(
  basePath: string,
  targetPath: string,
): void {
  // SDD §21.3 — Reject URL-encoded traversal sequences BEFORE path resolution
  if (/(?:\.|%2e){2}(?:$|\/|\\|%2f|%5c)/i.test(targetPath)) {
    throw new Error("Path traversal detected");
  }

  const resolvedBase = path.resolve(basePath);
  const resolvedTarget = path.resolve(targetPath);
  if (!resolvedTarget.startsWith(resolvedBase + path.sep) &&
      resolvedTarget !== resolvedBase) {
    throw new Error("Path traversal detected");
  }
}

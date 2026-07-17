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
  const resolvedBase = path.resolve(basePath);
  const resolvedTarget = path.resolve(targetPath);
  if (!resolvedTarget.startsWith(resolvedBase + path.sep) &&
      resolvedTarget !== resolvedBase) {
    throw new Error("Path traversal detected");
  }
}

/**
 * Workstream D / P0-5 fix — Garde-fou pour les chemins de sortie contrôlés
 * par le renderer (project:create parentPath, export outputPath, etc.).
 *
 * Rejette les chemins qui pointeraient vers des zones système sensibles où
 * NovelTrad ne devrait jamais écrire. La threat model d'une app desktop
 * accorde déjà au renderer les privilèges utilisateur, mais defense-in-depth :
 * un plugin compromis ou un IPC détourné ne doit pas pouvoir écraser
 * C:\Windows, /etc, /usr, le dossier de l'OS, etc.
 *
 * Note : ce n'est PAS une allowlist stricte (l'utilisateur peut légitimement
 * créer un projet n'importe où dans son home). On bloque juste les cibles
 * manifestement dangereuses.
 *
 * @throws Error si le chemin résolu tombe sous un répertoire système critique.
 */
const FORBIDDEN_PREFIXES_WIN32 = [
  "c:\\windows",
  "c:\\program files",
  "c:\\program files (x86)",
  "c:\\programdata",
  "c:\\$recycle.bin",
  "c:\\system volume information",
];
const FORBIDDEN_PREFIXES_POSIX = [
  "/etc",
  "/usr",
  "/bin",
  "/sbin",
  "/lib",
  "/lib64",
  "/boot",
  "/dev",
  "/proc",
  "/sys",
  "/var",
];

export function assertSafeProjectPath(targetPath: string): void {
  const resolved = path.resolve(expandHome(targetPath)).toLowerCase();
  const forbidden =
    process.platform === "win32"
      ? FORBIDDEN_PREFIXES_WIN32
      : FORBIDDEN_PREFIXES_POSIX;
  for (const prefix of forbidden) {
    if (resolved === prefix || resolved.startsWith(prefix + path.sep) || resolved.startsWith(prefix + "/")) {
      throw new Error(
        `Chemin de projet interdit (zone système) : ${targetPath}`,
      );
    }
  }
}

import path from "node:path";
import os from "node:os";
import fs from "node:fs";

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
 * Regex détectant les tentatives de path traversal, qu'elles soient brutes
 * (`..`) ou URL-encodées (`%2e%2e`, `%2f`, `%5c`). L'ancre `(?:^|\/|\\|...)`
 * garantit que `..` est un segment de chemin complet — pas un littéral dans
 * un nom de fichier légitime (ex: `my..file.txt` n'est PAS matché).
 *
 * Consolidation des 6 PRs sentinel (#86, #87, #90, #91, #93, #96) qui
 * proposaient chacune une variation de cette regex. La version ci-dessous
 * est la plus stricte (ancre + couverture des séparateurs encodés) et valide
 * les deux chemins (basePath + targetPath) comme #91.
 */
const TRAVERSAL_REGEX = /(?:^|\/|\\|%2f|%5c)(?:\.|%2e){2}(?:$|\/|\\|%2f|%5c)/i;

/**
 * SDD §21.3 — Protection contre le path traversal.
 * Vérifie que `targetPath` réside bien dans `basePath`.
 * Lance une erreur si une tentative de sortie du répertoire est détectée.
 *
 * Trois couches de défense (consolidation des 6 PRs sentinel) :
 *   1. Regex TRAVERSAL_REGEX sur les chaînes brutes (attrape `%2e%2e` avant
 *      toute résolution — `path.resolve` traite `%2e%2e` comme un littéral,
 *      ce qui était le bypass).
 *   2. `fs.realpathSync` sur les deux chemins pour résoudre les symlinks
 *      (aucune des 6 PRs ne couvrait ce vecteur). Fallback sur `path.resolve`
 *      si le chemin n'existe pas encore (ex: fichier à créer).
 *   3. `startsWith` sur les chemins résolus (garde-fou classique).
 */
export function assertWithinProject(
  basePath: string,
  targetPath: string,
): void {
  // 1. Regex brute —attrape le bypass URL-encoded avant résolution.
  if (TRAVERSAL_REGEX.test(targetPath) || TRAVERSAL_REGEX.test(basePath)) {
    throw new Error("Path traversal detected");
  }

  // 2. Résolution via realpath (symlink-aware) si les chemins existent,
  //    sinon fallback path.resolve (fichier à créer).
  let resolvedBase: string;
  let resolvedTarget: string;
  try {
    resolvedBase = fs.realpathSync(path.resolve(basePath));
  } catch {
    resolvedBase = path.resolve(basePath);
  }
  try {
    resolvedTarget = fs.realpathSync(path.resolve(targetPath));
  } catch {
    resolvedTarget = path.resolve(targetPath);
  }

  // 3. startsWith sur chemins résolus.
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
  // Même regex anti-traversal que assertWithinProject (bypass %2e%2e).
  if (TRAVERSAL_REGEX.test(targetPath)) {
    throw new Error(`Chemin de projet interdit (path traversal) : ${targetPath}`);
  }
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

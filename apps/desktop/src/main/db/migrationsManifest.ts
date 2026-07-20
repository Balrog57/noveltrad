/**
 * Manifest des migrations SQL, bundled au build via `import.meta.glob`.
 *
 * Historiquement les fichiers `*.sql` étaient lus sur disque au runtime via
 * `path.join(__dirname, "../../db/migrations")`. En build packagé ce dossier
 * n'était jamais copié dans `out/`, donc `runMigrations()` échouait
 * silencieusement derrière un `fs.existsSync`, laissait la base sans la table
 * `projects`, et l'INSERT suivant levait `no such table: projects` (erreur
 * masquée côté UI par un ENOTEMPTY du cleanup).
 *
 * En inlinant le contenu des `.sql` comme chaînes dans le bundle via
 * `import.meta.glob(..., { query: "?raw", eager: true })`, on supprime tout
 * problème de résolution de chemin : la même source fonctionne en `dev`,
 * `preview` et app packagée.
 *
 * Fallback disque : quand le module est chargé hors Vite (scripts tsx, tests
 * isolés sans bundler), `import.meta.glob` n'existe pas. On lit alors les
 * `.sql` depuis le dossier adjacent — permet de tester le pipeline DB sans
 * electron-vite.
 */

import nodePath from "node:path";
import nodeFs from "node:fs";
import { fileURLToPath } from "node:url";

export interface BundledMigration {
  version: number;
  name: string;
  sql: string;
}

// `import.meta.glob` est résolu par Vite/electron-vite au build : chaque
// fichier est embarqué comme string (suffixe `?raw`), indépendamment de
// l'arborescence de `out/`.
//
// Fallback disque : quand le module est chargé hors Vite (scripts tsx,
// tests isolés sans bundler), `import.meta.glob` n'existe pas. On lit alors
// les `.sql` depuis le dossier `migrations/` adjacent. Vite replaçant
// `import.meta.glob(...)` par un objet littéral au build, `rawModules` est
// non-vide en production ; si vide, on tente le fallback disque.
let rawModules: Record<string, string>;
try {
  // En build Vite, l'appel ci-dessous est remplacé par un Object.assign
  // statique. En runtime hors-Vite, il lève TypeError (glob n'existe pas).
  rawModules = import.meta.glob("./migrations/*.sql", {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>;
} catch {
  rawModules = {};
}

// Si le bundle est vide (ex: tsx direct, tests hors Vite), fallback disque.
if (Object.keys(rawModules).length === 0) {
  const thisDir = nodePath.dirname(fileURLToPath(import.meta.url));
  const migrationsDir = nodePath.join(thisDir, "migrations");
  if (nodeFs.existsSync(migrationsDir)) {
    for (const name of nodeFs.readdirSync(migrationsDir)) {
      if (name.endsWith(".sql")) {
        rawModules[`./migrations/${name}`] = nodeFs.readFileSync(
          nodePath.join(migrationsDir, name),
          "utf-8",
        );
      }
    }
  }
}

export const MIGRATIONS: BundledMigration[] = Object.entries(rawModules)
  .map(([filePath, sql]) => {
    const name = filePath.split("/").pop() ?? filePath;
    const match = name.match(/^(\d+)/);
    return {
      version: match ? parseInt(match[1], 10) : NaN,
      name,
      sql,
    };
  })
  .filter((m) => !Number.isNaN(m.version))
  .sort((a, b) => a.version - b.version);

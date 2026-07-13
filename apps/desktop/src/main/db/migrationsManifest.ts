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
 * `import.meta.glob(..., { query: '?raw', eager: true })`, on supprime tout
 * problème de résolution de chemin : la même source fonctionne en `dev`,
 * `preview` et app packagée.
 */

export interface BundledMigration {
  version: number;
  name: string;
  sql: string;
}

// `import.meta.glob` est résolu par Vite/electron-vite au build : chaque
// fichier est embarqué comme string (suffixe `?raw`), indépendamment de
// l'arborescence de `out/`.
const rawModules = import.meta.glob("./migrations/*.sql", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

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

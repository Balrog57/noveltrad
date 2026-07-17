import type { Database } from "node-sqlite3-wasm";

/**
 * Helpers partagés pour la couche DB.
 *
 * Objectifs (Workstream A du refactor) :
 * - **Atomicité** : `withTransaction` remplace les blocs BEGIN/COMMIT/ROLLBACK
 *   copiés-collés dans plusieurs repositories (Paragraph, Lexicon, Summary).
 * - **Lecture/écriture JSON** : `jsonColumn` supprime la dizaine de copies du
 *   pattern `row.x ? JSON.parse(String(row.x)) : undefined`.
 * - **Booléens SQLite** : `boolColumn` unifie la coercition `0/1 ↔ boolean`.
 *
 * Aucune dépendance à `connection.ts` pour éviter une importation circulaire
 * (les repositories n'ont besoin que du type `Database`).
 */

/**
 * Exécute `fn` à l'intérieur d'une transaction SQLite.
 *
 * - Ouvre par `BEGIN` (transaction différée).
 * - Commit sur retour normal de `fn`.
 * - Rollback sur exception puis relance l'erreur (la transaction est annulée,
 *   l'appelant garde la responsabilité du reporting d'erreur).
 *
 * Ne supporte pas l'imbrication : SQLite, via `exec()` brut, lèverait
 * "cannot start a transaction within a transaction". Les migrations qui
 * contiennent déjà leur propre transaction doivent l'appeler sans wrapper.
 */
export function withTransaction<T>(db: Database, fn: () => T): T {
  db.exec("BEGIN");
  try {
    const result = fn();
    db.exec("COMMIT");
    return result;
  } catch (err) {
    try {
      db.exec("ROLLBACK");
    } catch {
      // La transaction a peut-être déjà été annulée (ex: SQLITE_BUSY mortel)
      // ou n'est plus ouverte. On ne masque pas l'erreur d'origine.
    }
    throw err;
  }
}

/**
 * Accesseur unifié pour les colonnes TEXT sérialisées en JSON.
 *
 * Lecture : `undefined` si la valeur SQL est NULL ou vide, sinon `JSON.parse`.
 *   Un JSON corrompu renvoie `undefined` (résilience — ne fait pas planter
 *   toute la lecture d'une ligne pour une colonne pourrie).
 * Écriture : `null` si la valeur est `null`/`undefined`, sinon `JSON.stringify`.
 */
export const jsonColumn = {
  read(row: Record<string, unknown>, key: string): unknown | undefined {
    const v = row[key];
    if (v == null || v === "") return undefined;
    try {
      return JSON.parse(String(v));
    } catch {
      return undefined;
    }
  },
  write(v: unknown): string | null {
    return v == null ? null : JSON.stringify(v);
  },
};

/**
 * Accesseur unifié pour les colonnes booléennes stockées en INTEGER (0/1).
 */
export const boolColumn = {
  read(row: Record<string, unknown>, key: string): boolean {
    return Boolean(row[key]);
  },
  write(v: boolean): 0 | 1 {
    return v ? 1 : 0;
  },
};

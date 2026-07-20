import type { Database, JSValue } from "node-sqlite3-wasm";

/**
 * Base class pour tous les repositories du domaine Noveltrad.
 *
 * Rationale (WS-1 — clean architecture) : les 7 repositories partageaient
 * 3 patterns mécaniques dupliqués :
 *   1. `constructor(private db: Database) {}` (7×)
 *   2. Le cast `as Record<string, unknown> | undefined` après chaque
 *      `.get()` / `.all()` (≈25 sites)
 *   3. L'appel `.map(row)` pour transformer la row brute en entité typée
 *
 * La base absorbe ces mécaniques via des helpers `protected`. Les subclasses
 * conservent la main sur :
 *   - leur liste de colonnes (chaque table a un schéma différent)
 *   - leurs requêtes spécialisées (HistoryRepository a des snapshots
 *     hybrides, SummaryRepository des UPSERTs, JobRepository mappe 2 entités)
 *   - leur fonction `map(row)` propre
 *
 * La base impose un type `T` d'entité et un `tableName` (utilisé uniquement
 * par les helpers par défaut `findById` / `deleteById`). Les subclasses qui
 * ont des besoins différents ne les utilisent simplement pas.
 *
 * Pas de SQL magique ni de reflection — la base ne devine pas les colonnes.
 * C'est volontaire : chaque repo reste lisible et auditable.
 */
export abstract class BaseRepository<T> {
  /** Connexion DB partagée avec les autres repositories du même contexte. */
  protected readonly db: Database;

  constructor(db: Database, private readonly tableName: string) {
    this.db = db;
  }

  // ── Helpers de lecture ────────────────────────────────────────────────

  /**
   * Exécute un SELECT qui renvoie 0 ou 1 row, et la mappe vers `T`.
   * Centralise le cast `Record<string, unknown>` et l'appel `map()`.
   *
   * @param sql     Requête SQL paramétrée.
   * @param params  Bind values.
   * @returns L'entité mappée, ou `undefined` si aucune row.
   */
  protected queryOne(
    sql: string,
    params: JSValue[] = [],
  ): T | undefined {
    const row = this.db
      .prepare(sql)
      .get(params) as Record<string, unknown> | undefined;
    return row ? this.map(row) : undefined;
  }

  /**
   * Exécute un SELECT multi-rows et mappe chaque row vers `T`.
   */
  protected queryMany(
    sql: string,
    params: JSValue[] = [],
  ): T[] {
    const rows = this.db
      .prepare(sql)
      .all(params) as Record<string, unknown>[];
    return rows.map((r) => this.map(r));
  }

  // ── Helpers d'écriture ────────────────────────────────────────────────

  /**
   * Exécute une requête d'écriture (INSERT/UPDATE/DELETE) préparée.
   * @returns Le `RunResult` de node-sqlite3-wasm (utile pour `lastInsertRowid`).
   */
  protected execute(sql: string, params: JSValue[] = []): ReturnType<Database["run"]> {
    return this.db.prepare(sql).run(params);
  }

  // ── Helpers par défaut (opt-in) ───────────────────────────────────────

  /**
   * Récupère une entité par sa clé primaire `id`. Utilise `tableName`.
   * Les repos dont la PK n'est pas `id` ou qui ont un SELECT spécialisé
   * (ex: HistoryRepository sur snapshots hybrides) ne l'utilisent pas.
   */
  protected findById(id: string): T | undefined {
    return this.queryOne(
      `SELECT * FROM ${this.tableName} WHERE id = ?`,
      [id],
    );
  }

  /**
   * Supprime une entité par sa clé primaire `id`.
   */
  protected deleteById(id: string): void {
    this.execute(`DELETE FROM ${this.tableName} WHERE id = ?`, [id]);
  }

  // ── Mapping (à implémenter par chaque subclass) ───────────────────────

  /**
   * Transforme une row brute SQLite en entité typée `T`.
   * Centralise les coercions `String()` / `Number()` / `jsonColumn.read()`.
   */
  protected abstract map(row: Record<string, unknown>): T;
}

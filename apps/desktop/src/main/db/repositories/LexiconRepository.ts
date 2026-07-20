import type { LexiconEntry } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";
import { randomUUID } from "node:crypto";
import { withTransaction, jsonColumn } from "../utils.js";
import { BaseRepository } from "../base/BaseRepository.js";

/**
 * WS-1 (clean architecture) : hérite de `BaseRepository<LexiconEntry>`.
 * `getById`/`listByProject` gardent leur JOIN sur `lexicon_aliases`
 * (colonne agrégée `aliases_agg`) — `findById` basique ne ferait pas l'affaire.
 * `delete` délègue à `deleteById` (cascade aliases en DB).
 */
export class LexiconRepository extends BaseRepository<LexiconEntry> {
  constructor(db: Database) {
    super(db, "lexicon");
  }

  create(entry: LexiconEntry): void {
    // P0-3 fix : l'INSERT principal et la sync des aliases doivent être
    // atomiques. Sans transaction commune, un crash entre les deux laisserait
    // la colonne `aliases` inline à jour mais la table `lexicon_aliases`
    // désynchronisée (ou inversement). `withTransaction` garantit les deux
    // ou aucun.
    withTransaction(this.db, () => {
      this.execute(
        `
        INSERT INTO lexicon (id, project_id, term, translation, category, aliases, locked, forbidden, priority, description, notes, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
        [
          entry.id,
          entry.projectId,
          entry.term,
          entry.translation,
          entry.category,
          entry.aliases.join("|"),
          entry.locked ? 1 : 0,
          entry.forbidden ? entry.forbidden.join("|") : null,
          entry.priority,
          entry.description ?? null,
          entry.notes ?? null,
          jsonColumn.write(entry.metadata),
        ],
      );

      // SDD §6.3 : insérer les aliases dans la table séparée
      this.syncAliases(entry.id, entry.aliases);
    });
  }

  getById(id: string): LexiconEntry | null {
    return this.queryOne(
      `
      SELECT l.*, GROUP_CONCAT(la.alias, '|') AS aliases_agg
      FROM lexicon l
      LEFT JOIN lexicon_aliases la ON la.lexicon_id = l.id
      WHERE l.id = ?
      GROUP BY l.id
    `,
      [id],
    ) ?? null;
  }

  listByProject(projectId: string): LexiconEntry[] {
    return this.queryMany(
      `
      SELECT l.*, GROUP_CONCAT(la.alias, '|') AS aliases_agg
      FROM lexicon l
      LEFT JOIN lexicon_aliases la ON la.lexicon_id = l.id
      WHERE l.project_id = ?
      GROUP BY l.id
      ORDER BY l.priority DESC, l.term ASC
    `,
      [projectId],
    );
  }

  update(entry: LexiconEntry): void {
    // P0-3 fix : cf. create() — UPDATE principal + sync aliases atomiques.
    withTransaction(this.db, () => {
      this.execute(
        `
        UPDATE lexicon SET term = ?, translation = ?, category = ?, aliases = ?, locked = ?, forbidden = ?, priority = ?, description = ?, notes = ?, metadata = ?
        WHERE id = ?
      `,
        [
          entry.term,
          entry.translation,
          entry.category,
          entry.aliases.join("|"),
          entry.locked ? 1 : 0,
          entry.forbidden ? entry.forbidden.join("|") : null,
          entry.priority,
          entry.description ?? null,
          entry.notes ?? null,
          jsonColumn.write(entry.metadata),
          entry.id,
        ],
      );

      // SDD §6.3 : synchroniser les aliases (supprimer les anciens, insérer les nouveaux)
      this.syncAliases(entry.id, entry.aliases);
    });
  }

  delete(id: string): void {
    // Les aliases sont supprimées automatiquement via ON DELETE CASCADE
    this.deleteById(id);
  }

  /**
   * Import en masse (PR #89 — fix N+1 query bottleneck).
   *
   * Avant, l'IPC `lexicon:import` bouclait sur chaque entrée et appelait
   * `create()`/`update()`, chacun ouvrant SA PROPRE transaction via
   * `withTransaction` → N commits = N fsyncs disque. Sur un import de 500
   * entrées, c'était ~500 fsyncs synchrones.
   *
   * `importMany` ouvre UNE SEULE transaction pour tout le lot. Le caller
   * classifie chaque entrée en mode "create" ou "update" (via la lookup
   * existingIds qu'il fait déjà une fois). À l'intérieur de la transaction,
   * on prépare les statements INSERT/UPDATE/alias une fois et on les réutilise
   * (prepared-statement reuse = gain supplémentaire).
   *
   * @param batch Entrées à importer avec leur mode (create/update).
   * @returns Nombre d'entrées traitées.
   */
  importMany(batch: Array<{ entry: LexiconEntry; mode: "create" | "update" }>): number {
    if (batch.length === 0) {return 0;}
    // Préparer les statements UNE fois (réutilisés dans la boucle).
    const insertStmt = this.db.prepare(
      `INSERT INTO lexicon (id, project_id, term, translation, category, aliases, locked, forbidden, priority, description, notes, metadata)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );
    const updateStmt = this.db.prepare(
      `UPDATE lexicon SET term = ?, translation = ?, category = ?, aliases = ?, locked = ?, forbidden = ?, priority = ?, description = ?, notes = ?, metadata = ?
       WHERE id = ?`,
    );
    const deleteAliasesStmt = this.db.prepare(
      "DELETE FROM lexicon_aliases WHERE lexicon_id = ?",
    );
    const insertAliasStmt = this.db.prepare(
      "INSERT INTO lexicon_aliases (id, lexicon_id, alias) VALUES (?, ?, ?)",
    );

    let count = 0;
    withTransaction(this.db, () => {
      for (const { entry, mode } of batch) {
        const aliasesInline = entry.aliases.join("|");
        const forbidden = entry.forbidden ? entry.forbidden.join("|") : null;
        const metadata = jsonColumn.write(entry.metadata);
        if (mode === "create") {
          insertStmt.run([
            entry.id, entry.projectId, entry.term, entry.translation,
            entry.category, aliasesInline, entry.locked ? 1 : 0, forbidden,
            entry.priority, entry.description ?? null, entry.notes ?? null, metadata,
          ]);
        } else {
          updateStmt.run([
            entry.term, entry.translation, entry.category, aliasesInline,
            entry.locked ? 1 : 0, forbidden, entry.priority,
            entry.description ?? null, entry.notes ?? null, metadata, entry.id,
          ]);
        }
        // syncAliases inline (sans sa propre transaction — cf. note plus haut).
        deleteAliasesStmt.run([entry.id]);
        for (const alias of entry.aliases) {
          insertAliasStmt.run([randomUUID(), entry.id, alias]);
        }
        count++;
      }
    });
    return count;
  }

  /**
   * Synchronise les aliases d'une entrée du lexique dans la table lexicon_aliases.
   * Supprime tous les aliases existants pour cette entrée, puis insère les nouveaux.
   *
   * NOTE : cette méthode NE gère plus sa propre transaction (BEGIN/COMMIT).
   * Elle s'exécute dans la transaction ouverte par l'appelant (`create`/`update`)
   * via `withTransaction` — cf. fix P0-3. L'appeler hors transaction casserait
   * l'atomicité voulue.
   */
  private syncAliases(lexiconId: string, aliases: string[]): void {
    this.db
      .prepare("DELETE FROM lexicon_aliases WHERE lexicon_id = ?")
      .run([lexiconId]);
    const insert = this.db.prepare(
      "INSERT INTO lexicon_aliases (id, lexicon_id, alias) VALUES (?, ?, ?)",
    );
    for (const alias of aliases) {
      insert.run([randomUUID(), lexiconId, alias]);
    }
  }

  protected map(row: Record<string, unknown>): LexiconEntry {
    return {
      id: String(row.id),
      projectId: String(row.project_id),
      term: String(row.term),
      translation: String(row.translation),
      category: String(row.category),
      aliases: this.parseAliases(row),
      locked: Boolean(row.locked),
      forbidden: row.forbidden ? String(row.forbidden).split("|") : undefined,
      priority: Number(row.priority),
      description: row.description ? String(row.description) : undefined,
      notes: row.notes ? String(row.notes) : undefined,
      metadata: jsonColumn.read(row, "metadata") as Record<string, unknown> | undefined,
    };
  }

  /**
   * Parse les aliases depuis le résultat de la requête.
   * Priorité : colonne agrégée `aliases_agg` (JOIN lexicon_aliases),
   * fallback sur la colonne inline `aliases` (rétro-compatibilité).
   */
  private parseAliases(row: Record<string, unknown>): string[] {
    const agg = row.aliases_agg;
    if (agg !== null && agg !== undefined) {
      return String(agg).split("|");
    }
    return row.aliases ? String(row.aliases).split("|") : [];
  }
}

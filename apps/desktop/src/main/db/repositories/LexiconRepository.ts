import type { Database } from "node-sqlite3-wasm";
import type { LexiconEntry } from "@shared/types/index.js";
import { randomUUID } from "node:crypto";

export class LexiconRepository {
  constructor(private db: Database) {}

  create(entry: LexiconEntry): void {
    this.db
      .prepare(
        `
      INSERT INTO lexicon (id, project_id, term, translation, category, aliases, locked, forbidden, priority, description, notes, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      )
      .run([
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
        entry.metadata ? JSON.stringify(entry.metadata) : null,
      ]);

    // SDD §6.3 : insérer les aliases dans la table séparée
    this.syncAliases(entry.id, entry.aliases);
  }

  getById(id: string): LexiconEntry | null {
    const row = this.db
      .prepare(
        `
      SELECT l.*, GROUP_CONCAT(la.alias, '|') AS aliases_agg
      FROM lexicon l
      LEFT JOIN lexicon_aliases la ON la.lexicon_id = l.id
      WHERE l.id = ?
      GROUP BY l.id
    `,
      )
      .get([id]) as Record<string, unknown> | undefined;
    return row ? this.map(row) : null;
  }

  listByProject(projectId: string): LexiconEntry[] {
    const rows = this.db
      .prepare(
        `
      SELECT l.*, GROUP_CONCAT(la.alias, '|') AS aliases_agg
      FROM lexicon l
      LEFT JOIN lexicon_aliases la ON la.lexicon_id = l.id
      WHERE l.project_id = ?
      GROUP BY l.id
      ORDER BY l.priority DESC, l.term ASC
    `,
      )
      .all([projectId]) as Record<string, unknown>[];
    return rows.map((r) => this.map(r));
  }

  update(entry: LexiconEntry): void {
    this.db
      .prepare(
        `
      UPDATE lexicon SET term = ?, translation = ?, category = ?, aliases = ?, locked = ?, forbidden = ?, priority = ?, description = ?, notes = ?, metadata = ?
      WHERE id = ?
    `,
      )
      .run([
        entry.term,
        entry.translation,
        entry.category,
        entry.aliases.join("|"),
        entry.locked ? 1 : 0,
        entry.forbidden ? entry.forbidden.join("|") : null,
        entry.priority,
        entry.description ?? null,
        entry.notes ?? null,
        entry.metadata ? JSON.stringify(entry.metadata) : null,
        entry.id,
      ]);

    // SDD §6.3 : synchroniser les aliases (supprimer les anciens, insérer les nouveaux)
    this.syncAliases(entry.id, entry.aliases);
  }

  delete(id: string): void {
    // Les aliases sont supprimées automatiquement via ON DELETE CASCADE
    this.db.prepare("DELETE FROM lexicon WHERE id = ?").run([id]);
  }

  /**
   * Synchronise les aliases d'une entrée du lexique dans la table lexicon_aliases.
   * Supprime tous les aliases existants pour cette entrée, puis insère les nouveaux.
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

  private map(row: Record<string, unknown>): LexiconEntry {
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
      metadata: row.metadata
        ? (JSON.parse(String(row.metadata)) as Record<string, unknown>)
        : undefined,
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

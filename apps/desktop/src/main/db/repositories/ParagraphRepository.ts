import type { Paragraph } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";
import { withTransaction, jsonColumn } from "../utils.js";
import { BaseRepository } from "../base/BaseRepository.js";

/**
 * WS-1 (clean architecture) : hérite de `BaseRepository<Paragraph>` pour le
 * constructeur et `map`. Les méthodes `createMany`/`updateMany` conservent
 * leur pattern prepared-statement-reuse + `withTransaction` (optimisation
 * N-fsyncs → 1, volontairement pas absorbable par la base générique).
 */
export class ParagraphRepository extends BaseRepository<Paragraph> {
  constructor(db: Database) {
    super(db, "paragraphs");
  }

  createMany(chapterId: string, paragraphs: Paragraph[]): void {
    const insert = this.db.prepare(`
      INSERT INTO paragraphs (id, chapter_id, index_in_chapter, source_text, translated_text, status, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);
    withTransaction(this.db, () => {
      for (const p of paragraphs) {
        insert.run([
          p.id,
          chapterId,
          p.indexInChapter,
          p.sourceText,
          p.translatedText ?? null,
          p.status,
          jsonColumn.write(p.metadata),
        ]);
      }
    });
  }

  listByChapter(chapterId: string): Paragraph[] {
    return this.queryMany(
      "SELECT * FROM paragraphs WHERE chapter_id = ? ORDER BY index_in_chapter",
      [chapterId],
    );
  }

  update(paragraph: Paragraph): void {
    this.execute(
      "UPDATE paragraphs SET translated_text = ?, status = ?, metadata = ? WHERE id = ?",
      [
        paragraph.translatedText ?? null,
        paragraph.status,
        jsonColumn.write(paragraph.metadata),
        paragraph.id,
      ],
    );
  }

  updateMany(paragraphs: Paragraph[]): void {
    // Bug fix : inclure source_text dans la mise à jour. history:rollback et
    // history:rollback-partial appellent updateMany avec des paragraphes de
    // snapshot qui contiennent le sourceText d'origine ; sans ce champ, le
    // rollback restaurait translated_text/status mais gardait silencieusement
    // le source modifié — état incohérent disque/DB.
    const update = this.db.prepare(
      "UPDATE paragraphs SET source_text = ?, translated_text = ?, status = ?, metadata = ? WHERE id = ?",
    );
    withTransaction(this.db, () => {
      for (const p of paragraphs) {
        update.run([
          p.sourceText,
          p.translatedText ?? null,
          p.status,
          jsonColumn.write(p.metadata),
          p.id,
        ]);
      }
    });
  }

  /**
   * Upsert : insère les nouveaux paragraphes (ID inexistant) et met à jour
   * les existants. Utilisé par WorkflowEngine.applyAgentOutput après le
   * SplitAgent qui génère de nouveaux IDs (crypto.randomUUID) qui n'existent
   * pas encore en DB — un UPDATE simple silently n'affectait aucune ligne.
   *
   * Bug fix : avant ce fix, les paragraphes traduits n'étaient JAMAIS
   * persistés après un workflow single-chapter, car le split stage
   * remplaçait this.paragraphs avec de nouveaux IDs que updateMany
   * ne pouvait pas UPDATE (0 lignes affectées silencieusement).
   */
  upsertMany(chapterId: string, paragraphs: Paragraph[]): void {
    const insert = this.db.prepare(`
      INSERT INTO paragraphs (id, chapter_id, index_in_chapter, source_text, translated_text, status, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        source_text = excluded.source_text,
        translated_text = excluded.translated_text,
        status = excluded.status,
        metadata = excluded.metadata
    `);
    withTransaction(this.db, () => {
      for (const p of paragraphs) {
        insert.run([
          p.id,
          p.chapterId || chapterId,
          p.indexInChapter,
          p.sourceText,
          p.translatedText ?? null,
          p.status,
          jsonColumn.write(p.metadata),
        ]);
      }
    });
  }

  protected map(row: Record<string, unknown>): Paragraph {
    return {
      id: String(row.id),
      chapterId: String(row.chapter_id),
      indexInChapter: Number(row.index_in_chapter),
      sourceText: String(row.source_text),
      translatedText: row.translated_text
        ? String(row.translated_text)
        : undefined,
      preTranslatedText: row.pre_translated_text
        ? String(row.pre_translated_text)
        : undefined,
      status: String(row.status) as Paragraph["status"],
      metadata: jsonColumn.read(row, "metadata") as Record<string, unknown> | undefined,
    };
  }
}

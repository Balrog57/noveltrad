import type { Database } from "node-sqlite3-wasm";
import type { Paragraph } from "@shared/types/index.js";
import { withTransaction, jsonColumn } from "../utils.js";

export class ParagraphRepository {
  constructor(private db: Database) {}

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
    const rows = this.db
      .prepare(
        "SELECT * FROM paragraphs WHERE chapter_id = ? ORDER BY index_in_chapter",
      )
      .all([chapterId]) as Record<string, unknown>[];
    return rows.map((r) => this.map(r));
  }

  update(paragraph: Paragraph): void {
    this.db
      .prepare(
        "UPDATE paragraphs SET translated_text = ?, status = ?, metadata = ? WHERE id = ?",
      )
      .run([
        paragraph.translatedText ?? null,
        paragraph.status,
        jsonColumn.write(paragraph.metadata),
        paragraph.id,
      ]);
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

  private map(row: Record<string, unknown>): Paragraph {
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

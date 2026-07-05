import fs from "node:fs";
import type { TranslationMemoryMatch } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";
import { XMLParser, XMLBuilder } from "fast-xml-parser";
import levenshtein from "fast-levenshtein";

export class TranslationMemoryEngine {
  constructor(private db?: Database) {}

  setDatabase(db: Database): void {
    this.db = db;
  }

  exactMatch(text: string, projectId: string): string | null {
    if (!this.db) {return null;}
    const row = this.db
      .prepare(
        "SELECT target_text FROM translation_memory WHERE project_id = ? AND source_text = ?",
      )
      .get([projectId, text]) as { target_text: string } | undefined;
    return row?.target_text ?? null;
  }

  fuzzyMatches(
    text: string,
    projectId: string,
    limit = 5,
  ): TranslationMemoryMatch[] {
    if (!this.db) {return [];}
    const rows = this.db
      .prepare(
        "SELECT source_text, target_text, usage_count FROM translation_memory WHERE project_id = ?",
      )
      .all([projectId]) as Array<{
      source_text: string;
      target_text: string;
      usage_count: number;
    }>;
    return rows
      .map((r) => ({
        sourceText: r.source_text,
        targetText: r.target_text,
        usageCount: r.usage_count,
        similarity: 1 - levenshtein.get(text, r.source_text) / Math.max(text.length, r.source_text.length),
      }))
      .filter((m) => m.similarity > 0.85)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit);
  }

  store(
    source: string,
    target: string,
    projectId: string,
    sourceLanguage: string,
    targetLanguage: string,
  ): void {
    if (!this.db) {return;}
    const existing = this.db
      .prepare(
        "SELECT id FROM translation_memory WHERE project_id = ? AND source_text = ?",
      )
      .get([projectId, source]) as { id: string } | undefined;
    if (existing) {
      this.db
        .prepare(
          "UPDATE translation_memory SET target_text = ?, usage_count = usage_count + 1, last_used_at = ? WHERE id = ?",
        )
        .run([target, new Date().toISOString(), existing.id]);
    } else {
      this.db
        .prepare(
          "INSERT INTO translation_memory (id, project_id, source_text, target_text, source_language, target_language, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        )
        .run([
          crypto.randomUUID(),
          projectId,
          source,
          target,
          sourceLanguage,
          targetLanguage,
          new Date().toISOString(),
        ]);
    }
  }

  /**
   * Importe un fichier TMX 1.4 dans la mémoire de traduction (SDD §9.7).
   * Retourne le nombre d'entrées importées.
   */
  importTmx(filePath: string, projectId: string): number {
    if (!this.db) {return 0;}
    const xml = fs.readFileSync(filePath, "utf-8");
    const parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: "@_",
    });
    const parsed = parser.parse(xml);
    const tmx = parsed?.tmx;
    if (!tmx) {throw new Error("Fichier TMX invalide : balise <tmx> introuvable.");}

    const body = tmx.body;
    const tus = body?.tu;
    if (!tus) {return 0;}

    const tuArray = Array.isArray(tus) ? tus : [tus];
    let imported = 0;

    for (const tu of tuArray) {
      const tuvs = tu?.tuv;
      if (!tuvs) {continue;}

      const tuvArray = Array.isArray(tuvs) ? tuvs : [tuvs];
      let sourceText = "";
      let targetText = "";
      let sourceLang = "";
      let targetLang = "";

      for (const tuv of tuvArray) {
        const lang = (tuv["@_xml:lang"] ?? tuv["@_lang"]) as string | undefined;
        const seg = tuv?.seg;
        const text = typeof seg === "string" ? seg : "";
        if (lang) {
          if (!sourceText) {
            sourceText = text;
            sourceLang = lang;
          } else {
            targetText = text;
            targetLang = lang;
          }
        }
      }

      if (sourceText && targetText) {
        this.store(sourceText, targetText, projectId, sourceLang, targetLang);
        imported++;
      }
    }

    return imported;
  }

  /**
   * Exporte la mémoire de traduction au format TMX 1.4 (SDD §9.7).
   */
  exportTmx(filePath: string, projectId: string): void {
    if (!this.db) {return;}
    const rows = this.db
      .prepare(
        "SELECT source_text, target_text, source_language, target_language FROM translation_memory WHERE project_id = ?",
      )
      .all([projectId]) as Array<{
      source_text: string;
      target_text: string;
      source_language: string;
      target_language: string;
    }>;

    const builder = new XMLBuilder({
      ignoreAttributes: false,
      attributeNamePrefix: "@_",
      format: true,
    });

    const tmxObj: Record<string, unknown> = {
      tmx: {
        "@_version": "1.4",
        header: {
          "@_creationtool": "NovelTrad 2.0",
          "@_segtype": "sentence",
          "@_o-tmf": "NovelTradTM",
        },
        body: {
          tu: rows.map((row) => ({
            tuv: [
              { "@_xml:lang": row.source_language, seg: row.source_text },
              { "@_xml:lang": row.target_language, seg: row.target_text },
            ],
          })),
        },
      },
    };

    // Si une seule entrée, fast-xml-parser n'encapsule pas dans un tableau
    if (rows.length === 1) {
      (tmxObj.tmx as Record<string, unknown>).body = {
        tu: {
          tuv: [
            { "@_xml:lang": rows[0].source_language, seg: rows[0].source_text },
            { "@_xml:lang": rows[0].target_language, seg: rows[0].target_text },
          ],
        },
      };
    }

    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n${builder.build(tmxObj)}`;
    fs.writeFileSync(filePath, xml, "utf-8");
  }
}

import fs from "node:fs";
import type { TranslationMemoryMatch } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";
import { XMLParser, XMLBuilder } from "fast-xml-parser";
import levenshtein from "fast-levenshtein";
import tokenizer from "sbd";
import MiniSearch from "minisearch";

export class TranslationMemoryEngine {
  /** MiniSearch index for two-pass fuzzy matching (rebuilt at startup) */
  private miniSearch: MiniSearch;

  constructor(private db?: Database) {
    this.miniSearch = new MiniSearch({
      fields: ["source_text"],
      storeFields: ["id", "source_text", "target_text", "similarity"],
      searchOptions: { fuzzy: 0.2, prefix: true },
    });
  }

  setDatabase(db: Database): void {
    this.db = db;
  }

  // ─── Normalization ───────────────────────────────────────────────────────

  /**
   * Normalise un texte pour la recherche exacte :
   * trim, lowercase, strip punctuation courante.
   */
  private normalize(text: string): string {
    return text
      .trim()
      .toLowerCase()
      .replace(
        /[.,!?;:'"«»()[\]{}《》「」【】、。，！？；：""''\u2018\u2019\u201c\u201d\u2013\u2014-]/g,
        "",
      )
      .replace(/\s+/g, " ")
      .trim();
  }

  // ─── Sentence segmentation ───────────────────────────────────────────────

  /**
   * Segmente un texte en phrases en utilisant sbd (Sentence Boundary Detection).
   * Pour les textes CJK, un split supplémentaire sur la ponctuation CJK est appliqué.
   */
  segmentSentences(text: string): string[] {
    if (!text.trim()) {return [];}
    try {
      const sbdSentences = tokenizer.sentences(text, {});
      const sentences = sbdSentences.flatMap((s: string) =>
        s.split(/[。！？]+/).filter((p: string) => p.trim().length > 0),
      );
      return sentences
        .map((s: string) => s.trim())
        .filter(Boolean);
    } catch {
      // Fallback: split on sentence-ending punctuation
      return text
        .split(/[.!?。！？\n]+/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
    }
  }

  // ─── Exact match (normalized) ────────────────────────────────────────────

  /**
   * Recherche une correspondance exacte normalisée.
   * @param text Texte source à chercher.
   * @param projectId ID du projet, ou null/undefined pour chercher uniquement les entrées globales.
   * @returns La traduction si trouvée, null sinon.
   */
  exactMatch(text: string, projectId?: string | null): string | null {
    if (!this.db) {return null;}
    const hash = this.normalize(text);

    if (projectId) {
      // Chercher dans les entrées du projet seulement
      const row = this.db
        .prepare(
          "SELECT target_text FROM translation_memory WHERE normalized_hash = ? AND project_id = ? AND is_global = 0",
        )
        .get([hash, projectId]) as { target_text: string } | undefined;
      return row?.target_text ?? null;
    }

    // Chercher dans les entrées globales (projectId est null)
    const globalRow = this.db
      .prepare(
        "SELECT target_text FROM translation_memory WHERE normalized_hash = ? AND is_global = 1",
      )
      .get([hash]) as { target_text: string } | undefined;

    return globalRow?.target_text ?? null;
  }

  // ─── Fuzzy matches (two-pass: MiniSearch prefilter + Levenshtein refine) ─

  /**
   * Recherche des correspondances floues avec un préfiltre SQL, un
   * index MiniSearch, puis un raffinement Levenshtein.
   * @param text Texte source à chercher.
   * @param projectId ID du projet, ou null/undefined pour chercher les entrées globales.
   * @param limit Nombre maximum de résultats.
   */
  fuzzyMatches(
    text: string,
    projectId?: string | null,
    limit = 5,
  ): TranslationMemoryMatch[] {
    if (!this.db) {return [];}

    try {
      // 1. Préfiltre SQL : récupérer jusqu'à 200 candidats pertinents
      const candidates = this.fuzzyPrefilter(text, projectId, 200);
      if (candidates.length === 0) {return [];}

      // 2. MiniSearch fuzzy search sur les candidats
      const miniSearch = new MiniSearch({
        fields: ["source_text"],
        storeFields: ["source_text", "target_text"],
        searchOptions: { fuzzy: 0.2, prefix: true },
      });
      miniSearch.addAll(
        candidates.map((c, i) => ({
          id: String(i),
          source_text: c.sourceText,
          target_text: c.targetText,
        })),
      );

      const msResults = miniSearch.search(text, { fuzzy: 0.2, prefix: true });
      const topCandidates = msResults.slice(0, 30);

      // 3. Levenshtein refine sur le top 30
      const scored = topCandidates.map((r) => {
        const sourceText = (r as { source_text?: string }).source_text ?? "";
        const sim =
          1 -
          levenshtein.get(text, sourceText) /
            Math.max(text.length, sourceText.length, 1);
        return {
          sourceText,
          targetText: (r as { target_text?: string }).target_text ?? "",
          usageCount: 0,
          similarity: sim,
        };
      });

      return scored
        .filter((m) => m.similarity > 0.85)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, limit);
    } catch {
      // Fallback : Levenshtein direct si MiniSearch échoue
      return this.fuzzyFallback(text, projectId, limit);
    }
  }

  /**
   * Préfiltre SQL pour la recherche floue.
   * Retourne jusqu'à `max` candidats de la TM projet (ou globale).
   */
  private fuzzyPrefilter(
    text: string,
    projectId?: string | null,
    max = 200,
  ): TranslationMemoryMatch[] {
    if (!this.db) {return [];}

    // Extraire le terme le plus long (>= 3 caractères) pour le préfiltre LIKE
    const terms = text.match(/\b\w{3,}\b/g);
    const searchTerm = terms
      ? terms.sort((a, b) => b.length - a.length)[0]
      : text.substring(0, 20);
    const likePattern = `%${searchTerm}%`;

    let rows: Array<{
      source_text: string;
      target_text: string;
      usage_count: number;
    }>;

    if (projectId) {
      rows = this.db
        .prepare(
          `SELECT source_text, target_text, usage_count FROM translation_memory
           WHERE source_text LIKE ? AND project_id = ?
           LIMIT ?`,
        )
        .all([likePattern, projectId, max]) as Array<{
        source_text: string;
        target_text: string;
        usage_count: number;
      }>;
    } else {
      rows = this.db
        .prepare(
          `SELECT source_text, target_text, usage_count FROM translation_memory
           WHERE source_text LIKE ? AND is_global = 1
           LIMIT ?`,
        )
        .all([likePattern, max]) as Array<{
        source_text: string;
        target_text: string;
        usage_count: number;
      }>;
    }

    return rows.map((r) => ({
      sourceText: r.source_text,
      targetText: r.target_text,
      usageCount: r.usage_count,
      similarity: 0,
    }));
  }

  /**
   * Fallback Levenshtein direct si MiniSearch échoue.
   */
  private fuzzyFallback(
    text: string,
    projectId?: string | null,
    limit = 5,
  ): TranslationMemoryMatch[] {
    if (!this.db) {return [];}

    const rows = this.db
      .prepare(
        projectId
          ? "SELECT source_text, target_text, usage_count FROM translation_memory WHERE project_id = ?"
          : "SELECT source_text, target_text, usage_count FROM translation_memory WHERE is_global = 1",
      )
      .all(projectId ? [projectId] : []) as Array<{
      source_text: string;
      target_text: string;
      usage_count: number;
    }>;

    return rows
      .map((r) => ({
        sourceText: r.source_text,
        targetText: r.target_text,
        usageCount: r.usage_count,
        similarity:
          1 -
          levenshtein.get(text, r.source_text) /
            Math.max(text.length, r.source_text.length),
      }))
      .filter((m) => m.similarity > 0.85)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit);
  }

  // ─── 5-tier priority (SDD §9.4) ──────────────────────────────────────────

  /**
   * Cascade de priorité 5 niveaux (SDD §9.4) :
   * 1. Project exact match (normalisé)
   * 2. Project fuzzy match (top 1)
   * 3. Global exact match
   * 4. Global fuzzy match (top 1)
   * 5. Aucun match → null (le caller peut essayer RAG/LLM)
   */
  findBestMatch(
    text: string,
    projectId: string,
  ): TranslationMemoryMatch | null {
    // Tier 1 : Project exact match
    const projectExact = this.exactMatch(text, projectId);
    if (projectExact) {
      return {
        sourceText: text,
        targetText: projectExact,
        usageCount: 0,
        similarity: 1,
      };
    }

    // Tier 2 : Project fuzzy match (top 1)
    const projectFuzzy = this.fuzzyMatches(text, projectId, 1);
    if (projectFuzzy.length > 0) {
      return projectFuzzy[0];
    }

    // Tier 3 : Global exact match
    const globalExact = this.exactMatch(text, null);
    if (globalExact) {
      return {
        sourceText: text,
        targetText: globalExact,
        usageCount: 0,
        similarity: 1,
      };
    }

    // Tier 4 : Global fuzzy match (top 1)
    const globalFuzzy = this.fuzzyMatches(text, null, 1);
    if (globalFuzzy.length > 0) {
      return globalFuzzy[0];
    }

    // Tier 5 : Aucun match — le caller utilise RAG/LLM
    return null;
  }

  // ─── Global TM ───────────────────────────────────────────────────────────

  /**
   * Pro promeut une entrée projet → globale.
   * Insère ou met à jour une entrée avec is_global = 1 et project_id = NULL.
   */
  promoteToGlobal(
    sourceText: string,
    translatedText: string,
    sourceLanguage?: string,
    targetLanguage?: string,
  ): void {
    if (!this.db) {return;}
    const hash = this.normalize(sourceText);

    const existing = this.db
      .prepare(
        "SELECT id FROM translation_memory WHERE normalized_hash = ? AND is_global = 1",
      )
      .get([hash]) as { id: string } | undefined;

    if (existing) {
      this.db
        .prepare(
          "UPDATE translation_memory SET target_text = ?, usage_count = usage_count + 1, last_used_at = ? WHERE id = ?",
        )
        .run([translatedText, new Date().toISOString(), existing.id]);
    } else {
      this.db
        .prepare(
          `INSERT INTO translation_memory (id, project_id, source_text, target_text, source_language, target_language, normalized_hash, segment_index, is_global, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .run([
          crypto.randomUUID(),
          null,
          sourceText,
          translatedText,
          sourceLanguage ?? "",
          targetLanguage ?? "",
          hash,
          0,
          1,
          new Date().toISOString(),
        ]);
    }
  }

  // ─── Store (sentence-level) ──────────────────────────────────────────────

  /**
   * Stocke une entrée en mémoire de traduction.
   * Le texte source est segmenté en phrases ; chaque phrase est stockée
   * individuellement avec son normalized_hash et segment_index.
   */
  store(
    source: string,
    target: string,
    projectId: string,
    sourceLanguage: string,
    targetLanguage: string,
  ): void {
    if (!this.db) {return;}

    const sentences = this.segmentSentences(source);
    const targetSentences = this.segmentSentences(target);

    // Si la segmentation ne donne qu'une phrase, on stocke simplement
    if (sentences.length <= 1) {
      this.storeSingle(source, target, projectId, sourceLanguage, targetLanguage, 0);
      return;
    }

    // Plusieurs phrases : stocker chaque paire phrase→traduction
    for (let i = 0; i < sentences.length; i++) {
      const targetSentence = targetSentences[i] ?? targetSentences[targetSentences.length - 1] ?? target;
      this.storeSingle(sentences[i], targetSentence, projectId, sourceLanguage, targetLanguage, i);
    }
  }

  /**
   * Stocke une entrée TM unique (une phrase).
   */
  private storeSingle(
    source: string,
    target: string,
    projectId: string,
    sourceLanguage: string,
    targetLanguage: string,
    segmentIndex: number,
  ): void {
    if (!this.db) {return;}
    const hash = this.normalize(source);

    const existing = this.db
      .prepare(
        "SELECT id FROM translation_memory WHERE project_id = ? AND normalized_hash = ? AND segment_index = ?",
      )
      .get([projectId, hash, segmentIndex]) as { id: string } | undefined;

    if (existing) {
      this.db
        .prepare(
          "UPDATE translation_memory SET target_text = ?, usage_count = usage_count + 1, last_used_at = ? WHERE id = ?",
        )
        .run([target, new Date().toISOString(), existing.id]);
    } else {
      this.db
        .prepare(
          `INSERT INTO translation_memory (id, project_id, source_text, target_text, source_language, target_language, normalized_hash, segment_index, is_global, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .run([
          crypto.randomUUID(),
          projectId,
          source,
          target,
          sourceLanguage,
          targetLanguage,
          hash,
          segmentIndex,
          0,
          new Date().toISOString(),
        ]);
    }
  }

  // ─── TMX import / export (unchanged) ────────────────────────────────────

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

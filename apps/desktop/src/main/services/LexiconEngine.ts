import type {
  LexiconEntry,
  LexiconApplyResult,
  Substitution,
} from "@shared/types/index.js";
import type { CandidateTerm } from "@shared/types/index.js";

export class LexiconEngine {
  private entries: Map<string, LexiconEntry> = new Map();

  load(entries: LexiconEntry[]): void {
    this.entries.clear();
    for (const entry of entries) {
      this.entries.set(entry.term.toLowerCase(), entry);
      for (const alias of entry.aliases) {
        this.entries.set(alias.toLowerCase(), entry);
      }
    }
  }

  apply(text: string, entries?: LexiconEntry[]): LexiconApplyResult {
    const substitutions: Substitution[] = [];
    const sorted = entries
      ? [...entries].sort((a, b) => b.term.length - a.term.length)
      : Array.from(this.entries.values()).sort(
          (a, b) => b.term.length - a.term.length,
        );

    let result = text;
    for (const entry of sorted) {
      const pattern = new RegExp(
        `\\b${this.escapeRegExp(entry.term)}\\b`,
        "gi",
      );
      result = result.replace(pattern, (match) => {
        substitutions.push({
          before: match,
          after: entry.translation,
          locked: entry.locked,
        });
        return entry.translation;
      });
    }

    return { text: result, substitutions };
  }

  /**
   * Extrait les termes candidats d'un texte source.
   * Algorithme SDD §10.8 :
   * - Chinois : groupes de 2-6 caractères, occurrences ≥ 3
   * - Autres langues : n-grammes de 1-4 mots, occurrences ≥ 3
   * Retourne le top 50 trié par fréquence décroissante.
   */
  extractCandidates(text: string, language: string): CandidateTerm[] {
    const isChinese = language === "zh";
    const minOccurrences = 3;
    const frequency = new Map<string, number>();

    if (isChinese) {
      // Nettoyer : retirer ponctuation et espaces
      const cleaned = text.replace(
        /[\s，。！？；：“”‘’「」『』、…\.\?,;:!"'\s]+/g,
        "",
      );
      // Extraire groupes de 2-6 caractères chinois
      for (let len = 2; len <= 6; len++) {
        for (let i = 0; i <= cleaned.length - len; i++) {
          const gram = cleaned.slice(i, i + len);
          // Ignorer si contient des caractères non-chinois
          if (!/^[\u4e00-\u9fff]+$/.test(gram)) continue;
          frequency.set(gram, (frequency.get(gram) ?? 0) + 1);
        }
      }
    } else {
      // Nettoyer et tokeniser par mots
      const words = text
        .toLowerCase()
        .replace(/[^\w\sàâäéèêëîïôöùûüçœæ'-]/g, " ")
        .split(/\s+/)
        .filter((w) => w.length >= 2);

      // N-grammes de 1-4 mots
      for (let n = 1; n <= 4; n++) {
        for (let i = 0; i <= words.length - n; i++) {
          const gram = words.slice(i, i + n).join(" ");
          frequency.set(gram, (frequency.get(gram) ?? 0) + 1);
        }
      }
    }

    // Filtrer, trier, retourner top 50
    const candidates: CandidateTerm[] = [];
    for (const [term, occurrences] of frequency) {
      if (occurrences >= minOccurrences) {
        candidates.push({
          term,
          occurrences,
          suggestedCategory: this.guessCategory(term, language),
        });
      }
    }

    candidates.sort((a, b) => b.occurrences - a.occurrences);
    return candidates.slice(0, 50);
  }

  /** Devine une catégorie suggérée basée sur le terme */
  private guessCategory(term: string, language: string): string {
    // Catégories basées sur des patterns communs
    if (language === "zh") {
      if (/[姓名称号]/.test(term)) return "personnage";
      if (/[国城山湖海河州府镇村]/.test(term)) return "lieu";
      if (/[功法术技招式]/.test(term)) return "technique";
      if (/[剑刀枪弓棍斧锤鞭]/.test(term)) return "arme";
      if (/[丹丹药草花]/.test(term)) return "objet";
    } else {
      const lower = term.toLowerCase();
      if (
        /\b(king|queen|prince|princess|lord|lady|emperor|master|disciple|sect)\b/.test(
          lower,
        )
      )
        return "personnage";
      if (
        /\b(city|village|kingdom|mountain|river|palace|temple|cave|forest)\b/.test(
          lower,
        )
      )
        return "lieu";
      if (/\b(sword|blade|spear|bow|staff|dagger|axe|hammer)\b/.test(lower))
        return "arme";
      if (
        /\b(skill|technique|art|spell|magic|formation|pill|elixir)\b/.test(
          lower,
        )
      )
        return "technique";
    }
    return "general";
  }

  /**
   * Exporte les entrées du lexique dans le format spécifié.
   * Formats supportés : csv, json, tsv.
   */
  exportEntries(
    entries: LexiconEntry[],
    format: "csv" | "json" | "tsv",
  ): string {
    switch (format) {
      case "json":
        return JSON.stringify(
          entries.map((e) => ({
            term: e.term,
            translation: e.translation,
            category: e.category,
            aliases: e.aliases,
            locked: e.locked,
            forbidden: e.forbidden ?? [],
            priority: e.priority,
            description: e.description ?? "",
            notes: e.notes ?? "",
            gender: e.gender ?? "",
            pronunciation: e.pronunciation ?? "",
          })),
          null,
          2,
        );

      case "csv":
      case "tsv": {
        const sep = format === "csv" ? "," : "\t";
        const headers = [
          "term",
          "translation",
          "category",
          "aliases",
          "locked",
          "forbidden",
          "priority",
          "description",
          "notes",
          "gender",
          "pronunciation",
        ].join(sep);
        const rows = entries.map((e) =>
          [
            this.escapeCsv(e.term, sep),
            this.escapeCsv(e.translation, sep),
            this.escapeCsv(e.category, sep),
            this.escapeCsv(e.aliases.join(";"), sep),
            e.locked ? "1" : "0",
            this.escapeCsv((e.forbidden ?? []).join(";"), sep),
            String(e.priority),
            this.escapeCsv(e.description ?? "", sep),
            this.escapeCsv(e.notes ?? "", sep),
            this.escapeCsv(e.gender ?? "", sep),
            this.escapeCsv(e.pronunciation ?? "", sep),
          ].join(sep),
        );
        return [headers, ...rows].join("\n");
      }
    }
  }

  /** Échappe une valeur pour CSV/TSV */
  private escapeCsv(value: string, separator: string): string {
    if (
      value.includes(separator) ||
      value.includes('"') ||
      value.includes("\n")
    ) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  }

  private escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
}

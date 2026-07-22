import type { ProjectDatabase } from "../../db/connection.js";
import { TRANSLATE_SYSTEM_PROMPT } from "./translate.system.js";
import { PROOFREAD_SYSTEM_PROMPT } from "./proofread.system.js";
import { LEXICON_SYSTEM_PROMPT } from "./lexicon.system.js";
import { VALIDATE_SYSTEM_PROMPT } from "./validate.system.js";

/**
 * Map des identifiants de prompts vers leurs constantes TS de fallback.
 * v3 : pipeline 4-stages (translate, proofread, glossary=lexicon, validate).
 * Les anciens prompts (split/pre_translate/grammar/style/polish/consistency/
 * qa/export) ont été supprimés avec leurs stages.
 */
const PROMPT_MAP: Record<string, string> = {
  "translate": TRANSLATE_SYSTEM_PROMPT,
  "proofread": PROOFREAD_SYSTEM_PROMPT,
  "glossary": LEXICON_SYSTEM_PROMPT,
  "validate": VALIDATE_SYSTEM_PROMPT,
};

/**
 * PromptLoader — Service additif de résolution de prompts avec override DB.
 *
 * Les agents continuent d'importer leurs prompts directement (comportement par
 * défaut). PromptLoader offre une capacité d'override runtime via une table
 * `prompts` en base de données, sans modifier le comportement des agents.
 *
 * SDD §25 — Prompt Book, extension pour overrides utilisateur.
 */
export class PromptLoader {
  constructor(private db: ProjectDatabase) {}

  /**
   * Résout un prompt par son identifiant.
   *
   * 1. Interroge la DB : `SELECT content FROM prompts WHERE id = ? AND active = 1
   *    ORDER BY version DESC LIMIT 1`.
   * 2. Si trouvé → retourne le contenu DB (runtime override).
   * 3. Si absent (pas de ligne, prompt désactivé) ou erreur DB → fallback
   *    sur la constante TypeScript importée depuis les fichiers *.system.ts.
   *
   * @throws {Error} Si le promptId est inconnu (ni DB, ni fallback TS).
   */
  async load(promptId: string): Promise<string> {
    // 1. Essai DB
    try {
      const row = this.db
        .prepare(
          "SELECT content FROM prompts WHERE id = ? AND active = 1 ORDER BY version DESC LIMIT 1",
        )
        .get([promptId]) as { content: string } | undefined;

      if (row?.content) {
        return row.content;
      }
    } catch {
      // Erreur DB (table inexistante, etc.) → fallback silencieux
    }

    // 2. Fallback constante TS
    const fallback = PROMPT_MAP[promptId];
    if (fallback !== undefined) {
      return fallback;
    }

    throw new Error(`Prompt inconnu : ${promptId}`);
  }

  /**
   * Retourne la liste des prompts personnalisés en DB (dernière version active
   * par ID). Ces prompts sont ceux qui override les constantes TS.
   */
  listCustomPrompts(): Array<{ id: string; content: string; version: number }> {
    try {
      const rows = this.db
        .prepare(
          "SELECT id, content, version FROM prompts WHERE active = 1 ORDER BY id, version DESC",
        )
        .all() as Array<{ id: string; content: string; version: number }>;

      // Ne garder que la version la plus récente de chaque ID
      const latest: Record<string, { id: string; content: string; version: number }> = {};
      for (const row of rows) {
        if (!latest[row.id]) {
          latest[row.id] = row;
        }
      }
      return Object.values(latest);
    } catch {
      return [];
    }
  }

  /**
   * Réinitialise un prompt à sa valeur par défaut en désactivant toutes les
   * versions actives en DB. Les versions désactivées sont conservées en base
   * mais ne sont plus chargées par `load()`.
   */
  resetToDefault(promptId: string): void {
    this.db
      .prepare("UPDATE prompts SET active = 0 WHERE id = ? AND active = 1")
      .run([promptId]);
  }
}

import { logger } from "../../utils/logger.js";

/**
 * WS-3 (clean architecture) : extrait de AiRouter.tryParseJson.
 *
 * Fonction PURE (aucun état), isolable et testable. Tentatives de parsing
 * d'une chaîne brute en JSON avec 3 stratégies de fallback :
 *   1. JSON.parse() direct
 *   2. Extraction depuis des fences markdown ```json ... ```
 *   3. Réparation basique (trailing commas, single quotes)
 *
 * @returns Le JSON parsé, ou `null` si toutes les stratégies échouent.
 */
export function tryParseJson(raw: string): unknown {
  // 1. Essai direct
  try {
    return JSON.parse(raw);
  } catch {
    // continue
  }

  // 2. Extraction depuis des fences markdown ```json ... ```
  const fenceMatch = raw.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (fenceMatch) {
    try {
      return JSON.parse(fenceMatch[1].trim());
    } catch {
      // continue
    }
  }

  // 3. Réparation basique des erreurs JSON courantes
  try {
    let fixed = raw.trim();
    // Supprimer les trailing commas avant } ou ]
    fixed = fixed.replace(/,(\s*[}\]])/g, "$1");
    // Remplacer les single quotes par des double quotes (approche simple)
    // Note : ne gère pas les apostrophes à l'intérieur des chaînes
    fixed = fixed.replace(/'/g, '"');
    const result = JSON.parse(fixed);
    logger.warn(
      "[AiRouter] JSON réparé (fallback single quotes / trailing commas)",
    );
    return result;
  } catch {
    // continue
  }

  return null;
}

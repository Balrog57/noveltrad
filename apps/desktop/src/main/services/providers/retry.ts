import { logger } from "../../utils/logger.js";

/**
 * Helpers partagés pour la gestion du retry des providers IA.
 *
 * P2-7 refactor : la logique de sleep `Retry-After` était dupliquée entre
 * OllamaProvider.handle429 (lit Retry-After depuis Response.headers) et
 * OpenAiCompatibleProvider.handle429IfApplicable (lit depuis APIError.headers).
 * Le calcul `Number.isFinite(seconds) && seconds > 0 && seconds < 300` +
 * setTimeout + log était copié-collé. Centralisé ici.
 */

/**
 * Borde la durée de sleep pour éviter qu'un serveur malveillant ou bogué
 * ne nous fasse attendre indéfiniment via un Retry-After énorme.
 */
const MAX_RETRY_AFTER_SECONDS = 300;

/**
 * Attend la durée indiquée par un header `Retry-After` (en secondes) si elle
 * est valide et raisonnable (0 < s < 300). Sinon, ne dort pas — l'appelant
 * retombera sur le backoff par défaut de pRetry.
 *
 * @param retryAfterHeaderValue Valeur brute du header (string ou undefined).
 * @param logPrefix Préfixe pour le log (ex: "[OllamaProvider]").
 */
export async function sleepForRetryAfter(
  retryAfterHeaderValue: string | undefined | null,
  logPrefix: string,
): Promise<void> {
  if (!retryAfterHeaderValue) {return;}
  const seconds = Number.parseInt(retryAfterHeaderValue, 10);
  if (Number.isFinite(seconds) && seconds > 0 && seconds < MAX_RETRY_AFTER_SECONDS) {
    logger.warn(`${logPrefix} HTTP 429, attente Retry-After: ${seconds}s`);
    await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
  }
}

/**
 * Erreur retryable levée après gestion d'un 429. Ce n'est PAS une AbortError
 * afin que le pRetry de l'AiRouter retraite la requête (les AbortError
 * interrompent immédiatement le retry).
 */
export const RETRYABLE_429_ERROR_MESSAGE = "HTTP 429 Too Many Requests";

/**
 * Construit l'erreur retryable post-429. Factory pour garder le message
 * centralisé (les tests assertent sur ce texte exact).
 */
export function retryable429Error(): Error {
  return new Error(RETRYABLE_429_ERROR_MESSAGE);
}

import type { PromptLoader } from "../prompts/PromptLoader.js";

/**
 * WS-3 (clean architecture) : extrait de AiRouter ( résolution de prompts ).
 *
 * T5 fix : résout un prompt avec override DB optionnel. Les agents appellent
 * cette méthode avec leur identifiant de prompt et la constante TS par défaut.
 * Si un PromptLoader est enregistré et qu'une version active existe en DB,
 * elle remplace la constante. Sinon, la constante TS est retournée
 * (comportement inchangé).
 *
 * Isoler cette responsabilité permet aux agents de dépendre d'un collaborateur
 * dédié plutôt que du AiRouter (qui n'a pas vocation à gérer les prompts).
 */
export class PromptResolver {
  private loader?: PromptLoader;

  setLoader(loader: PromptLoader): void {
    this.loader = loader;
  }

  async resolve(promptId: string, defaultContent: string): Promise<string> {
    if (!this.loader) {
      return defaultContent;
    }
    try {
      return await this.loader.load(promptId);
    } catch {
      // Prompt inconnu du loader → fallback constante TS
      return defaultContent;
    }
  }
}

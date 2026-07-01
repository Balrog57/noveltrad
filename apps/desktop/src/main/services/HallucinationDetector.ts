import type { HallucinationReport } from "@shared/types/index.js";

/**
 * SDD §12.6 : Détecteur d'hallucinations local.
 *
 * Approche locale (sans IA) : comparer les entités nommées du texte source
 * et du texte cible pour vérifier qu'aucun nom propre n'a été inventé.
 *
 * Trois vérifications principales :
 * 1. Entités nommées inventées : noms propres présents dans la cible mais
 *    absents du source (potentiellement inventés par le modèle).
 * 2. Références suspectes : chapitres/personnages mentionnés dans la cible
 *    sans être dans le source.
 * 3. Score d'hallucination dérivé du nombre d'entités inventées.
 *
 * Note : cette approche est heuristique et produit des faux positifs
 * (ex: un nom traduit phonétiquement peut ne pas matcher). Elle est
 * complémentaire du score `hallucination` du QualityChecker.
 */
export class HallucinationDetector {
  /**
   * Détecte les hallucinations potentielles en comparant les entités nommées
   * du texte source et du texte cible.
   *
   * @param sourceText Texte source (langue d'origine)
   * @param targetText Texte cible (traduction)
   * @param sourceLanguage Code langue source (ex: "zh", "ja", "en")
   * @param targetLanguage Code langue cible (ex: "fr")
   * @returns Rapport d'hallucination avec score et listes d'entités suspectes
   */
  detect(
    sourceText: string,
    targetText: string,
    sourceLanguage: string,
    targetLanguage: string,
  ): HallucinationReport {
    const sourceEntities = this.extractNamedEntities(
      sourceText,
      sourceLanguage,
    );
    const targetEntities = this.extractNamedEntities(
      targetText,
      targetLanguage,
    );

    // Entités inventées : présentes dans la cible mais absentes du source
    const inventedEntities = this.findInventedEntities(
      sourceEntities,
      targetEntities,
      sourceLanguage,
      targetLanguage,
    );

    // Références suspectes : mentions de "chapitre" ou numéros dans la cible
    // sans correspondance dans le source
    const suspiciousReferences = this.findSuspiciousReferences(
      sourceText,
      targetText,
    );

    // Construction des avertissements détaillés
    const warnings: string[] = [];
    for (const entity of inventedEntities) {
      warnings.push(
        `Entité nommée potentiellement inventée : "${entity}" (absente du source)`,
      );
    }
    for (const ref of suspiciousReferences) {
      warnings.push(
        `Référence suspecte : "${ref}" mentionnée dans la cible sans correspondance dans le source`,
      );
    }

    // Score d'hallucination : 100 = aucune hallucination, 0 = beaucoup
    // Pénalité : 10 points par entité inventée, 15 par référence suspecte
    const penalty =
      inventedEntities.length * 10 + suspiciousReferences.length * 15;
    const score = Math.max(0, 100 - penalty);

    return {
      score,
      inventedEntities,
      suspiciousReferences,
      warnings,
    };
  }

  /**
   * Extrait les entités nommées d'un texte selon la langue.
   *
   * Pour les langues asiatiques (zh, ja, ko) : extrait les séquences de
   * caractères CJK qui ne sont pas des mots communs.
   * Pour les langues latines (en, fr, etc.) : extrait les mots commençant
   * par une majuscule (noms propres) et les mots composés.
   *
   * @param text Texte à analyser
   * @param language Code langue
   * @returns Ensemble d'entités nommées (en minuscules pour comparaison)
   */
  extractNamedEntities(text: string, language: string): Set<string> {
    if (!text) return new Set();

    const entities = new Set<string>();

    if (this.isCjkLanguage(language)) {
      // Pour les langues CJK : extraire les séquences de caractères CJK
      // (noms propres chinois/japonais sont souvent des caractères CJK spécifiques)
      const cjkPattern =
        /[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+/g;
      const matches = text.match(cjkPattern);
      if (matches) {
        for (const match of matches) {
          // Ignorer les séquences trop courtes (1 caractère = souvent un mot commun)
          if (match.length >= 2) {
            entities.add(match.toLowerCase());
          }
        }
      }
    }

    // Pour toutes les langues : extraire les mots commençant par une majuscule
    // (noms propres en latin, mais aussi noms translittérés)
    const capitalizedPattern =
      /\b[A-ZÀ-Ý][a-zà-ÿA-ZÀ-Ý]+(?:[-\s][A-ZÀ-Ý][a-zà-ÿA-ZÀ-Ý]+)*\b/g;
    const capitalizedMatches = text.match(capitalizedPattern);
    if (capitalizedMatches) {
      for (const match of capitalizedMatches) {
        // Ignorer les mots communs en début de phrase (heuristique simple)
        if (!this.isCommonWord(match.toLowerCase(), language)) {
          entities.add(match.toLowerCase());
        }
      }
    }

    return entities;
  }

  /**
   * Trouve les entités de la cible qui ne sont pas dans le source.
   *
   * Pour les paires de langues différentes (ex: zh → fr), les entités ne
   * correspondent pas directement (noms translittérés). On utilise donc
   * une heuristique : si le source et la cible sont dans des écritures
   * différentes (CJK vs latin), on ne compare que les entités latines
   * (qui pourraient être des noms propres non traduits).
   *
   * @param sourceEntities Entités du source
   * @param targetEntities Entités de la cible
   * @param sourceLanguage Langue source
   * @param targetLanguage Langue cible
   * @returns Liste des entités potentiellement inventées
   */
  findInventedEntities(
    sourceEntities: Set<string>,
    targetEntities: Set<string>,
    sourceLanguage: string,
    targetLanguage: string,
  ): string[] {
    const invented: string[] = [];
    const sourceIsCjk = this.isCjkLanguage(sourceLanguage);
    const targetIsCjk = this.isCjkLanguage(targetLanguage);

    for (const entity of targetEntities) {
      // Si l'entité est présente dans le source, ce n'est pas une invention
      if (sourceEntities.has(entity)) continue;

      // Si les deux langues sont CJK, comparaison directe
      if (sourceIsCjk && targetIsCjk) {
        invented.push(entity);
        continue;
      }

      // Si le source est CJK et la cible est latine, on ne peut pas comparer
      // directement les noms (translittération). On signale seulement les
      // entités latines qui ressemblent à des noms propres non traduits.
      if (sourceIsCjk && !targetIsCjk) {
        // Heuristique : si l'entité contient des caractères latins et
        // n'est pas un mot commun français, c'est potentiellement inventé
        if (/^[a-zà-ÿ]+$/i.test(entity) && entity.length >= 3) {
          invented.push(entity);
        }
        continue;
      }

      // Si le source est latin et la cible est CJK, les entités CJK de la
      // cible qui ne sont pas dans le source sont suspectes
      if (!sourceIsCjk && targetIsCjk) {
        invented.push(entity);
        continue;
      }

      // Si les deux langues sont latines, comparaison directe
      if (!sourceIsCjk && !targetIsCjk) {
        invented.push(entity);
      }
    }

    return invented;
  }

  /**
   * Trouve les références suspectes dans la cible : mentions de "chapitre",
   * numéros de chapitre, ou références à des personnages qui n'apparaissent
   * pas dans le source.
   *
   * @param sourceText Texte source
   * @param targetText Texte cible
   * @returns Liste des références suspectes
   */
  findSuspiciousReferences(sourceText: string, targetText: string): string[] {
    const suspicious: string[] = [];

    // Détecter les mentions de "chapitre N" dans la cible
    const chapterPattern = /chapitre\s+(\d+|[ivxlcdm]+)/gi;
    const targetChapters = targetText.match(chapterPattern) ?? [];
    const sourceChapters =
      sourceText.match(/第?\s*\d+\s*章?|chapter\s+\d+|chapitre\s+\d+/gi) ?? [];

    for (const ref of targetChapters) {
      // Extraire le numéro
      const numMatch = ref.match(/(\d+|[ivxlcdm]+)/i);
      const num = numMatch?.[1]?.toLowerCase();
      if (!num) continue;

      // Vérifier si ce numéro apparaît dans le source
      const sourceHasNum = sourceChapters.some((sc) =>
        sc.toLowerCase().includes(num),
      );
      if (!sourceHasNum) {
        suspicious.push(ref);
      }
    }

    return suspicious;
  }

  /**
   * Vérifie si une langue utilise l'écriture CJK (chinois, japonais, coréen).
   */
  private isCjkLanguage(language: string): boolean {
    const cjkLanguages = ["zh", "ja", "ko", "chinese", "japanese", "korean"];
    return cjkLanguages.includes(language.toLowerCase());
  }

  /**
   * Vérifie si un mot est un mot commun dans la langue donnée.
   * Liste non exhaustive — sert d'heuristique pour filtrer les faux positifs.
   */
  private isCommonWord(word: string, language: string): boolean {
    const commonWords: Record<string, string[]> = {
      fr: [
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "et",
        "ou",
        "mais",
        "donc",
        "or",
        "ni",
        "car",
        "que",
        "qui",
        "quoi",
        "dont",
        "où",
        "ce",
        "cette",
        "ces",
        "mon",
        "ton",
        "son",
        "ma",
        "ta",
        "sa",
        "mes",
        "tes",
        "ses",
        "notre",
        "votre",
        "leur",
        "nous",
        "vous",
        "ils",
        "elles",
        "il",
        "elle",
        "on",
        "en",
        "y",
        "à",
        "au",
        "aux",
        "dans",
        "sur",
        "sous",
        "pour",
        "par",
        "avec",
        "sans",
        "vers",
        "chez",
        "entre",
        "pendant",
        "avant",
        "après",
        "depuis",
        "ici",
        "là",
        "tout",
        "tous",
        "toute",
        "toutes",
        "rien",
        "quelque",
        "quelques",
        "autre",
        "autres",
        "même",
        "mêmes",
        "tel",
        "telle",
        "comment",
        "pourquoi",
        "quand",
        "combien",
        "the",
        "chapter",
      ],
      en: [
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "so",
        "because",
        "if",
        "when",
        "where",
        "what",
        "who",
        "why",
        "how",
        "this",
        "that",
        "these",
        "those",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "us",
        "them",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "from",
        "by",
        "of",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "can",
        "will",
        "just",
        "should",
        "now",
        "chapter",
      ],
    };

    const lang = language.toLowerCase();
    const words = commonWords[lang] ?? commonWords["en"];
    return words.includes(word);
  }
}

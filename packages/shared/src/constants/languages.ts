/**
 * Langues supportées par NovelTrad.
 *
 * Source unique de vérité pour les menus déroulants de sélection de langue
 * (SettingsView, HomeView, WizardDialog). Évite la divergence des listes
 * hardcoded et les typos sur les codes à 2 lettres.
 */

export interface LanguageOption {
  /** Code ISO 639-1 (ex. "zh", "ja", "fr") */
  code: string;
  /** Libellé affiché dans l'UI, avec script natif si pertinent */
  label: string;
}

/** Langues sources supportées (traduction depuis).
 *
 * NovelTrad s'appuie sur un LLM pour la traduction : toute langue est
 * techniquement supportée. Cette liste couvre les langues majeures
 * (chinois, japonais, coréen, langues européennes principales). Le detecteur
 * `franc` (Vol 05 §5.7) reconnait un spectre plus large encore.
 */
export const SOURCE_LANGUAGES: LanguageOption[] = [
  // CJK (cas d'usage principal : web-novel)
  { code: "zh", label: "Chinois (中文)" },
  { code: "ja", label: "Japonais (日本語)" },
  { code: "ko", label: "Coréen (한국어)" },
  // Langues européennes
  { code: "fr", label: "Français" },
  { code: "en", label: "Anglais" },
  { code: "es", label: "Espagnol (Español)" },
  { code: "de", label: "Allemand (Deutsch)" },
  { code: "it", label: "Italien (Italiano)" },
  { code: "pt", label: "Portugais (Português)" },
  { code: "ru", label: "Russe (Русский)" },
  { code: "nl", label: "Néerlandais (Nederlands)" },
  { code: "pl", label: "Polonais (Polski)" },
  { code: "tr", label: "Turc (Türkçe)" },
  // Autres langues majeures
  { code: "ar", label: "Arabe (العربية)" },
  { code: "hi", label: "Hindi (हिन्दी)" },
  { code: "vi", label: "Vietnamien (Tiếng Việt)" },
  { code: "th", label: "Thaï (ไทย)" },
  { code: "id", label: "Indonésien (Bahasa Indonesia)" },
];

/** Langues cibles supportées (traduction vers). */
export const TARGET_LANGUAGES: LanguageOption[] = [
  { code: "fr", label: "Français" },
  { code: "en", label: "Anglais" },
];

"""Immutable ISO 639-1 language list with FR/EN labels (SDD 9.2).

The list is embedded locally; no network service is queried. Codes are
exactly two lowercase ASCII letters. `und` and `mul` are reserved and
refused as target languages.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import LanguageCode


@dataclass(frozen=True, slots=True)
class LanguageEntry:
    code: LanguageCode
    label_fr: str
    label_en: str


LANGUAGES: tuple[LanguageEntry, ...] = (
    LanguageEntry("aa", "Afar", "Afar"),
    LanguageEntry("ab", "Abkhaze", "Abkhaz"),
    LanguageEntry("af", "Afrikaans", "Afrikaans"),
    LanguageEntry("am", "Amharique", "Amharic"),
    LanguageEntry("ar", "Arabe", "Arabic"),
    LanguageEntry("az", "Azéri", "Azerbaijani"),
    LanguageEntry("be", "Biélorusse", "Belarusian"),
    LanguageEntry("bg", "Bulgare", "Bulgarian"),
    LanguageEntry("bn", "Bengali", "Bengali"),
    LanguageEntry("bs", "Bosnien", "Bosnian"),
    LanguageEntry("ca", "Catalan", "Catalan"),
    LanguageEntry("ceb", "Cebuano", "Cebuano"),
    LanguageEntry("cs", "Tchèque", "Czech"),
    LanguageEntry("cy", "Gallois", "Welsh"),
    LanguageEntry("da", "Danois", "Danish"),
    LanguageEntry("de", "Allemand", "German"),
    LanguageEntry("el", "Grec", "Greek"),
    LanguageEntry("en", "Anglais", "English"),
    LanguageEntry("eo", "Espéranto", "Esperanto"),
    LanguageEntry("es", "Espagnol", "Spanish"),
    LanguageEntry("et", "Estonien", "Estonian"),
    LanguageEntry("eu", "Basque", "Basque"),
    LanguageEntry("fa", "Persan", "Persian"),
    LanguageEntry("fi", "Finnois", "Finnish"),
    LanguageEntry("fil", "Filipino", "Filipino"),
    LanguageEntry("fr", "Français", "French"),
    LanguageEntry("ga", "Irlandais", "Irish"),
    LanguageEntry("gl", "Galicien", "Galician"),
    LanguageEntry("gu", "Gujarati", "Gujarati"),
    LanguageEntry("ha", "Haoussa", "Hausa"),
    LanguageEntry("he", "Hébreu", "Hebrew"),
    LanguageEntry("hi", "Hindi", "Hindi"),
    LanguageEntry("hr", "Croate", "Croatian"),
    LanguageEntry("ht", "Créole haïtien", "Haitian Creole"),
    LanguageEntry("hu", "Hongrois", "Hungarian"),
    LanguageEntry("hy", "Arménien", "Armenian"),
    LanguageEntry("id", "Indonésien", "Indonesian"),
    LanguageEntry("ig", "Igbo", "Igbo"),
    LanguageEntry("is", "Islandais", "Icelandic"),
    LanguageEntry("it", "Italien", "Italian"),
    LanguageEntry("ja", "Japonais", "Japanese"),
    LanguageEntry("jv", "Javanais", "Javanese"),
    LanguageEntry("ka", "Géorgien", "Georgian"),
    LanguageEntry("kk", "Kazakh", "Kazakh"),
    LanguageEntry("km", "Khmer", "Khmer"),
    LanguageEntry("kn", "Kannada", "Kannada"),
    LanguageEntry("ko", "Coréen", "Korean"),
    LanguageEntry("ku", "Kurde", "Kurdish"),
    LanguageEntry("ky", "Kirghize", "Kyrgyz"),
    LanguageEntry("la", "Latin", "Latin"),
    LanguageEntry("lb", "Luxembourgeois", "Luxembourgish"),
    LanguageEntry("lo", "Lao", "Lao"),
    LanguageEntry("lt", "Lituanien", "Lithuanian"),
    LanguageEntry("lv", "Letton", "Latvian"),
    LanguageEntry("mg", "Malgache", "Malagasy"),
    LanguageEntry("mi", "Maori", "Maori"),
    LanguageEntry("mk", "Macédonien", "Macedonian"),
    LanguageEntry("ml", "Malayalam", "Malayalam"),
    LanguageEntry("mn", "Mongol", "Mongolian"),
    LanguageEntry("mr", "Marathi", "Marathi"),
    LanguageEntry("ms", "Malais", "Malay"),
    LanguageEntry("mt", "Maltais", "Maltese"),
    LanguageEntry("my", "Birman", "Burmese"),
    LanguageEntry("ne", "Népalais", "Nepali"),
    LanguageEntry("nl", "Néerlandais", "Dutch"),
    LanguageEntry("no", "Norvégien", "Norwegian"),
    LanguageEntry("ny", "Chichewa", "Chichewa"),
    LanguageEntry("pa", "Pendjabi", "Punjabi"),
    LanguageEntry("pl", "Polonais", "Polish"),
    LanguageEntry("ps", "Pachto", "Pashto"),
    LanguageEntry("pt", "Portugais", "Portuguese"),
    LanguageEntry("ro", "Roumain", "Romanian"),
    LanguageEntry("ru", "Russe", "Russian"),
    LanguageEntry("rw", "Kinyarwanda", "Kinyarwanda"),
    LanguageEntry("sd", "Sindhi", "Sindhi"),
    LanguageEntry("si", "Cingalais", "Sinhala"),
    LanguageEntry("sk", "Slovaque", "Slovak"),
    LanguageEntry("sl", "Slovène", "Slovenian"),
    LanguageEntry("so", "Somali", "Somali"),
    LanguageEntry("sq", "Albanais", "Albanian"),
    LanguageEntry("sr", "Serbe", "Serbian"),
    LanguageEntry("st", "Sotho du Sud", "Southern Sotho"),
    LanguageEntry("su", "Soundanais", "Sundanese"),
    LanguageEntry("sv", "Suédois", "Swedish"),
    LanguageEntry("sw", "Swahili", "Swahili"),
    LanguageEntry("ta", "Tamoul", "Tamil"),
    LanguageEntry("te", "Télougou", "Telugu"),
    LanguageEntry("tg", "Tadjik", "Tajik"),
    LanguageEntry("th", "Thaï", "Thai"),
    LanguageEntry("tl", "Tagalog", "Tagalog"),
    LanguageEntry("tr", "Turc", "Turkish"),
    LanguageEntry("uk", "Ukrainien", "Ukrainian"),
    LanguageEntry("ur", "Ourdou", "Urdu"),
    LanguageEntry("uz", "Ouzbek", "Uzbek"),
    LanguageEntry("vi", "Vietnamien", "Vietnamese"),
    LanguageEntry("xh", "Xhosa", "Xhosa"),
    LanguageEntry("yi", "Yiddish", "Yiddish"),
    LanguageEntry("yo", "Yoruba", "Yoruba"),
    LanguageEntry("zh", "Chinois", "Chinese"),
    LanguageEntry("zu", "Zoulou", "Zulu"),
)


def language_label(code: LanguageCode, language: str) -> str:
    """Return the FR or EN label for a code, or the code itself."""
    for entry in LANGUAGES:
        if entry.code == code:
            return entry.label_fr if language == "fr" else entry.label_en
    return str(code)


def is_valid_target(code: LanguageCode) -> bool:
    return code not in ("und", "mul") and any(e.code == code for e in LANGUAGES)

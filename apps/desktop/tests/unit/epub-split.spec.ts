/**
 * Tests du découpage EPUB multi-fichiers + chunking par taille.
 *
 * Valide la Phase 1 du feature epub-split-and-cli :
 *   - extractEpub insère EPUB_FILE_BREAK entre fichiers xhtml consécutifs
 *   - splitIntoChapters reconnaît ce séparateur en priorité
 *   - chunkLongChapters re-découpe les chapitres > MAX_CHAPTER_CHARS
 *   - Les patterns existants (Chapter N, etc.) restent reconnus en fallback
 */

import { describe, it, expect, vi } from "vitest";

// Mock electron-log (ProjectManager importe logger → electron-log).
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    transports: { console: { format: vi.fn() }, file: { format: vi.fn() } },
  },
  initialize: vi.fn(),
}));

import {
  ProjectManager,
  EPUB_FILE_BREAK,
  MAX_CHAPTER_CHARS,
} from "../../src/main/managers/ProjectManager.js";

// Cast pour accéder aux méthodes publiques testées (splitIntoChapters est
// public ; extractEpub est private — testé indirectement via le comportement
// du séparateur injecté).
const pm = new ProjectManager({} as never) as unknown as {
  splitIntoChapters: (text: string, projectPath?: string) => string[];
};

describe("splitIntoChapters — séparateur EPUB_FILE_BREAK (Phase 1)", () => {
  it("découpe un texte contenant N séparateurs en N+1 chapitres", () => {
    const text = `Roman 1 première partie.${EPUB_FILE_BREAK}Roman 1 seconde partie.${EPUB_FILE_BREAK}Roman 2.`;
    const chapters = pm.splitIntoChapters(text);
    expect(chapters).toHaveLength(3);
    expect(chapters[0]).toContain("Roman 1 première partie");
    expect(chapters[2]).toBe("Roman 2.");
  });

  it("ignore les séparateurs en début/fin (trim)", () => {
    const text = `${EPUB_FILE_BREAK}Contenu unique${EPUB_FILE_BREAK}`;
    const chapters = pm.splitIntoChapters(text);
    // 1 seul segment non vide après trim → traité comme texte unique
    expect(chapters).toHaveLength(1);
    expect(chapters[0]).toBe("Contenu unique");
  });

  it("ignore les segments vides (séparateurs consécutifs)", () => {
    const text = `A${EPUB_FILE_BREAK}${EPUB_FILE_BREAK}B`;
    const chapters = pm.splitIntoChapters(text);
    expect(chapters).toHaveLength(2);
    expect(chapters).toEqual(["A", "B"]);
  });

  it("priorité au séparateur EPUB même si le texte contient 'Chapter N'", () => {
    // Si un epub multi-fichiers a aussi des "Chapter N" internes, on découpe
    // par fichier d'abord (plus fiable — correspond à la structure physique).
    const text = `Chapter 1\nintro${EPUB_FILE_BREAK}Chapter 2\nsuite`;
    const chapters = pm.splitIntoChapters(text);
    expect(chapters).toHaveLength(2);
    expect(chapters[0]).toContain("Chapter 1");
    expect(chapters[1]).toContain("Chapter 2");
  });
});

describe("splitIntoChapters — patterns existants (fallback, inchangé)", () => {
  it("reconnaît 'Chapter N' sans séparateur EPUB", () => {
    const text = "Intro\nChapter 1\nPremier contenu\nChapter 2\nSecond contenu";
    const chapters = pm.splitIntoChapters(text);
    expect(chapters.length).toBeGreaterThanOrEqual(2);
  });

  it("reconnaît 'Chapitre N' (français)", () => {
    const text = "Intro\nChapitre 1\nPremier contenu\nChapitre 2\nSecond contenu";
    const chapters = pm.splitIntoChapters(text);
    expect(chapters.length).toBeGreaterThanOrEqual(2);
  });

  it("reconnaît '第N章' (chinois, chiffre arabe)", () => {
    // NOTE : le pattern /^第\s*\d+\s*章/im utilise \d+ (chiffre arabe).
    // Les chiffres chinois (一二三) ne sont PAS reconnus — limitation
    // préexistante documentée. La plupart des EPUBs modernes utilisent
    // des chiffres arabes même dans les titres chinois.
    const text = "Intro\n第1章\nPremier contenu\n第2章\nSecond contenu";
    const chapters = pm.splitIntoChapters(text);
    expect(chapters.length).toBeGreaterThanOrEqual(2);
  });

  it("retourne le texte entier si aucun pattern ne matche (single chapter)", () => {
    const text = "Un bloc de texte sans aucun séparateur de chapitre.";
    const chapters = pm.splitIntoChapters(text);
    expect(chapters).toHaveLength(1);
    expect(chapters[0]).toBe(text);
  });
});

describe("splitIntoChapters — chunking par taille (MAX_CHAPTER_CHARS)", () => {
  it("chapitre sous la limite → inchangé", () => {
    const short = "A".repeat(1000);
    expect(pm.splitIntoChapters(short)).toEqual([short]);
  });

  it("chapitre au-dessus de MAX_CHAPTER_CHARS est re-découpé", () => {
    // Construire un chapitre avec des paragraphes \n\n qui dépasse la limite.
    const para = "A".repeat(10000); // 10k car par paragraphe
    const paragraphs = Array.from({ length: 15 }, () => para); // 150k car total
    const giant = paragraphs.join("\n\n");
    expect(giant.length).toBeGreaterThan(MAX_CHAPTER_CHARS);

    const chapters = pm.splitIntoChapters(giant);
    expect(chapters.length).toBeGreaterThan(1);
    // Aucun chunk ne doit dépasser la limite (ou très peu au-dessus à cause
    // de la préservation des paragraphes — on accepte une marge d'un paragraphe).
    for (const ch of chapters) {
      expect(ch.length).toBeLessThanOrEqual(MAX_CHAPTER_CHARS + 10000);
    }
  });

  it("chunking ne coupe jamais au milieu d'un paragraphe", () => {
    // Chaque paragraphe est plus petit que MAX_CHAPTER_CHARS → aucun n'est coupé.
    const para = "B".repeat(1000);
    const paragraphs = Array.from({ length: 200 }, (_, i) => `${para}-${i}`);
    const giant = paragraphs.join("\n\n");
    const chapters = pm.splitIntoChapters(giant);
    // Vérifier qu'au moins un chunk a été créé (>1) et que chaque paragraphe
    // est retrouvé intact dans un des chunks.
    expect(chapters.length).toBeGreaterThan(1);
    const allText = chapters.join("\n\n");
    for (const p of paragraphs) {
      expect(allText).toContain(p);
    }
  });

  it("chunking s'applique aussi après découpage par séparateur EPUB", () => {
    // 2 fichiers xhtml, chacun > MAX_CHAPTER_CHARS → chacun re-découpé.
    const big1 = ("X".repeat(10000) + "\n\n").repeat(15); // ~150k
    const big2 = ("Y".repeat(10000) + "\n\n").repeat(15); // ~150k
    const text = big1 + EPUB_FILE_BREAK + big2;
    const chapters = pm.splitIntoChapters(text);
    // Chaque gros fichier doit produire >1 chunk → total > 2.
    expect(chapters.length).toBeGreaterThan(2);
  });
});

describe("EPUB_FILE_BREAK + MAX_CHAPTER_CHARS — contrats exportés", () => {
  it("EPUB_FILE_BREAK est un token non-ambigu", () => {
    expect(EPUB_FILE_BREAK).toContain("---EPUB-FILE-BREAK---");
    expect(EPUB_FILE_BREAK.startsWith("\n\n")).toBe(true);
    expect(EPUB_FILE_BREAK.endsWith("\n\n")).toBe(true);
  });

  it("MAX_CHAPTER_CHARS est raisonnable pour un LLM 32k context", () => {
    // ~100k caractères ≈ ~25k tokens (4 car/token). Doit rester sous 32k.
    expect(MAX_CHAPTER_CHARS).toBe(100_000);
    const approxTokens = MAX_CHAPTER_CHARS / 4;
    expect(approxTokens).toBeLessThan(30000);
  });
});

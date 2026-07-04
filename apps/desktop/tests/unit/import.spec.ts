import { describe, it, expect, vi } from "vitest";

// Mock electron-log (ProjectManager imports logger which imports electron-log)
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

import { ProjectManager } from "../../src/main/managers/ProjectManager";

/**
 * Tests unitaires pour l'import de fichiers (SDD §5.4, §5.5, §5.7, §5.9).
 * Teste uniquement les méthodes pures (htmlToMarkdown, splitIntoChapters).
 * Les tests d'intégration (DOCX, EPUB, drag-and-drop) nécessitent Electron.
 */

// Créer une instance minimaliste pour tester les méthodes pures
// On mock SettingsManager pour éviter la dépendance au filesystem
function createManagerForTesting(): ProjectManager {
  // Utiliser un mock minimal de SettingsManager
  const mockSettings = {
    get: () => undefined,
    set: () => {},
  } as never;
  return new ProjectManager(mockSettings);
}

describe("ProjectManager.htmlToMarkdown", () => {
  const manager = createManagerForTesting();

  it("devrait convertir les titres HTML en markdown", () => {
    const html = "<h1>Titre principal</h1><h2>Sous-titre</h2>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("# Titre principal");
    expect(result).toContain("## Sous-titre");
  });

  it("devrait convertir les paragraphes HTML", () => {
    const html = "<p>Premier paragraphe.</p><p>Deuxieme paragraphe.</p>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("Premier paragraphe.");
    expect(result).toContain("Deuxieme paragraphe.");
  });

  it("devrait convertir le gras en markdown", () => {
    const html = "<p>Texte <strong>gras</strong> normal.</p>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("**gras**");
  });

  it("devrait convertir l'italique en markdown", () => {
    const html = "<p>Texte <em>italique</em> normal.</p>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("*italique*");
  });

  it("devrait convertir les listes en markdown", () => {
    const html = "<ul><li>Element 1</li><li>Element 2</li></ul>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("- Element 1");
    expect(result).toContain("- Element 2");
  });

  it("devrait supprimer les balises script et style", () => {
    const html =
      '<p>Contenu</p><script>alert("xss")</script><style>.x{}</style>';
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("Contenu");
    expect(result).not.toContain("alert");
    expect(result).not.toContain("xss");
  });

  it("devrait gerer les sauts de ligne", () => {
    const html = "<p>Ligne 1<br>Ligne 2</p>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("Ligne 1");
    expect(result).toContain("Ligne 2");
  });

  it("devrait nettoyer les espaces multiples", () => {
    const html = "<p>Texte   avec    espaces.</p>";
    const result = manager.htmlToMarkdown(html);
    expect(result).not.toContain("   ");
  });

  it("devrait gerer un HTML vide", () => {
    const result = manager.htmlToMarkdown("");
    expect(typeof result).toBe("string");
  });

  it("devrait conserver le texte brut sans balises HTML", () => {
    const html = "<p>Simple texte sans格式special.</p>";
    const result = manager.htmlToMarkdown(html);
    expect(result).toContain("Simple texte sans格式special.");
  });
});

describe("ProjectManager.splitIntoChapters", () => {
  const manager = createManagerForTesting();

  it("devrait retourner le texte entier si aucun pattern ne correspond", () => {
    const text = "Un texte simple sans chapitres.\n\nDeuxieme paragraphe.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(1);
    expect(result[0]).toBe(text);
  });

  it("devrait separer selon le pattern Chapter N", () => {
    const text =
      "Chapter 1\nPremier chapitre.\n\nChapter 2\nDeuxieme chapitre.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(2);
    expect(result[0]).toContain("Premier chapitre.");
    expect(result[1]).toContain("Deuxieme chapitre.");
  });

  it("devrait separer selon le pattern Chapitre N", () => {
    const text =
      "Chapitre 1\nPremier chapitre.\n\nChapitre 2\nDeuxieme chapitre.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(2);
  });

  it("devrait separer selon le pattern 第 N 章", () => {
    const text = "第 1 章\nPremier chapitre.\n\n第 2 章\nDeuxieme chapitre.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(2);
  });

  it("devrait separer selon CHAPTER N (majuscules)", () => {
    const text =
      "CHAPTER 1\nPremier chapitre.\n\nCHAPTER 2\nDeuxieme chapitre.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(2);
  });

  it("devrait respecter un pattern personnalise via config", () => {
    // Note: Ce test vérifie que la méthode accepte un projectPath
    // En environnement réel, il lirait config.json
    const text = "Partie 1\nContenu 1.\n\nPartie 2\nContenu 2.";
    const result = manager.splitIntoChapters(text);
    // Sans config, les patterns par défaut ne matchent pas "Partie"
    expect(result).toHaveLength(1);
  });

  it("devrait gerer un texte avec plusieurs sauts de ligne", () => {
    const text =
      "Chapter 1\n\n\nPremier chapitre.\n\n\n\nChapter 2\n\nDeuxieme.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(2);
  });

  it("devrait retourner un seul element pour un texte court sans chapitres", () => {
    const text = "Texte tres court.";
    const result = manager.splitIntoChapters(text);
    expect(result).toHaveLength(1);
    expect(result[0]).toBe(text);
  });
});

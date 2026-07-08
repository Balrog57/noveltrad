import { describe, it, expect } from "vitest";
import { SOURCE_LANGUAGES, TARGET_LANGUAGES } from "@shared/constants/languages.js";

// ---------------------------------------------------------------------------
// Constante LANGUAGES partagée — source unique pour les menus déroulants
// de sélection de langue (SettingsView, HomeView, WizardDialog).
// ---------------------------------------------------------------------------

describe("LANGUAGES constant (shared)", () => {
  it("SOURCE_LANGUAGES contient les langues CJK + européennes majeures", () => {
    const codes = SOURCE_LANGUAGES.map((l) => l.code);
    // Cas d'usage principal (web-novel)
    expect(codes).toContain("zh");
    expect(codes).toContain("ja");
    expect(codes).toContain("ko");
    // Langues européennes demandées
    expect(codes).toContain("fr");
    expect(codes).toContain("en");
    expect(codes).toContain("es");
    expect(codes).toContain("de");
    expect(codes).toContain("it");
    expect(codes).toContain("pt");
    expect(codes).toContain("ru");

    for (const lang of SOURCE_LANGUAGES) {
      expect(lang.label.length).toBeGreaterThan(0);
      expect(lang.code.length).toBe(2);
    }
    // Au moins 15 langues sources
    expect(SOURCE_LANGUAGES.length).toBeGreaterThanOrEqual(15);
  });

  it("TARGET_LANGUAGES contient fr et en avec labels non vides", () => {
    const codes = TARGET_LANGUAGES.map((l) => l.code);
    expect(codes).toContain("fr");
    expect(codes).toContain("en");

    for (const lang of TARGET_LANGUAGES) {
      expect(lang.label.length).toBeGreaterThan(0);
      expect(lang.code.length).toBe(2);
    }
  });
});

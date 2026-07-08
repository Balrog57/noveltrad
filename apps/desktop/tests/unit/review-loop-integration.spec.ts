import { describe, it, expect, vi } from "vitest";
import fs from "node:fs";
import path from "node:path";

// Mock electron-log before any imports that trigger the logger
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    transports: { file: { level: false }, console: { level: false } },
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { ReviewAgent } from "../../src/main/services/agents/ReviewAgent";
import { ReviseAgent } from "../../src/main/services/agents/ReviseAgent";
import { SummarizerAgent } from "../../src/main/services/agents/SummarizerAgent";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { Paragraph } from "@shared/types/index.js";

// ---------------------------------------------------------------------------
// Fixture : chapitre anglais (domaine public, style roman)
// ---------------------------------------------------------------------------

const FIXTURE_PATH = path.resolve(__dirname, "../fixtures/sample_en_chapter.md");
const SOURCE_TEXT = fs.readFileSync(FIXTURE_PATH, "utf-8");

/** Construit les paragraphes depuis le markdown (chaque § séparé par ligne vide) */
function buildParagraphs(source: string): Paragraph[] {
  // Normaliser les CRLF (Windows) avant le split
  const normalized = source.replace(/\r\n/g, "\n");
  const blocks = normalized.split(/\n\n+/).filter((b) => b.trim().length > 0);
  return blocks.map((block, i) => ({
    id: `p${i}`,
    chapterId: "ch1",
    indexInChapter: i,
    sourceText: block.replace(/^#\s+.*\n/, "").trim(),
    // Traduction volontairement imparfaite pour tester le review
    translatedText: `[FR] ${block.replace(/^#\s+.*\n/, "").trim().slice(0, 40)}...`,
    status: "translated" as const,
  }));
}

const CONFIG = { providerId: "ollama", model: "qwen3.5:9b" };

// ---------------------------------------------------------------------------
// Intégration : la boucle Review → Revise enchaîne correctement les données
// ---------------------------------------------------------------------------

describe("Boucle Review→Revise — intégration (fixture en→fr)", () => {
  it("la fixture en→fr se charge et produit 8 paragraphes", () => {
    expect(SOURCE_TEXT.length).toBeGreaterThan(500);
    const paragraphs = buildParagraphs(SOURCE_TEXT);
    expect(paragraphs.length).toBeGreaterThanOrEqual(8);
  });

  it("Review produit un rapport, Revise l'applique sur le texte", async () => {
    const paragraphs = buildParagraphs(SOURCE_TEXT);
    const translatedText = paragraphs.map((p) => p.translatedText ?? "").join("\n\n");

    // Mock LLM : Review retourne 2 issues, Revise retourne le texte corrigé
    const mockRouter = {
      chat: vi
        .fn()
        // 1er appel (Review)
        .mockResolvedValueOnce(
          JSON.stringify({
            issues: [
              {
                paragraphIndex: 0,
                severity: "high",
                category: "fidelity",
                original: "[FR] The wind howled across...",
                suggestion: "Le vent hurlait au bord de la falaise.",
                reason: "Literal placeholder; source conveys atmospheric tension.",
              },
              {
                paragraphIndex: 3,
                severity: "medium",
                category: "style",
                original: "[FR] I'm not wrong...",
                suggestion: "Je ne me trompe pas, je suis juste en avance.",
                reason: "Original punchline lost.",
              },
            ],
            summary: "Two issues: fidelity and style in dialogue.",
          }),
        )
        // 2e appel (Revise)
        .mockResolvedValueOnce(
          "Le vent hurlait au bord de la falaise.\n\nElle chuchota.\n\nKael trébucha.\n\nJe ne me trompe pas, je suis juste en avance.",
        ),
      tryParseJson: vi.fn((raw: string) => {
        try {
          return JSON.parse(raw);
        } catch {
          return null;
        }
      }),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;

    // 1. Review
    const reviewAgent = new ReviewAgent(CONFIG, mockRouter);
    const reviewOutput = await reviewAgent.execute({
      projectId: "proj-1",
      paragraphs,
      options: { targetLanguage: "French" },
    });

    const reviewReport = reviewOutput.report as { issues: unknown[]; summary: string };
    expect(reviewReport.issues).toHaveLength(2);
    expect(reviewReport.summary).toContain("fidelity");

    // 2. Revise (consomme le ReviewReport)
    const reviseAgent = new ReviseAgent(CONFIG, mockRouter);
    const reviseOutput = await reviseAgent.execute({
      projectId: "proj-1",
      text: translatedText,
      options: { reviewReport: reviewReport },
    });

    expect(reviseOutput.text).toContain("Le vent hurlait au bord de la falaise");
    expect(reviseOutput.text).toContain("Je ne me trompe pas");
    // Le Revise a bien appelé le LLM (car il y avait des issues)
    expect(mockRouter.chat).toHaveBeenCalledTimes(2);
  });

  it("Summarizer produit un résumé cohérent depuis la fixture", async () => {
    const paragraphs = buildParagraphs(SOURCE_TEXT);

    const mockRouter = {
      chat: vi.fn().mockResolvedValue(
        JSON.stringify({
          chapterSummary: "Elara and Kael reach the citadel after a hard climb.",
          novelSummary:
            "Elara and her reluctant ally Kael travel north to the Ashen King's citadel to end his reign.",
        }),
      ),
      tryParseJson: vi.fn((raw: string) => JSON.parse(raw)),
      isEthicalRefusal: vi.fn().mockReturnValue(false),
    } as unknown as AiRouter;

    const agent = new SummarizerAgent(CONFIG, mockRouter);
    const output = await agent.execute({
      projectId: "proj-1",
      paragraphs,
      options: { novelSummary: "Previous summary." },
    });

    expect(output.metadata?.chapterSummary).toContain("Elara");
    expect(output.metadata?.novelSummary).toContain("Ashen King");
  });
});

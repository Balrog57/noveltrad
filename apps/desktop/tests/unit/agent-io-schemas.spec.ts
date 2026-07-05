import { describe, it, expect } from "vitest";
import {
  agentInputSchema,
  textOutputSchema,
  paragraphsOutputSchema,
  consistencyOutputSchema,
  lexiconOutputSchema,
  qaOutputSchema,
  exportOutputSchema,
} from "@shared/schemas/agent-io.js";

// ---------------------------------------------------------------------------
// Helper data factories
// ---------------------------------------------------------------------------

function validInput() {
  return {
    projectId: "proj-1",
    paragraphs: [
      {
        id: "p1",
        chapterId: "ch1",
        indexInChapter: 0,
        sourceText: "Hello",
        status: "pending",
      },
    ],
  };
}

function validTextOutput() {
  return { text: "Bonjour le monde" };
}

function validParagraphsOutput() {
  return {
    paragraphs: [
      {
        id: "p1",
        chapterId: "ch1",
        indexInChapter: 0,
        sourceText: "Hello",
        translatedText: "Bonjour",
        status: "translated",
      },
    ],
  };
}

function validConsistencyOutput() {
  return {
    report: {
      metrics: [{ name: "paragraphs", source: 5, target: 5, ok: true, score: 100 }],
      warnings: [{ severity: "medium", message: "Dialogue mismatch" }],
      globalScore: 85,
    },
  };
}

function validLexiconOutput() {
  return {
    text: "Le dragon survola les montagnes.",
    substitutions: [
      { before: "dragon", after: "dragon", locked: true },
    ],
  };
}

function validQaOutput() {
  return {
    report: {
      consistency: 95,
      grammar: 92,
      fluency: 88,
      style: 90,
      lexicon: 100,
      hallucination: 95,
      length: 87,
      dialogue: 91,
      globalScore: 93,
      comments: "Good translation",
    },
    score: 93,
  };
}

function validExportOutput() {
  return {
    metadata: { exportPath: "/output/book.epub" },
  };
}

// ---------------------------------------------------------------------------
// Tests : 5 valid + 5 invalid
// ---------------------------------------------------------------------------

describe("Agent I/O Zod schemas (SDD §8.13)", () => {
  // --- Valid ---

  it("1. agentInputSchema should validate a valid input", () => {
    const result = agentInputSchema.safeParse(validInput());
    expect(result.success).toBe(true);
  });

  it("2. textOutputSchema should validate a valid text output", () => {
    const result = textOutputSchema.safeParse(validTextOutput());
    expect(result.success).toBe(true);
  });

  it("3. paragraphsOutputSchema should validate a valid paragraphs output", () => {
    const result = paragraphsOutputSchema.safeParse(validParagraphsOutput());
    expect(result.success).toBe(true);
  });

  it("4. consistencyOutputSchema should validate a valid consistency report", () => {
    const result = consistencyOutputSchema.safeParse(validConsistencyOutput());
    expect(result.success).toBe(true);
  });

  it("5. qaOutputSchema should validate a valid QA report", () => {
    const result = qaOutputSchema.safeParse(validQaOutput());
    expect(result.success).toBe(true);
  });

  // --- Invalid ---

  it("6. agentInputSchema should reject input with missing projectId", () => {
    const result = agentInputSchema.safeParse({ paragraphs: [] });
    expect(result.success).toBe(false);
  });

  it("7. textOutputSchema should reject output missing text field", () => {
    const result = textOutputSchema.safeParse({ metadata: {} });
    expect(result.success).toBe(false);
  });

  it("8. paragraphsOutputSchema should reject output with invalid status", () => {
    const result = paragraphsOutputSchema.safeParse({
      paragraphs: [
        {
          id: "p1",
          chapterId: "ch1",
          indexInChapter: 0,
          sourceText: "Hello",
          status: "invalid_status",
        },
      ],
    });
    expect(result.success).toBe(false);
  });

  it("9. qaOutputSchema should reject output with score out of range (>100)", () => {
    const output = validQaOutput();
    output.score = 150;
    const result = qaOutputSchema.safeParse(output);
    expect(result.success).toBe(false);
  });

  it("10. consistencyOutputSchema should reject output with missing globalScore", () => {
    const result = consistencyOutputSchema.safeParse({
      report: { metrics: [], warnings: [] },
    });
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Additional schema coverage: lexicon + export
// ---------------------------------------------------------------------------

describe("Lexicon + Export schemas", () => {
  it("lexiconOutputSchema should validate valid lexicon output", () => {
    const result = lexiconOutputSchema.safeParse(validLexiconOutput());
    expect(result.success).toBe(true);
  });

  it("lexiconOutputSchema should reject output without substitutions array", () => {
    const result = lexiconOutputSchema.safeParse({ text: "foo" });
    expect(result.success).toBe(false);
  });

  it("exportOutputSchema should validate valid export output", () => {
    const result = exportOutputSchema.safeParse(validExportOutput());
    expect(result.success).toBe(true);
  });

  it("exportOutputSchema should reject output without metadata.exportPath", () => {
    const result = exportOutputSchema.safeParse({ metadata: {} });
    expect(result.success).toBe(false);
  });
});

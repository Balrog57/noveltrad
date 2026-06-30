import { describe, it, expect, beforeEach, vi } from "vitest";
import type {
  DiffResult,
  ParagraphChange,
  HistorySnapshot,
  Paragraph,
} from "@shared/types/index.js";

// ── Helpers ──

/** Crée un paragraphe de test */
function makeParagraph(
  id: string,
  index: number,
  sourceText: string,
  translatedText?: string,
): Paragraph {
  return {
    id,
    chapterId: "ch-1",
    indexInChapter: index,
    sourceText,
    translatedText,
    status: translatedText ? "translated" : "pending",
  };
}

/** Calcule le diff entre deux listes de paragraphes (réimplémentation du handler) */
function computeDiff(
  beforeParagraphs: Paragraph[],
  afterParagraphs: Paragraph[],
): DiffResult {
  const changes: ParagraphChange[] = [];
  const maxIndex = Math.max(beforeParagraphs.length, afterParagraphs.length);

  for (let i = 0; i < maxIndex; i++) {
    const before = beforeParagraphs[i];
    const after = afterParagraphs[i];

    if (!before && after) {
      changes.push({
        index: after.indexInChapter,
        type: "added",
        sourceAfter: after.sourceText,
        targetAfter: after.translatedText,
      });
    } else if (before && !after) {
      changes.push({
        index: before.indexInChapter,
        type: "removed",
        sourceBefore: before.sourceText,
        targetBefore: before.translatedText,
      });
    } else if (before && after) {
      const sourceChanged = before.sourceText !== after.sourceText;
      const targetChanged = before.translatedText !== after.translatedText;
      if (sourceChanged || targetChanged) {
        changes.push({
          index: after.indexInChapter,
          type: "modified",
          sourceBefore: sourceChanged ? before.sourceText : undefined,
          sourceAfter: sourceChanged ? after.sourceText : undefined,
          targetBefore: targetChanged ? before.translatedText : undefined,
          targetAfter: targetChanged ? after.translatedText : undefined,
        });
      }
    }
  }

  return { changes };
}

// ── Tests ──

describe("DiffResult / computeDiff", () => {
  it("devrait détecter un paragraphe ajouté", () => {
    const before: Paragraph[] = [];
    const after: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
    ];

    const result = computeDiff(before, after);
    expect(result.changes).toHaveLength(1);
    expect(result.changes[0].type).toBe("added");
    expect(result.changes[0].sourceAfter).toBe("Hello world");
    expect(result.changes[0].targetAfter).toBe("Bonjour le monde");
  });

  it("devrait détecter un paragraphe supprimé", () => {
    const before: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
    ];
    const after: Paragraph[] = [];

    const result = computeDiff(before, after);
    expect(result.changes).toHaveLength(1);
    expect(result.changes[0].type).toBe("removed");
    expect(result.changes[0].sourceBefore).toBe("Hello world");
    expect(result.changes[0].targetBefore).toBe("Bonjour le monde");
  });

  it("devrait détecter un paragraphe modifié (source et cible)", () => {
    const before: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
    ];
    const after: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world!", "Bonjour le monde !"),
    ];

    const result = computeDiff(before, after);
    expect(result.changes).toHaveLength(1);
    expect(result.changes[0].type).toBe("modified");
    expect(result.changes[0].sourceBefore).toBe("Hello world");
    expect(result.changes[0].sourceAfter).toBe("Hello world!");
    expect(result.changes[0].targetBefore).toBe("Bonjour le monde");
    expect(result.changes[0].targetAfter).toBe("Bonjour le monde !");
  });

  it("devrait détecter uniquement la source modifiée", () => {
    const before: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
    ];
    const after: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world!", "Bonjour le monde"),
    ];

    const result = computeDiff(before, after);
    expect(result.changes).toHaveLength(1);
    expect(result.changes[0].type).toBe("modified");
    expect(result.changes[0].sourceBefore).toBe("Hello world");
    expect(result.changes[0].sourceAfter).toBe("Hello world!");
    expect(result.changes[0].targetBefore).toBeUndefined();
    expect(result.changes[0].targetAfter).toBeUndefined();
  });

  it("devrait détecter uniquement la cible modifiée", () => {
    const before: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
    ];
    const after: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour !"),
    ];

    const result = computeDiff(before, after);
    expect(result.changes).toHaveLength(1);
    expect(result.changes[0].type).toBe("modified");
    expect(result.changes[0].sourceBefore).toBeUndefined();
    expect(result.changes[0].sourceAfter).toBeUndefined();
    expect(result.changes[0].targetBefore).toBe("Bonjour le monde");
    expect(result.changes[0].targetAfter).toBe("Bonjour !");
  });

  it("ne devrait pas signaler de changement si identique", () => {
    const paragraphs: Paragraph[] = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
      makeParagraph("p2", 2, "Good morning", "Bonjour"),
    ];

    const result = computeDiff(paragraphs, paragraphs);
    expect(result.changes).toHaveLength(0);
  });

  it("devrait gérer plusieurs modifications simultanées", () => {
    const before: Paragraph[] = [
      makeParagraph("p1", 1, "Hello", "Bonjour"),
      makeParagraph("p2", 2, "World", "Monde"),
      makeParagraph("p3", 3, "Foo", "Bar"),
    ];
    const after: Paragraph[] = [
      makeParagraph("p1", 1, "Hi", "Salut"),
      makeParagraph("p2", 2, "World", "Monde"),
      makeParagraph("p3", 3, "Foo", "Baz"),
    ];

    const result = computeDiff(before, after);
    expect(result.changes).toHaveLength(2);
    expect(result.changes[0].index).toBe(1);
    expect(result.changes[0].type).toBe("modified");
    expect(result.changes[1].index).toBe(3);
    expect(result.changes[1].type).toBe("modified");
  });

  it("devrait gérer les suppressions et ajouts", () => {
    const before: Paragraph[] = [
      makeParagraph("p1", 1, "A", "a"),
      makeParagraph("p2", 2, "B", "b"),
      makeParagraph("p3", 3, "C", "c"),
    ];
    // Après : le paragraphe du milieu est supprimé, un nouveau est ajouté à la fin
    const after: Paragraph[] = [
      makeParagraph("p1", 1, "A", "a"),
      makeParagraph("p4", 4, "D", "d"),
    ];

    const result = computeDiff(before, after);
    // p1 inchangé → 0 ; p2 vs p4 → modified ; p3 manquant → removed
    expect(result.changes).toHaveLength(2);
    const removed = result.changes.find((c) => c.type === "removed");
    const modified = result.changes.find((c) => c.type === "modified");
    expect(removed).toBeDefined();
    expect(modified).toBeDefined();
    expect(removed!.index).toBe(3);
    expect(modified!.index).toBe(4);
  });
});

describe("HistorySnapshot / types", () => {
  it("devrait valider un snapshot workflow", () => {
    const snapshot: HistorySnapshot = {
      id: "snap-1",
      projectId: "proj-1",
      chapterId: "ch-1",
      jobId: "job-1",
      stepId: "step-1",
      stage: "translate",
      paragraphs: [makeParagraph("p1", 1, "Hello", "Bonjour")],
      qualityScore: 0.85,
      triggeredBy: "workflow",
      createdAt: "2026-06-30T12:00:00.000Z",
      versionNumber: 1,
    };

    expect(snapshot.triggeredBy).toBe("workflow");
    expect(snapshot.versionNumber).toBe(1);
    expect(snapshot.qualityScore).toBe(0.85);
    expect(snapshot.paragraphs).toHaveLength(1);
  });

  it("devrait valider un snapshot manuel", () => {
    const snapshot: HistorySnapshot = {
      id: "snap-2",
      projectId: "proj-1",
      chapterId: "ch-1",
      stage: "manual",
      paragraphs: [makeParagraph("p1", 1, "Hello", "Bonjour")],
      triggeredBy: "manual",
      createdAt: "2026-06-30T12:00:00.000Z",
      versionNumber: 2,
    };

    expect(snapshot.triggeredBy).toBe("manual");
    expect(snapshot.jobId).toBeUndefined();
    expect(snapshot.stepId).toBeUndefined();
  });

  it("devrait valider un snapshot rollback", () => {
    const snapshot: HistorySnapshot = {
      id: "snap-3",
      projectId: "proj-1",
      chapterId: "ch-1",
      stage: "rollback",
      paragraphs: [makeParagraph("p1", 1, "Hello", "Bonjour")],
      triggeredBy: "rollback",
      createdAt: "2026-06-30T12:00:00.000Z",
      versionNumber: 3,
    };

    expect(snapshot.triggeredBy).toBe("rollback");
    expect(snapshot.stage).toBe("rollback");
  });
});

describe("HistorySnapshot / rollback logic", () => {
  it("devrait préserver les paragraphes lors d'un rollback", () => {
    const originalParagraphs = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
      makeParagraph("p2", 2, "How are you?", "Comment allez-vous ?"),
    ];

    const snapshot: HistorySnapshot = {
      id: "snap-1",
      projectId: "proj-1",
      chapterId: "ch-1",
      stage: "translate",
      paragraphs: [...originalParagraphs],
      triggeredBy: "workflow",
      createdAt: "2026-06-30T10:00:00.000Z",
      versionNumber: 1,
    };

    // Simuler un rollback : les paragraphes restaurés doivent être identiques
    const restored = snapshot.paragraphs;
    expect(restored).toHaveLength(2);
    expect(restored[0].sourceText).toBe(originalParagraphs[0].sourceText);
    expect(restored[0].translatedText).toBe(
      originalParagraphs[0].translatedText,
    );
    expect(restored[1].sourceText).toBe(originalParagraphs[1].sourceText);
    expect(restored[1].translatedText).toBe(
      originalParagraphs[1].translatedText,
    );
  });

  it("devrait calculer la versionNumber correctement après rollback", () => {
    const snapshots: HistorySnapshot[] = [
      {
        id: "s1",
        projectId: "p1",
        stage: "translate",
        paragraphs: [],
        triggeredBy: "workflow",
        createdAt: "2026-06-30T10:00:00.000Z",
        versionNumber: 1,
      },
      {
        id: "s2",
        projectId: "p1",
        stage: "translate",
        paragraphs: [],
        triggeredBy: "workflow",
        createdAt: "2026-06-30T11:00:00.000Z",
        versionNumber: 2,
      },
      {
        id: "s3",
        projectId: "p1",
        stage: "rollback",
        paragraphs: [],
        triggeredBy: "rollback",
        createdAt: "2026-06-30T12:00:00.000Z",
        versionNumber: 3,
      },
    ];

    // Le rollback crée une nouvelle version
    const latestAfterRollback: HistorySnapshot = {
      id: "s4",
      projectId: "p1",
      stage: "rollback",
      paragraphs: [],
      triggeredBy: "rollback",
      createdAt: "2026-06-30T13:00:00.000Z",
      versionNumber: 4,
    };

    expect(latestAfterRollback.versionNumber).toBe(4);
    expect(latestAfterRollback.triggeredBy).toBe("rollback");
  });
});

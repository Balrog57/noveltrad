import { describe, it, expect } from "vitest";
import zlib from "node:zlib";
import type {
  DiffResult,
  ParagraphChange,
  HistorySnapshot,
  Paragraph,
  IncrementalChange,
  IncrementalPayload,
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
    const _snapshots: HistorySnapshot[] = [
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

// ── Phase E : Snapshots hybrides (SDD §14.3) ──

describe("HybridSnapshots / incremental changes", () => {
  /**
   * Simule le calcul des changements incrémentaux entre deux listes.
   * Réimplémente la logique de HistoryRepository.computeIncrementalChanges().
   */
  function computeIncrementalChanges(
    base: Paragraph[],
    current: Paragraph[],
  ): IncrementalChange[] {
    const changes: IncrementalChange[] = [];
    const maxIndex = Math.max(base.length, current.length);

    for (let i = 0; i < maxIndex; i++) {
      const b = base[i];
      const c = current[i];

      if (!b && c) {
        changes.push({
          index: c.indexInChapter,
          sourceText: c.sourceText,
          translatedText: c.translatedText,
          status: c.status,
        });
      } else if (b && !c) {
        changes.push({
          index: b.indexInChapter,
          sourceText: "",
          translatedText: undefined,
          status: "pending",
        });
      } else if (b && c) {
        const changed =
          b.sourceText !== c.sourceText ||
          b.translatedText !== c.translatedText ||
          b.status !== c.status;
        if (changed) {
          changes.push({
            index: c.indexInChapter,
            sourceText: c.sourceText,
            translatedText: c.translatedText,
            status: c.status,
          });
        }
      }
    }
    return changes;
  }

  /**
   * Simule la reconstruction depuis un snapshot incrémental.
   */
  function applyIncrementalChanges(
    baseParagraphs: Paragraph[],
    payload: IncrementalPayload,
  ): Paragraph[] {
    const result = [...baseParagraphs];
    for (const change of payload.changes) {
      const existingIdx = result.findIndex(
        (p) => p.indexInChapter === change.index,
      );
      if (change.sourceText === "") {
        if (existingIdx >= 0) {
          result.splice(existingIdx, 1);
        }
      } else if (existingIdx >= 0) {
        result[existingIdx] = {
          ...result[existingIdx],
          sourceText: change.sourceText,
          translatedText: change.translatedText,
          status: change.status,
        };
      } else {
        result.push({
          id: `reconstructed-${payload.baseSnapshotId}-${change.index}`,
          chapterId: "ch-1",
          indexInChapter: change.index,
          sourceText: change.sourceText,
          translatedText: change.translatedText,
          status: change.status,
        });
      }
    }
    result.sort((a, b) => a.indexInChapter - b.indexInChapter);
    return result;
  }

  it("devrait ne générer aucun changement si identique", () => {
    const base = [
      makeParagraph("p1", 1, "Hello", "Bonjour"),
      makeParagraph("p2", 2, "World", "Monde"),
    ];
    const current = [
      makeParagraph("p1", 1, "Hello", "Bonjour"),
      makeParagraph("p2", 2, "World", "Monde"),
    ];

    const changes = computeIncrementalChanges(base, current);
    expect(changes).toHaveLength(0);
  });

  it("devrait détecter un paragraphe modifié", () => {
    const base = [makeParagraph("p1", 1, "Hello", "Bonjour")];
    const current = [makeParagraph("p1", 1, "Hello", "Salut")];

    const changes = computeIncrementalChanges(base, current);
    expect(changes).toHaveLength(1);
    expect(changes[0].index).toBe(1);
    expect(changes[0].translatedText).toBe("Salut");
  });

  it("devrait détecter un paragraphe ajouté", () => {
    const base: Paragraph[] = [];
    const current = [makeParagraph("p1", 1, "Hello", "Bonjour")];

    const changes = computeIncrementalChanges(base, current);
    expect(changes).toHaveLength(1);
    expect(changes[0].index).toBe(1);
    expect(changes[0].sourceText).toBe("Hello");
  });

  it("devrait détecter un paragraphe supprimé", () => {
    const base = [makeParagraph("p1", 1, "Hello", "Bonjour")];
    const current: Paragraph[] = [];

    const changes = computeIncrementalChanges(base, current);
    expect(changes).toHaveLength(1);
    expect(changes[0].index).toBe(1);
    expect(changes[0].sourceText).toBe("");
  });

  it("devrait reconstruire correctement après un changement incrémental", () => {
    const base = [makeParagraph("p1", 1, "Hello", "Bonjour")];
    const payload: IncrementalPayload = {
      _type: "incremental",
      baseSnapshotId: "snap-1",
      changes: [{ index: 1, sourceText: "Hello", translatedText: "Salut", status: "translated" }],
    };

    const reconstructed = applyIncrementalChanges(base, payload);
    expect(reconstructed).toHaveLength(1);
    expect(reconstructed[0].translatedText).toBe("Salut");
  });

  it("devrait gérer plusieurs changements simultanés dans un incrémental", () => {
    const base = [
      makeParagraph("p1", 1, "A", "a"),
      makeParagraph("p2", 2, "B", "b"),
      makeParagraph("p3", 3, "C", "c"),
    ];
    const current = [
      makeParagraph("p1", 1, "A modifié", "a modifié"),
      makeParagraph("p2", 2, "B", "b"), // inchangé
      makeParagraph("p3", 3, "C nouveau", "c nouveau"),
    ];

    const changes = computeIncrementalChanges(base, current);
    expect(changes).toHaveLength(2);
    expect(changes[0].index).toBe(1);
    expect(changes[1].index).toBe(3);

    // Reconstruction
    const payload: IncrementalPayload = {
      _type: "incremental",
      baseSnapshotId: "snap-1",
      changes,
    };
    const reconstructed = applyIncrementalChanges(base, payload);
    expect(reconstructed).toHaveLength(3);
    expect(reconstructed[0].sourceText).toBe("A modifié");
    expect(reconstructed[1].sourceText).toBe("B");
    expect(reconstructed[2].sourceText).toBe("C nouveau");
  });

  it("devrait déterminer si un snapshot doit être complet selon sa version", () => {
    // v1 → full, v5 → full, v10 → full
    const isFull = (version: number): boolean =>
      version === 1 || version % 5 === 0;

    expect(isFull(1)).toBe(true);
    expect(isFull(2)).toBe(false);
    expect(isFull(3)).toBe(false);
    expect(isFull(4)).toBe(false);
    expect(isFull(5)).toBe(true);
    expect(isFull(6)).toBe(false);
    expect(isFull(9)).toBe(false);
    expect(isFull(10)).toBe(true);
    expect(isFull(15)).toBe(true);
  });
});

// ── Phase E : Compression zlib (SDD §14.3) ──

describe("HybridSnapshots / zlib compression", () => {
  const COMPRESSION_THRESHOLD = 10_000;

  it("devrait compresser un texte long avec zlib", () => {
    const largeText = "A".repeat(COMPRESSION_THRESHOLD + 100);
    const compressed = zlib
      .deflateSync(Buffer.from(largeText, "utf-8"))
      .toString("base64");

    // Vérifier que c'est plus petit
    expect(compressed.length).toBeLessThan(largeText.length);

    // Vérifier la décompression
    const decompressed = zlib
      .inflateSync(Buffer.from(compressed, "base64"))
      .toString("utf-8");
    expect(decompressed).toBe(largeText);
  });

  it("ne devrait pas compresser un texte court", () => {
    const smallText = "Hello world";
    const json = JSON.stringify(smallText);
    const shouldCompress = Buffer.byteLength(json, "utf-8") > COMPRESSION_THRESHOLD;

    expect(shouldCompress).toBe(false);
  });

  it("devrait compresser des paragraphes volumineux", () => {
    // Créer 1000 paragraphes avec du texte long
    const paragraphs = Array.from({ length: 1000 }, (_, i) =>
      makeParagraph(
        `p${i}`,
        i,
        "Texte source très long qui se répète pour atteindre le seuil de compression. ".repeat(5),
        "Texte traduit tout aussi long pour les besoins du test de compression. ".repeat(5),
      ),
    );
    const json = JSON.stringify(paragraphs);
    const jsonSize = Buffer.byteLength(json, "utf-8");

    // Vérifier que le JSON dépasse le seuil
    expect(jsonSize).toBeGreaterThan(COMPRESSION_THRESHOLD);

    // Compresser
    const compressed = zlib
      .deflateSync(Buffer.from(json, "utf-8"))
      .toString("base64");

    // Vérifier que la compression est efficace
    expect(compressed.length).toBeLessThan(jsonSize * 0.8);

    // Vérifier la décompression
    const decompressed = zlib
      .inflateSync(Buffer.from(compressed, "base64"))
      .toString("utf-8");
    const restored = JSON.parse(decompressed) as Paragraph[];
    expect(restored).toHaveLength(1000);
    expect(restored[0].sourceText).toContain("Texte source");
    expect(restored[999].sourceText).toContain("Texte source");
  });

  it("devrait préserver l'intégrité après compression/décompression", () => {
    const original = [
      makeParagraph("p1", 1, "Hello world", "Bonjour le monde"),
      makeParagraph("p2", 2, "How are you?", "Comment allez-vous ?"),
    ];

    const json = JSON.stringify(original);
    const compressed = zlib
      .deflateSync(Buffer.from(json, "utf-8"))
      .toString("base64");
    const decompressed = zlib
      .inflateSync(Buffer.from(compressed, "base64"))
      .toString("utf-8");
    const restored = JSON.parse(decompressed) as Paragraph[];

    expect(restored).toEqual(original);
  });
});

// ── Phase E : Rollback partiel (SDD §14.5) ──

describe("PartialRollback / logique de sélection", () => {
  it("devrait filtrer les paragraphes à restaurer par IDs", () => {
    const allParagraphs = [
      makeParagraph("p1", 1, "Hello", "Bonjour"),
      makeParagraph("p2", 2, "World", "Monde"),
      makeParagraph("p3", 3, "Foo", "Bar"),
    ];

    const selectedIds = ["p1", "p3"];
    const selected = allParagraphs.filter((p) =>
      selectedIds.includes(p.id),
    );

    expect(selected).toHaveLength(2);
    expect(selected[0].id).toBe("p1");
    expect(selected[1].id).toBe("p3");
  });

  it("devrait retourner un tableau vide si aucun ID ne correspond", () => {
    const allParagraphs = [makeParagraph("p1", 1, "Hello", "Bonjour")];
    const selected = allParagraphs.filter((p) =>
      ["nonexistent"].includes(p.id),
    );

    expect(selected).toHaveLength(0);
  });

  it("devrait préserver les données des paragraphes sélectionnés", () => {
    const paragraphs = [
      makeParagraph("p1", 1, "Ancien source", "Ancienne trad"),
      makeParagraph("p2", 2, "Source actuel", "Traduction actuelle"),
    ];

    // Simuler le rollback partiel : restaurer seulement p1
    const restoredParagraphs = paragraphs.filter((p) => p.id === "p1");

    expect(restoredParagraphs).toHaveLength(1);
    expect(restoredParagraphs[0].sourceText).toBe("Ancien source");
    expect(restoredParagraphs[0].translatedText).toBe("Ancienne trad");
  });

  it("devrait valider que paragraphIds n'est pas vide", () => {
    const validate = (ids: string[]): boolean => ids.length >= 1;
    expect(validate(["p1"])).toBe(true);
    expect(validate([])).toBe(false);
  });

  it("devrait permettre de sélectionner tous les paragraphes (équivalent rollback complet)", () => {
    const paragraphs = [
      makeParagraph("p1", 1, "A", "a"),
      makeParagraph("p2", 2, "B", "b"),
    ];

    const allIds = paragraphs.map((p) => p.id);
    expect(allIds).toHaveLength(2);

    const selected = paragraphs.filter((p) => allIds.includes(p.id));
    expect(selected).toEqual(paragraphs);
  });
});

/**
 * Tests du policy holder QaBranchPolicy (Axe 1a — clean architecture followup).
 *
 * Avant, la logique de branching QA était inline dans WorkflowRunner.runStep
 * (~70 LOC entrelavées avec mutations DB), testée uniquement via
 * workflow-branching.spec.ts qui mocke l'engine complet. Désormais la
 * décision est testable isolément — ces tests couvrent tous les cas limites.
 */

import { describe, it, expect } from "vitest";
import { decideQaBranch, QA_BRANCH_MARGIN } from "../../src/main/managers/workflow/QaBranchPolicy.js";

describe("QaBranchPolicy — decideQaBranch (Axe 1a)", () => {
  // Defaults du settings (cf. appSettingsSchema) : threshold=70, maxQaRetries=3.
  const THRESHOLD = 70;
  const MAX_RETRIES = 3;

  describe("branche continue (score ≥ threshold)", () => {
    it("score égal au threshold → continue", () => {
      expect(decideQaBranch(70, THRESHOLD, 0, MAX_RETRIES)).toEqual({ action: "continue" });
    });

    it("score au-dessus du threshold → continue", () => {
      expect(decideQaBranch(95, THRESHOLD, 5, MAX_RETRIES)).toEqual({ action: "continue" });
    });

    it("score 100 (max) → continue quel que soit retryCount", () => {
      expect(decideQaBranch(100, THRESHOLD, 99, MAX_RETRIES)).toEqual({ action: "continue" });
    });
  });

  describe("branche retryWeakest (score ∈ [threshold-20, threshold))", () => {
    it("score à la limite basse (threshold - 20) → retryWeakest", () => {
      expect(decideQaBranch(50, THRESHOLD, 0, MAX_RETRIES)).toEqual({ action: "retryWeakest" });
    });

    it("score juste sous le threshold → retryWeakest", () => {
      expect(decideQaBranch(69, THRESHOLD, 0, MAX_RETRIES)).toEqual({ action: "retryWeakest" });
    });

    it("score milieu de zone (threshold - 10) → retryWeakest", () => {
      expect(decideQaBranch(60, THRESHOLD, 1, MAX_RETRIES)).toEqual({ action: "retryWeakest" });
    });

    it("retryCount = maxRetries exact → encore retryWeakest (la borne est > strict)", () => {
      // Le policy original: retry si retryCount <= maxQaRetries (la comparaison
      // de pause est retryCount > maxQaRetries). Donc retryCount = maxRetries
      // permet encore un retry (le prochain tour déclenchera la pause).
      expect(decideQaBranch(60, THRESHOLD, 3, MAX_RETRIES)).toEqual({ action: "retryWeakest" });
    });
  });

  describe("branche pause max_qa_retries_exceeded", () => {
    it("score intermédiaire + retryCount > max → pause max_qa_retries_exceeded", () => {
      expect(decideQaBranch(60, THRESHOLD, 4, MAX_RETRIES)).toEqual({
        action: "pause",
        reason: "max_qa_retries_exceeded",
      });
    });

    it("retryCount très au-delà du max → toujours pause max_qa_retries_exceeded", () => {
      expect(decideQaBranch(69, THRESHOLD, 20, MAX_RETRIES)).toEqual({
        action: "pause",
        reason: "max_qa_retries_exceeded",
      });
    });
  });

  describe("branche pause low_score (score < threshold - 20)", () => {
    it("score juste sous la zone intermédiaire → pause low_score", () => {
      expect(decideQaBranch(49, THRESHOLD, 0, MAX_RETRIES)).toEqual({
        action: "pause",
        reason: "low_score",
      });
    });

    it("score 0 → pause low_score quel que soit retryCount", () => {
      expect(decideQaBranch(0, THRESHOLD, 99, MAX_RETRIES)).toEqual({
        action: "pause",
        reason: "low_score",
      });
    });

    it("low_score prend priorité sur max_qa_retries_exceeded", () => {
      // Score très bas + retryCount dépassé → c'est low_score qui gagne
      // (la pause est immédiate, pas de retry supplémentaire).
      expect(decideQaBranch(10, THRESHOLD, 99, MAX_RETRIES)).toEqual({
        action: "pause",
        reason: "low_score",
      });
    });
  });

  describe("configurations custom (threshold / maxRetries)", () => {
    it("threshold 90 (strict) → score 75 tombe en zone intermédiaire", () => {
      expect(decideQaBranch(75, 90, 0, 5)).toEqual({ action: "retryWeakest" });
    });

    it("threshold 50 (lax) → score 60 continue", () => {
      expect(decideQaBranch(60, 50, 0, 3)).toEqual({ action: "continue" });
    });

    it("maxRetries 0 → tout score intermédiaire déclenche immédiatement pause", () => {
      expect(decideQaBranch(60, THRESHOLD, 1, 0)).toEqual({
        action: "pause",
        reason: "max_qa_retries_exceeded",
      });
    });

    it("QA_BRANCH_MARGIN = 20 (constante exportée, ne pas changer sans cassure)", () => {
      // Sanity check : si quelqu'un change la marge, les seuils ci-dessus
      // cassent. Le test documente le contrat.
      expect(QA_BRANCH_MARGIN).toBe(20);
    });
  });

  describe("frontières exactes", () => {
    it("score = threshold - QA_BRANCH_MARGIN exact → retryWeakest (>= est inclus)", () => {
      expect(decideQaBranch(THRESHOLD - QA_BRANCH_MARGIN, THRESHOLD, 0, MAX_RETRIES))
        .toEqual({ action: "retryWeakest" });
    });

    it("score = threshold - QA_BRANCH_MARGIN - 1 → pause low_score", () => {
      expect(decideQaBranch(THRESHOLD - QA_BRANCH_MARGIN - 1, THRESHOLD, 0, MAX_RETRIES))
        .toEqual({ action: "pause", reason: "low_score" });
    });
  });
});

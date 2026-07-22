import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  ConsistencyReport,
  QualityReport,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import type { QualityChecker } from "../QualityChecker.js";
import type { ConsistencyChecker } from "../ConsistencyChecker.js";
import {
  VALIDATE_SYSTEM_PROMPT,
  buildValidateUserPrompt,
} from "../prompts/validate.system.js";
import { buildLexiconBlock } from "../prompts/blocks.js";
import { qaOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

/**
 * v3 (REFACTOR_PLAN_V3.md Phase 1) : ValidatorAgent fusionne les anciens
 * stages consistency + qa en une seule évaluation finale de qualité.
 *
 * Anciennement, le moteur exécutait ConsistencyAgent (→ ConsistencyReport),
 * puis injectait ce report dans QaAgent via `options.consistencyReport`. La
 * fusion internalise ce hand-off : le Validator calcule le ConsistencyReport
 * (heuristique, via ConsistencyChecker) puis l'utilise comme fallback pour le
 * scoring de cohérence si l'évaluation LLM échoue.
 *
 * Flux :
 *   1. LLM evaluation (JSON) — dimensions qualité 8-axes + suspectSentences
 *      + consistencyWarnings dans un seul appel.
 *   2. Fallback heuristic (QualityChecker + ConsistencyChecker) si le LLM
 *      échoue ou retourne un JSON invalide.
 *
 * Sortie : { report: QualityReport, score: globalScore }.
 * Le schema de sortie reste qaOutputSchema (shape QualityReport) — rétro-
 * compatible avec l'inspecteur d'agents et les tests existants.
 *
 * NB : CalibrationService n'est pas repris (supprimé en Phase 3). Le scoring
 * est brut (non calibré), ce qui est honnête pour un MVP.
 */
export class ValidatorAgent extends Agent {
  readonly id = "validate";
  readonly name = "Validator";
  readonly stage = "validate";
  readonly outputSchema = qaOutputSchema;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    private qualityChecker: QualityChecker,
    private consistencyChecker: ConsistencyChecker,
  ) {
    super();
  }

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const sourceText = paragraphs.map((p) => p.sourceText).join("\n\n");
    const translatedText = paragraphs
      .map((p) => p.translatedText ?? "")
      .join("\n\n");
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";
    const sourceLanguage =
      (input.options?.sourceLanguage as string | undefined) ?? undefined;
    const novelSummary =
      (input.options?.novelSummary as string | undefined) ?? undefined;
    const lexicon = input.lexicon ?? [];

    // --- ConsistencyReport heuristique (toujours calculé : sert de fallback
    // de cohérence ET de signal pour l'utilisateur). Anciennement produit par
    // le stage ConsistencyAgent séparé, ici internalisé.
    const consistencyReport = this.computeConsistencyReport(
      paragraphs.map((p) => p.sourceText),
      paragraphs.map((p) => p.translatedText ?? ""),
      lexicon,
      sourceLanguage,
      targetLanguage,
    );

    // --- Phase 1 : évaluation LLM unifiée (QA + consistency) ---
    let report: QualityReport;
    const fallbackEvaluate = (): Promise<QualityReport> =>
      this.heuristicEvaluate(sourceText, translatedText, lexicon, consistencyReport);

    try {
      const lexiconBlock = buildLexiconBlock(lexicon);
      const userPrompt = buildValidateUserPrompt({
        sourceText,
        translatedText,
        targetLanguage,
        novelSummary,
        lexiconBlock: lexiconBlock || undefined,
      });

      const response = await this.aiRouter.chat(
        this.config.providerId,
        [
          { role: "system", content: VALIDATE_SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        { jsonMode: true },
      );

      const parsed = this.aiRouter.tryParseJson(response);
      if (parsed && typeof parsed === "object") {
        const obj = parsed as Record<string, unknown>;
        const suspectSentences = Array.isArray(obj.suspectSentences)
          ? (obj.suspectSentences as Array<Record<string, unknown>>)
              .map((raw) => ({
                sentence: String(raw.sentence ?? ""),
                score: typeof raw.score === "number" ? raw.score : 50,
                issue: String(raw.issue ?? ""),
              }))
              .filter((s) => s.sentence.length > 0)
          : [];
        report = {
          consistency: typeof obj.consistency === "number" ? obj.consistency : 50,
          grammar: typeof obj.grammar === "number" ? obj.grammar : 50,
          fluency: typeof obj.fluency === "number" ? obj.fluency : 50,
          style: typeof obj.style === "number" ? obj.style : 50,
          lexicon: typeof obj.lexicon === "number" ? obj.lexicon : 50,
          hallucination:
            typeof obj.hallucination === "number" ? obj.hallucination : 50,
          length: typeof obj.length === "number" ? obj.length : 50,
          dialogue: typeof obj.dialogue === "number" ? obj.dialogue : 50,
          globalScore:
            typeof obj.globalScore === "number" ? obj.globalScore : 50,
          comments: String(obj.comments ?? ""),
          suspectSentences,
          retryInstructions:
            typeof obj.retryInstructions === "string"
              ? obj.retryInstructions
              : "",
        };
      } else {
        report = await fallbackEvaluate();
      }
    } catch (err) {
      logger.warn(
        "[ValidatorAgent] LLM evaluation failed, falling back to heuristics",
        { error: (err as Error).message },
      );
      report = await fallbackEvaluate();
    }

    return { report, score: report.globalScore };
  }

  /**
   * ConsistencyReport heuristique via ConsistencyChecker.
   * Internalise ce que l'ancien stage ConsistencyAgent produisait séparément.
   */
  private computeConsistencyReport(
    source: string[],
    target: string[],
    lexicon: AgentInput["lexicon"],
    sourceLanguage?: string,
    targetLanguage?: string,
  ): ConsistencyReport {
    const languagePair =
      sourceLanguage && targetLanguage
        ? `${sourceLanguage}-${targetLanguage}`
        : undefined;
    return this.consistencyChecker.check(
      source,
      target,
      lexicon ?? [],
      languagePair,
    );
  }

  /**
   * Évaluation heuristique de fallback via QualityChecker.
   * async car QualityChecker.evaluate retourne une Promise (l'impl actuelle est
   * synchrone mais le contrat est async — on respecte le contrat).
   */
  private async heuristicEvaluate(
    sourceText: string,
    translatedText: string,
    lexicon: AgentInput["lexicon"],
    consistencyReport: ConsistencyReport,
  ): Promise<QualityReport> {
    return this.qualityChecker.evaluate(
      sourceText,
      translatedText,
      lexicon ?? [],
      consistencyReport,
    );
  }
}

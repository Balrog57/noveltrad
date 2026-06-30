import type {
  WorkflowStage,
  AgentInput,
  AgentOutput,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import type { Agent, AgentConfig } from "./Agent.js";
import { SplitAgent } from "./SplitAgent.js";
import { PreTranslateAgent } from "./PreTranslateAgent.js";
import { TranslateAgent } from "./TranslateAgent.js";
import { ConsistencyAgent } from "./ConsistencyAgent.js";
import { LexiconAgent } from "./LexiconAgent.js";
import { GrammarAgent } from "./GrammarAgent.js";
import { StyleAgent } from "./StyleAgent.js";
import { PolishAgent } from "./PolishAgent.js";
import { QaAgent } from "./QaAgent.js";
import { ExportAgent } from "./ExportAgent.js";
import type { LexiconEngine } from "../LexiconEngine.js";
import type { TranslationMemoryEngine } from "../TranslationMemoryEngine.js";
import type { ConsistencyChecker } from "../ConsistencyChecker.js";
import type { QualityChecker } from "../QualityChecker.js";
import type { ExportEngine } from "../ExportEngine.js";

export interface AgentFactoryServices {
  aiRouter: AiRouter;
  lexiconEngine: LexiconEngine;
  tmEngine: TranslationMemoryEngine;
  consistencyChecker: ConsistencyChecker;
  qualityChecker: QualityChecker;
  exportEngine: ExportEngine;
}

export class AgentFactory {
  constructor(private services: AgentFactoryServices) {}

  create(stage: WorkflowStage, config: AgentConfig): Agent {
    switch (stage) {
      case "split":
        return new SplitAgent(config);
      case "pre_translate":
        return new PreTranslateAgent(config, this.services.aiRouter);
      case "translate":
        return new TranslateAgent(
          config,
          this.services.aiRouter,
          this.services.tmEngine,
        );
      case "consistency":
        return new ConsistencyAgent(config, this.services.consistencyChecker);
      case "lexicon":
        return new LexiconAgent(config, this.services.lexiconEngine);
      case "grammar":
        return new GrammarAgent(config, this.services.aiRouter);
      case "style":
        return new StyleAgent(config, this.services.aiRouter);
      case "polish":
        return new PolishAgent(config, this.services.aiRouter);
      case "qa":
        return new QaAgent(
          config,
          this.services.aiRouter,
          this.services.qualityChecker,
        );
      case "export":
        return new ExportAgent(config, this.services.exportEngine);
      default:
        throw new Error(`Stage inconnu : ${stage}`);
    }
  }
}

import type {
  WorkflowStage,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import { SplitAgent } from "./SplitAgent.js";
import { PreTranslateAgent } from "./PreTranslateAgent.js";
import { TranslateAgent } from "./TranslateAgent.js";
import { ConsistencyAgent } from "./ConsistencyAgent.js";
import { LexiconAgent } from "./LexiconAgent.js";
import { GrammarAgent } from "./GrammarAgent.js";
import { StyleAgent } from "./StyleAgent.js";
import { PolishAgent } from "./PolishAgent.js";
import { ReviewAgent } from "./ReviewAgent.js";
import { ReviseAgent } from "./ReviseAgent.js";
import { QaAgent } from "./QaAgent.js";
import { ExportAgent } from "./ExportAgent.js";
import type { LexiconEngine } from "../LexiconEngine.js";
import type { TranslationMemoryEngine } from "../TranslationMemoryEngine.js";
import type { ConsistencyChecker } from "../ConsistencyChecker.js";
import type { QualityChecker } from "../QualityChecker.js";
import type { ExportEngine } from "../ExportEngine.js";
import type { CalibrationService } from "../CalibrationService.js";

export interface AgentFactoryServices {
  aiRouter: AiRouter;
  lexiconEngine: LexiconEngine;
  tmEngine: TranslationMemoryEngine;
  consistencyChecker: ConsistencyChecker;
  qualityChecker: QualityChecker;
  exportEngine: ExportEngine;
  /** SDD §12.5 : service de calibration optionnel */
  calibrationService?: CalibrationService;
  /**
   * SDD §15 : callback pour obtenir un agent depuis un plugin.
   * PluginHost fournit cette fonction. Si elle retourne un agent,
   * il est utilisé à la place du built-in.
   */
  getPluginAgent?: (stage: string, config: AgentConfig) => Agent | undefined;
}

export class AgentFactory {
  constructor(private services: AgentFactoryServices) {}

  create(stage: WorkflowStage, config: AgentConfig): Agent {
    // SDD §15 : vérifier d'abord si un plugin fournit un agent pour ce stage
    if (this.services.getPluginAgent) {
      const pluginAgent = this.services.getPluginAgent(stage, config);
      if (pluginAgent) {return pluginAgent;}
    }

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
        return new ConsistencyAgent(config, this.services.consistencyChecker, this.services.aiRouter);
      case "lexicon":
        return new LexiconAgent(config, this.services.lexiconEngine, this.services.aiRouter);
      case "grammar":
        return new GrammarAgent(config, this.services.aiRouter);
      case "style":
        return new StyleAgent(config, this.services.aiRouter);
      case "polish":
        return new PolishAgent(config, this.services.aiRouter);
      case "review":
        return new ReviewAgent(config, this.services.aiRouter);
      case "revise":
        return new ReviseAgent(config, this.services.aiRouter);
      case "qa":
        return new QaAgent(
          config,
          this.services.aiRouter,
          this.services.qualityChecker,
          this.services.calibrationService,
        );
      case "export":
        return new ExportAgent(config, this.services.exportEngine);
      default:
        throw new Error(`Stage inconnu : ${stage}`);
    }
  }
}

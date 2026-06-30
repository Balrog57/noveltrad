import type { Agent, AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  ExportInput,
} from "@shared/types/index.js";
import type { ExportEngine } from "../ExportEngine.js";

export class ExportAgent implements Agent {
  readonly id = "export";
  readonly name = "Export";
  readonly stage = "export";

  constructor(
    private config: AgentConfig,
    private exportEngine: ExportEngine,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    if (!input.projectId) throw new Error("projectId requis pour export");
    const exportInput: ExportInput = {
      projectId: input.projectId,
      title: (input.options?.title as string) ?? "Export",
      author: input.options?.author as string,
      paragraphs: input.paragraphs ?? [],
      format: (input.options?.format as ExportInput["format"]) ?? "markdown",
      outputPath: input.options?.outputPath as string,
      options: {
        includeTitle: true,
        bilingual: !!input.options?.bilingual,
      },
    };
    const filePath = await this.exportEngine.export(exportInput);
    return { metadata: { exportPath: filePath } };
  }
}

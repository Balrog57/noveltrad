import { describe, it, expect, vi } from "vitest";

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

import { AgentFactory } from "../../src/main/services/agents/AgentFactory";
import { Agent } from "../../src/main/services/agents/Agent";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { AgentConfig } from "../../src/main/services/agents/Agent";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";

// ---------------------------------------------------------------------------
// Agent factice fourni par un "plugin"
// ---------------------------------------------------------------------------

class FakePluginTranslateAgent extends Agent {
  readonly id = "fake-translate";
  readonly name = "Fake Translate (plugin)";
  readonly stage = "translate" as const;

  async execute(_input: AgentInput): Promise<AgentOutput> {
    return { text: "TRANSLATED-BY-PLUGIN" };
  }
}

// ---------------------------------------------------------------------------
// Tests — câblage PluginHost → AgentFactory.getPluginAgent (Phase B1)
// ---------------------------------------------------------------------------

describe("AgentFactory — câblage plugin agents (Phase B1)", () => {
  it("utilise l'agent du plugin quand getPluginAgent retourne un agent", () => {
    const fakeAgent = new FakePluginTranslateAgent();
    const fakeFactory = vi.fn((_config: AgentConfig) => fakeAgent);

    const factory = new AgentFactory({
      aiRouter: {} as AiRouter,
      lexiconEngine: {} as never,
      tmEngine: {} as never,
      consistencyChecker: {} as never,
      qualityChecker: {} as never,
      exportEngine: {} as never,
      getPluginAgent: (stage: string, config: AgentConfig) => {
        if (stage === "translate") {
          return fakeFactory(config) as unknown as Agent;
        }
        return undefined;
      },
    });

    const config = { providerId: "ollama", model: "qwen3.5:9b" };
    const agent = factory.create("translate", config);

    expect(agent).toBe(fakeAgent);
    expect(agent.id).toBe("fake-translate");
    expect(fakeFactory).toHaveBeenCalledWith(config);
  });

  it("retombe sur l'agent built-in si le plugin ne fournit pas ce stage", () => {
    const builtInAgent = factoryWithoutPlugin();
    expect(builtInAgent.id).not.toBe("fake-translate");
  });
});

function factoryWithoutPlugin(): Agent {
  const factory = new AgentFactory({
    aiRouter: {
      chat: vi.fn().mockResolvedValue("built-in response"),
    } as unknown as AiRouter,
    lexiconEngine: {} as never,
    tmEngine: {} as never,
    consistencyChecker: {} as never,
    qualityChecker: {} as never,
    exportEngine: {} as never,
    // Pas de getPluginAgent → built-in uniquement
  });
  return factory.create("grammar", { providerId: "ollama", model: "qwen3.5:9b" });
}

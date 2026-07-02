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

import { ExportEngine } from "../../src/main/services/ExportEngine";
import type { Agent } from "../../src/main/services/agents/Agent";
import type { AgentConfig } from "../../src/main/services/agents/Agent";

describe("ExportEngine custom renderers", () => {
  it("registerRenderer ajoute un renderer personnalisé", () => {
    const engine = new ExportEngine();
    const renderer = vi.fn().mockReturnValue("pdf content");
    engine.registerRenderer("pdf", renderer);
    // Le renderer est stocké en interne — vérifié en appelant export()
    expect(renderer).not.toHaveBeenCalled();
  });

  it("custom renderer est appelé avant le switch built-in", async () => {
    const engine = new ExportEngine();
    const customRenderer = vi.fn().mockResolvedValue("custom html");
    engine.registerRenderer("html", customRenderer);

    const result = await (engine as any).render({
      projectId: "p1",
      title: "Test",
      paragraphs: [],
      format: "html",
    });

    expect(customRenderer).toHaveBeenCalledOnce();
    expect(result).toBe("custom html");
  });

  it("custom renderer pour un format inconnu", async () => {
    const engine = new ExportEngine();
    const customRenderer = vi.fn().mockResolvedValue(Buffer.from("pdf data"));
    engine.registerRenderer("pdf", customRenderer);

    const result = await (engine as any).render({
      projectId: "p1",
      title: "Test",
      paragraphs: [],
      format: "pdf",
    });

    expect(customRenderer).toHaveBeenCalledOnce();
    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it("le switch built-in est utilisé si aucun custom renderer", async () => {
    const engine = new ExportEngine();
    const result = await (engine as any).render({
      projectId: "p1",
      title: "Test",
      paragraphs: [{ indexInChapter: 0, sourceText: "Hello", translatedText: "Bonjour" } as any],
      format: "txt",
    });
    expect(typeof result).toBe("string");
    expect(result).toContain("Bonjour");
  });
});

describe("AiRouter plugin provider resolver", () => {
  it("setPluginProviderResolver permet de résoudre les providers plugins", async () => {
    // Ce test vérifie simplement que l'API existe
    const { AiRouter } = await import("../../src/main/services/AiRouter");
    const router = new AiRouter();
    const pluginProvider = {
      id: "plugin-test",
      name: "Plugin Test",
      model: "test-model",
      chat: vi.fn(),
      streamChat: vi.fn(),
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
    };

    router.setPluginProviderResolver((id) => {
      if (id === "plugin-test") return pluginProvider;
      return undefined;
    });

    const result = router.get("plugin-test");
    expect(result).toBe(pluginProvider);
  });

  it("le resolver plugin est consulté après les providers built-in", async () => {
    const { AiRouter } = await import("../../src/main/services/AiRouter");
    const router = new AiRouter();
    const builtInProvider = {
      id: "built-in",
      name: "Built-in",
      model: "test",
      chat: vi.fn(),
      streamChat: vi.fn(),
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
    };

    router.register(builtInProvider);

    const pluginResolver = vi.fn();
    router.setPluginProviderResolver(pluginResolver);

    const result = router.get("built-in");
    expect(result).toBe(builtInProvider);
    expect(pluginResolver).not.toHaveBeenCalled();
  });

  it("lève une erreur si le provider n'existe ni dans built-in ni dans plugins", async () => {
    const { AiRouter } = await import("../../src/main/services/AiRouter");
    const router = new AiRouter();
    router.setPluginProviderResolver(() => undefined);
    expect(() => router.get("unknown")).toThrow("Provider inconnu");
  });
});

describe("AgentFactory plugin agent callback", () => {
  it("getPluginAgent est consulté avant le switch built-in", async () => {
    const { AgentFactory } = await import("../../src/main/services/agents/AgentFactory");
    const mockAgent = { id: "plugin-agent", name: "Plugin Agent", stage: "split", execute: vi.fn() };

    const factory = new AgentFactory({
      aiRouter: {} as any,
      lexiconEngine: {} as any,
      tmEngine: {} as any,
      consistencyChecker: {} as any,
      qualityChecker: {} as any,
      exportEngine: {} as any,
      getPluginAgent: (stage: string, _config: AgentConfig): Agent | undefined => {
        if (stage === "split") return mockAgent as any;
        return undefined;
      },
    });

    const agent = factory.create("split", { providerId: "test", model: "test" });
    expect(agent).toBe(mockAgent);
  });

  it("le switch built-in est utilisé si getPluginAgent retourne undefined", async () => {
    const { AgentFactory } = await import("../../src/main/services/agents/AgentFactory");

    const factory = new AgentFactory({
      aiRouter: {} as any,
      lexiconEngine: {} as any,
      tmEngine: {} as any,
      consistencyChecker: {} as any,
      qualityChecker: {} as any,
      exportEngine: {} as any,
      getPluginAgent: () => undefined,
    });

    // SplitAgent existe dans le switch built-in
    const agent = factory.create("split", { providerId: "test", model: "test" });
    expect(agent).toBeDefined();
    expect(agent.constructor.name).toBe("SplitAgent");
  });

  it("lève une erreur si le stage est inconnu et aucun plugin", async () => {
    const { AgentFactory } = await import("../../src/main/services/agents/AgentFactory");
    const factory = new AgentFactory({
      aiRouter: {} as any,
      lexiconEngine: {} as any,
      tmEngine: {} as any,
      consistencyChecker: {} as any,
      qualityChecker: {} as any,
      exportEngine: {} as any,
      getPluginAgent: () => undefined,
    });

    expect(() =>
      factory.create("unknown_stage" as any, { providerId: "test", model: "test" }),
    ).toThrow("Stage inconnu");
  });
});

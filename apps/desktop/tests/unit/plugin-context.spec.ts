import { describe, it, expect, vi } from "vitest";
import { PluginContext } from "../../src/main/plugins/PluginContext";
import type { NovelTradPlugin, PluginManifest } from "@shared/types/index.js";
import type { AiRouter } from "../../src/main/services/AiRouter";
import type { LexiconEngine } from "../../src/main/services/LexiconEngine";

// ── Mocks ─────────────────────────────────────────────────────────────

const createMockManifest = (id = "com.test.plugin"): PluginManifest => ({
  id,
  name: "Test Plugin",
  version: "1.0.0",
  type: "export",
  entry: "index.mjs",
  permissions: [],
});

const createMockPlugin = (): NovelTradPlugin => ({
  manifest: createMockManifest(),
  apiVersion: "1.0",
  activate: vi.fn(),
  deactivate: vi.fn(),
});

const createMockAiRouter = (): AiRouter =>
  ({
    chat: vi.fn().mockResolvedValue(""),
    streamChat: vi.fn(),
    register: vi.fn(),
    setCache: vi.fn(),
    get: vi.fn(),
    tryParseJson: vi.fn(),
    isEthicalRefusal: vi.fn(),
  }) as unknown as AiRouter;

const createMockLexiconEngine = (): LexiconEngine =>
  ({
    load: vi.fn(),
    apply: vi.fn().mockReturnValue({ text: "", substitutions: [] }),
    extractCandidates: vi.fn(),
    exportEntries: vi.fn(),
    findConflicts: vi.fn(),
  }) as unknown as LexiconEngine;

const createMockLogger = () => ({
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  debug: vi.fn(),
});

function createRegistry() {
  return {
    agents: new Map(),
    exports: new Map(),
    providers: new Map(),
    parsers: new Map(),
    prompts: new Map(),
    commands: new Map(),
  };
}

describe("PluginContext", () => {
  it("crée un contexte avec les bons IDs", () => {
    const plugin = createMockPlugin();
    const context = new PluginContext(
      plugin,
      createMockAiRouter(),
      createMockLexiconEngine(),
      createMockLogger(),
      createRegistry(),
    );
    expect(context.pluginId).toBe("com.test.plugin");
    expect(context.projectId).toBeNull();
  });

  it("expose aiRouter et lexiconEngine", () => {
    const context = new PluginContext(
      createMockPlugin(),
      createMockAiRouter(),
      createMockLexiconEngine(),
      createMockLogger(),
      createRegistry(),
    );
    expect(context.aiRouter).toBeDefined();
    expect(typeof context.aiRouter.chat).toBe("function");
    expect(context.lexiconEngine).toBeDefined();
    expect(typeof context.lexiconEngine.apply).toBe("function");
  });

  it("expose un logger prefixé par le pluginId", () => {
    const logger = createMockLogger();
    const context = new PluginContext(
      createMockPlugin(),
      createMockAiRouter(),
      createMockLexiconEngine(),
      logger,
      createRegistry(),
    );
    context.logger.info("test message");
    expect(logger.info).toHaveBeenCalledWith("[com.test.plugin] test message");
  });

  describe("registerAgent", () => {
    it("enregistre un agent dans le registre", () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      const factory = vi.fn();
      context.registerAgent("xianxia_check", factory);
      expect(registry.agents.get("xianxia_check")).toBe(factory);
    });

    it("dispose supprime l'agent du registre", async () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      const factory = vi.fn();
      context.registerAgent("test_stage", factory);
      expect(registry.agents.has("test_stage")).toBe(true);
      await context.subscriptions.dispose();
      expect(registry.agents.has("test_stage")).toBe(false);
    });
  });

  describe("registerExport", () => {
    it("enregistre un export dans le registre", () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      const exporter = vi.fn();
      context.registerExport("pdf", exporter);
      expect(registry.exports.get("pdf")).toBe(exporter);
    });
  });

  describe("registerProvider", () => {
    it("enregistre un provider dans le registre", () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      const provider = vi.fn();
      context.registerProvider("lmstudio", provider);
      expect(registry.providers.get("lmstudio")).toBe(provider);
    });
  });

  describe("registerPrompt", () => {
    it("enregistre un prompt dans le registre", () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      context.registerPrompt("test-prompt", { template: "hello {{name}}" });
      expect(registry.prompts.has("test-prompt")).toBe(true);
    });
  });

  describe("registerParser", () => {
    it("enregistre un parser dans le registre", () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      context.registerParser(".pdf", { parse: vi.fn() });
      expect(registry.parsers.get(".pdf")).toBeDefined();
    });
  });

  describe("registerCommand", () => {
    it("enregistre une commande dans le registre", () => {
      const registry = createRegistry();
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      const handler = vi.fn();
      context.registerCommand("my-command", handler);
      expect(registry.commands.get("my-command")).toBe(handler);
    });
  });

  describe("registerConfigChangeListener", () => {
    it("notifie le listener quand la config change", () => {
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      const listener = vi.fn();
      context.registerConfigChangeListener(listener);
      context.setConfig({ key: "value" });
      expect(listener).toHaveBeenCalledWith({ key: "value" });
    });

    it("dispose supprime le listener", async () => {
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      const listener = vi.fn();
      context.registerConfigChangeListener(listener);
      await context.subscriptions.dispose();
      context.setConfig({ key: "value" });
      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe("getConfig / setConfig", () => {
    it("retourne la config par défaut vide", () => {
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      expect(context.getConfig()).toEqual({});
    });

    it("setConfig modifie la config", () => {
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      context.setConfig({ strictness: 0.8 });
      expect(context.getConfig()).toEqual({ strictness: 0.8 });
    });
  });

  describe("subscriptions", () => {
    it("CompositeDisposable se vide après dispose", async () => {
      const context = new PluginContext(
        createMockPlugin(),
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      expect(context.subscriptions.size).toBe(0);
      context.registerAgent("test", vi.fn());
      expect(context.subscriptions.size).toBe(1);
      await context.subscriptions.dispose();
      expect(context.subscriptions.size).toBe(0);
    });
  });

  describe("permission guards (runtime enforcement)", () => {
    it("aiRouter.chat() lève une erreur si la permission 'ai' manque", () => {
      const plugin = createMockPlugin();
      plugin.manifest.permissions = []; // pas de permissions
      const context = new PluginContext(
        plugin,
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      expect(() => context.aiRouter.chat("provider", [])).toThrow("permission \"ai\"");
    });

    it("aiRouter.chat() fonctionne si la permission 'ai' est déclarée", async () => {
      const router = createMockAiRouter();
      vi.mocked(router.chat).mockResolvedValue("response");
      const plugin = createMockPlugin();
      plugin.manifest.permissions = ["ai"];
      const context = new PluginContext(
        plugin,
        router,
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      const result = await context.aiRouter.chat("provider", []);
      expect(result).toBe("response");
    });

    it("lexiconEngine.apply() lève une erreur si la permission 'lexicon' manque", () => {
      const plugin = createMockPlugin();
      plugin.manifest.permissions = [];
      const context = new PluginContext(
        plugin,
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
      );
      expect(() => context.lexiconEngine.apply("text")).toThrow("permission \"lexicon\"");
    });

    it("lexiconEngine.apply() fonctionne si la permission 'lexicon' est déclarée", () => {
      const engine = createMockLexiconEngine();
      vi.mocked(engine.apply).mockReturnValue({ text: "ok", substitutions: [] });
      const plugin = createMockPlugin();
      plugin.manifest.permissions = ["lexicon"];
      const context = new PluginContext(
        plugin,
        createMockAiRouter(),
        engine,
        createMockLogger(),
        createRegistry(),
      );
      const result = context.lexiconEngine.apply("text");
      expect(result.text).toBe("ok");
    });

    it("les permissions sont lues depuis le constructeur si pas dans le manifest", () => {
      const plugin = createMockPlugin();
      plugin.manifest.permissions = []; // manifest vide
      // Mais on passe les permissions en paramètre
      const context = new PluginContext(
        plugin,
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        createRegistry(),
        undefined,
        undefined,
        ["ai", "lexicon"], // permissions explicites
      );
      // Pas d'erreur car les permissions sont passées en paramètre
      expect(() => context.aiRouter.chat("provider", [])).not.toThrow();
      expect(() => context.lexiconEngine.apply("text")).not.toThrow();
    });

    it("registerAgent ne lève pas d'erreur (pas de guard sur register)", () => {
      const plugin = createMockPlugin();
      plugin.manifest.permissions = [];
      const registry = createRegistry();
      const context = new PluginContext(
        plugin,
        createMockAiRouter(),
        createMockLexiconEngine(),
        createMockLogger(),
        registry,
      );
      // registerAgent n'a pas de guard — seuls les appels de service sont filtrés
      expect(() => context.registerAgent("test", vi.fn())).not.toThrow();
    });
  });
});

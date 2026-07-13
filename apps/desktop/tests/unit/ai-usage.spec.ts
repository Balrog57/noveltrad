import { describe, it, expect, beforeEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// SDD §3.8 : Token accounting — accumulateur AiRouter + chatWithUsage
//
// Valide que l'AiRouter accumule l'usage renvoyé par provider.chatWithUsage()
// et l'expose via getAndResetUsage() pour que le WorkflowEngine remplisse
// step.tokensIn/Out et applique le cap maxJobTokens.
// ---------------------------------------------------------------------------

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

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: {
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { AiRouter } from "../../src/main/services/AiRouter";
import type { AiProvider, ChatResult } from "@shared/types/index.js";

function makeProvider(chatResults: ChatResult[]): AiProvider {
  let i = 0;
  return {
    id: "test",
    name: "Test",
    model: "m",
    chat: vi.fn(async () => chatResults[Math.min(i, chatResults.length - 1)].content),
    chatWithUsage: vi.fn(async (): Promise<ChatResult> => {
      const r = chatResults[Math.min(i, chatResults.length - 1)];
      i++;
      return r;
    }),
    streamChat: vi.fn(),
    listModels: vi.fn(),
    embeddings: vi.fn(),
    isAvailable: vi.fn(),
  } as unknown as AiProvider;
}

describe("Token accounting — AiRouter accumulateur (SDD §3.8)", () => {
  let router: AiRouter;

  beforeEach(() => {
    router = new AiRouter();
  });

  it("resetUsage puis getAndResetUsage retourne undefined si aucun appel", () => {
    router.resetUsage();
    expect(router.getAndResetUsage()).toBeUndefined();
  });

  it("accumule l'usage d'un seul appel chat", async () => {
    const provider = makeProvider([
      { content: "ok", usage: { promptTokens: 100, completionTokens: 30, totalTokens: 130 } },
    ]);
    router.register(provider);

    router.resetUsage();
    await router.chat("test", [{ role: "user", content: "hi" }]);

    const usage = router.getAndResetUsage();
    expect(usage).toBeDefined();
    expect(usage!.promptTokens).toBe(100);
    expect(usage!.completionTokens).toBe(30);
    expect(usage!.totalTokens).toBe(130);
  });

  it("accumule l'usage sur plusieurs appels (agent multi-paragraphe)", async () => {
    const provider = makeProvider([
      { content: "t1", usage: { promptTokens: 50, completionTokens: 20, totalTokens: 70 } },
      { content: "t2", usage: { promptTokens: 60, completionTokens: 25, totalTokens: 85 } },
      { content: "t3", usage: { promptTokens: 40, completionTokens: 15, totalTokens: 55 } },
    ]);
    router.register(provider);

    router.resetUsage();
    await router.chat("test", [{ role: "user", content: "p1" }]);
    await router.chat("test", [{ role: "user", content: "p2" }]);
    await router.chat("test", [{ role: "user", content: "p3" }]);

    const usage = router.getAndResetUsage();
    expect(usage).toBeDefined();
    expect(usage!.promptTokens).toBe(150); // 50+60+40
    expect(usage!.completionTokens).toBe(60); // 20+25+15
    expect(usage!.totalTokens).toBe(210); // 70+85+55
  });

  it("getAndResetUsage réinitialise l'accumulateur après lecture", async () => {
    const provider = makeProvider([
      { content: "ok", usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 } },
    ]);
    router.register(provider);

    router.resetUsage();
    await router.chat("test", [{ role: "user", content: "hi" }]);
    const first = router.getAndResetUsage();
    expect(first!.totalTokens).toBe(15);

    // Deuxième lecture sans nouvel appel → undefined
    expect(router.getAndResetUsage()).toBeUndefined();
  });

  it("retourne undefined quand le provider ne renvoie pas d'usage", async () => {
    const provider = makeProvider([{ content: "ok" }]); // pas de usage
    router.register(provider);

    router.resetUsage();
    await router.chat("test", [{ role: "user", content: "hi" }]);
    expect(router.getAndResetUsage()).toBeUndefined();
  });

  it("chat() retourne le contenu seul (rétrocompatible)", async () => {
    const provider = makeProvider([
      { content: "Bonjour", usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 } },
    ]);
    router.register(provider);

    const content = await router.chat("test", [{ role: "user", content: "hi" }]);
    expect(content).toBe("Bonjour");
    expect(typeof content).toBe("string");
  });

  it("chatWithUsage() retourne contenu + usage", async () => {
    const provider = makeProvider([
      { content: "Bonjour", usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 } },
    ]);
    router.register(provider);

    const result = await router.chatWithUsage("test", [{ role: "user", content: "hi" }]);
    expect(result.content).toBe("Bonjour");
    expect(result.usage).toBeDefined();
    expect(result.usage!.totalTokens).toBe(15);
  });

  it("fallback vers provider.chat() si chatWithUsage absent (provider legacy)", async () => {
    // Provider sans chatWithUsage (ex: plugin provider legacy)
    const provider: AiProvider = {
      id: "legacy",
      name: "Legacy",
      model: "m",
      chat: vi.fn().mockResolvedValue("legacy-content"),
      streamChat: vi.fn(),
      listModels: vi.fn(),
      embeddings: vi.fn(),
      isAvailable: vi.fn(),
    } as unknown as AiProvider;
    router.register(provider);

    router.resetUsage();
    const result = await router.chatWithUsage("legacy", [{ role: "user", content: "hi" }]);
    expect(result.content).toBe("legacy-content");
    expect(result.usage).toBeUndefined(); // pas d'usage dispo
    expect(router.getAndResetUsage()).toBeUndefined();
  });
});

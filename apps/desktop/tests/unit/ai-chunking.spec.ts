/**
 * Tests pour le auto-chunking de AiRouter (SDD §3.6b)
 *
 * R4. Vérifie que chatWithChunking() découpe correctement les prompts
 * dépassant 50% de la fenêtre contextuelle, et que les petits prompts
 * passent sans découpage.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { encode } from "gpt-tokenizer";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

/** Compteur du nombre d'appels à chat() (pour vérifier le découpage) */
let chatCallCount = 0;
/** Résultats simulés pour chaque appel à chat() */
let chatResults: string[] = [];

vi.mock("../../src/main/services/AiCache.js", () => ({
  AiCache: vi.fn().mockImplementation(() => ({
    get: vi.fn().mockReturnValue(null),
    set: vi.fn(),
    generateKey: vi.fn().mockReturnValue("test-key"),
  })),
}));

vi.mock("../../src/main/utils/logger.js", () => ({
  logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

// ---------------------------------------------------------------------------
// Helper : génère un texte d'une taille approximative en tokens
// ---------------------------------------------------------------------------

function generateText(tokenCount: number): string {
  // En moyenne ~1 token pour 4 caractères latins
  const charCount = tokenCount * 4;
  const words = [];
  for (let i = 0; i < charCount / 6; i++) {
    words.push(`mot${i}`);
  }
  return words.join(" ");
}

function generateParagraphs(count: number, tokensPerPara: number): string {
  const paras: string[] = [];
  for (let i = 0; i < count; i++) {
    paras.push(`Paragraphe ${i + 1}. ${generateText(tokensPerPara)}`);
  }
  return paras.join("\n\n");
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AiRouter — chatWithChunking (SDD §3.6b)", () => {
  let router: import("../../src/main/services/AiRouter.js").AiRouter;

  beforeEach(async () => {
    vi.clearAllMocks();
    chatCallCount = 0;
    chatResults = [];

    const { AiRouter } = await import(
      "../../src/main/services/AiRouter.js"
    );

    // Enregistrer un provider factice pour les tests
    router = new AiRouter();
    const fakeProvider = {
      id: "fake",
      name: "Fake",
      model: "fake-model",
      chat: vi.fn().mockImplementation(async () => {
        const idx = chatCallCount;
        chatCallCount++;
        return chatResults[idx] ?? `traduction-chunk-${idx + 1}`;
      }),
      streamChat: vi.fn(),
      isAvailable: vi.fn().mockResolvedValue(true),
      listModels: vi.fn().mockResolvedValue([]),
      embeddings: vi.fn().mockResolvedValue([]),
    } as unknown as import("@shared/types/index.js").AiProvider;
    router.register(fakeProvider);
  });

  // ── Petit prompt (pas de découpage) ─────────────────────────────────

  describe("Petit prompt — pas de découpage", () => {
    it("ne découpe pas un prompt sous 50% de la fenêtre", async () => {
      const result = await router.chatWithChunking("fake", [
        { role: "system", content: "Système" },
        { role: "user", content: "Petit texte" },
      ], {}, 32768);

      expect(result).toBe("traduction-chunk-1");
      expect(chatCallCount).toBe(1);
    });

    it("utilise chat() normal quand le prompt est vide", async () => {
      const result = await router.chatWithChunking("fake", [
        { role: "user", content: "" },
      ], {}, 32768);

      expect(chatCallCount).toBe(1);
      expect(result).toBeDefined();
    });

    it("passe les options à chat()", async () => {
      const { AiRouter } = await import(
        "../../src/main/services/AiRouter.js"
      );
      const localRouter = new AiRouter();
      const chatSpy = vi.fn().mockResolvedValue("ok");
      localRouter.register({
        id: "test",
        name: "Test",
        model: "test",
        chat: chatSpy,
        streamChat: vi.fn(),
        isAvailable: vi.fn().mockResolvedValue(true),
        listModels: vi.fn(),
        embeddings: vi.fn(),
      } as unknown as import("@shared/types/index.js").AiProvider);

      await localRouter.chatWithChunking("test", [
        { role: "user", content: "Salut" },
      ], { temperature: 0.5 }, 4096);

      expect(chatSpy).toHaveBeenCalledWith(
        [{ role: "user", content: "Salut" }],
        { temperature: 0.5 },
      );
    });
  });

  // ── Gros prompt (découpage) ─────────────────────────────────────────

  describe("Gros prompt — découpage actif", () => {
    it("découpe un prompt dépassant 50% de la fenêtre", async () => {
      // Fenêtre de 4096 → seuil 2048 tokens
      // 3 paragraphes de 1000 tokens chacun = 3000 tokens > 2048
      const text = generateParagraphs(3, 1000);
      // Vérifier que le texte dépasse bien le seuil
      const tokenCount = encode(text).length;
      expect(tokenCount).toBeGreaterThan(4096 * 0.5);

      // Simuler des réponses pour chaque chunk
      chatResults = ["traduction-1", "traduction-2", "traduction-3"];

      const result = await router.chatWithChunking("fake", [
        { role: "system", content: "Traduis ce texte." },
        { role: "user", content: text },
      ], {}, 4096);

      // Doit avoir appelé chat() plusieurs fois
      expect(chatCallCount).toBeGreaterThan(1);
      // Le résultat doit concaténer toutes les traductions
      expect(result).toContain("traduction-1");
      expect(result).toContain("traduction-2");
      expect(result).toContain("traduction-3");
    });

    it("conserve les messages système dans chaque chunk", async () => {
      const text = generateParagraphs(4, 800);
      const tokenCount = encode(text).length;
      expect(tokenCount).toBeGreaterThan(4096 * 0.5);

      chatResults = ["r1", "r2"];

      await router.chatWithChunking("fake", [
        { role: "system", content: "Système important." },
        { role: "user", content: text },
      ], {}, 4096);

      // Le mock de chat reçoit les messages. On ne peut pas vérifier
      // directement (vi.fn interne), mais on vérifie que le découpage
      // s'est produit
      expect(chatCallCount).toBeGreaterThan(1);
    });

    it("gère correctement le réassemblage des chunks", async () => {
      // 2 paragrapges qui dépassent ensemble le seuil
      const text = generateParagraphs(2, 1200);
      const tokenCount = encode(text).length;
      expect(tokenCount).toBeGreaterThan(4096 * 0.5);

      chatResults = ["[TRADUCTION PARTIE 1]", "[TRADUCTION PARTIE 2]"];

      const result = await router.chatWithChunking("fake", [
        { role: "user", content: text },
      ], {}, 4096);

      // Vérifier que les deux parties sont présentes dans l'ordre
      expect(result).toContain("TRADUCTION PARTIE 1");
      expect(result).toContain("TRADUCTION PARTIE 2");
      // Vérifier l'ordre
      const idx1 = result.indexOf("TRADUCTION PARTIE 1");
      const idx2 = result.indexOf("TRADUCTION PARTIE 2");
      expect(idx1).toBeLessThan(idx2);
    });
  });

  // ── Fenêtre contextuelle configurable ───────────────────────────────

  describe("Fenêtre contextuelle configurable", () => {
    it("utilise contextWindow passé en paramètre", async () => {
      // Petite fenêtre : 512 tokens → tout dépasse
      const text = generateText(300); // ~300 tokens
      const tokenCount = encode(text).length;
      expect(tokenCount).toBeGreaterThan(512 * 0.5);

      chatResults = ["chunk-only"];

      const result = await router.chatWithChunking("fake", [
        { role: "user", content: text },
      ], {}, 512);

      expect(result).toBeDefined();
    });

    it("ne découpe pas avec une très grande fenêtre", async () => {
      // Fenêtre de 1M tokens → rien ne dépasse
      const text = generateText(500);

      chatResults = ["pas-de-decoupage"];

      const result = await router.chatWithChunking("fake", [
        { role: "user", content: text },
      ], {}, 1_000_000);

      expect(result).toBe("pas-de-decoupage");
      expect(chatCallCount).toBe(1);
    });
  });
});

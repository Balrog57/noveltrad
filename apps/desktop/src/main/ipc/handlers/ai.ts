import { ipcMain } from "electron";
import { z } from "zod";
import { AiRouter } from "../../services/AiRouter.js";
import { OllamaProvider } from "../../services/providers/OllamaProvider.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { logger } from "../../utils/logger.js";

// ── Validation Zod ──────────────────────────────────────────────────────────

const chatMessageSchema = z.object({
  role: z.enum(["system", "user", "assistant"]),
  content: z.string(),
});

const streamChatPayloadSchema = z.object({
  providerId: z.string().min(1),
  messages: z.array(chatMessageSchema).min(1),
  options: z
    .object({
      temperature: z.number().min(0).max(2).optional(),
      maxTokens: z.number().int().positive().optional(),
      jsonMode: z.boolean().optional(),
    })
    .optional(),
});

// ── Instance partagée du routeur avec provider Ollama (lazy) ────────────

let _router: AiRouter | undefined;

function getRouter(): AiRouter {
  if (!_router) {
    const settings = new SettingsManager();
    _router = new AiRouter();
    const defaultModel = settings.get("defaultModel") as string;
    const ollamaHost = settings.get("ollamaHost") as string;
    _router.register(
      new OllamaProvider("ollama-default", "Ollama local", defaultModel, ollamaHost),
    );
  }
  return _router;
}

// Si d'autres modèles sont configurés, ils pourraient être enregistrés ici.

// ── Handlers ────────────────────────────────────────────────────────────────

export function registerAiHandlers(): void {
  /**
   * SDD §22.2 : Streaming de chat IA via canal IPC.
   * Le renderer reçoit des événements progressifs :
   *   - ai:stream-chunk  → un morceau de texte
   *   - ai:stream-end    → { done: true }
   *   - ai:stream-error  → { message: string }
   */
  ipcMain.handle(
    "ai:stream-chat",
    async (event, payload: unknown): Promise<{ success: boolean }> => {
      try {
        const parsed = streamChatPayloadSchema.parse(payload);

        const stream = getRouter().streamChat(
          parsed.providerId,
          parsed.messages,
          parsed.options,
        );

        for await (const chunk of stream) {
          event.sender.send("ai:stream-chunk", chunk);
        }

        event.sender.send("ai:stream-end", { done: true });
        return { success: true };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Erreur de streaming inconnue";
        logger.error(`[ai:stream-chat] ${message}`, err);
        event.sender.send("ai:stream-error", { message });
        return { success: false, error: message } as never;
      }
    },
  );
}

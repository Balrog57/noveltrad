import type { SettingsManager } from "./SettingsManager.js";
import type { OllamaModelInfo } from "@shared/types/index.js";
import { logger } from "../utils/logger.js";
// Phase 2 : shim fetch (electron.net sous Electron, globalThis.fetch en CLI).
import { fetch } from "../utils/fetch.js";

/**
 * Résultat du check de disponibilité Ollama.
 *
 * `error` et `errorKind` sont renseignés uniquement quand `available === false`,
 * pour permettre à l'UI d'afficher la cause réelle de l'échec
 * (ex: ECONNREFUSED ::1 → suspicion IPv6, AbortError → timeout, etc.).
 */
export interface OllamaAvailability {
  available: boolean;
  /** Host effectivement testé (utile pour l'affichage et le diagnostic). */
  host: string;
  /** Message d'erreur lisible (vide si succès). */
  error?: string;
  /**
   * Catégorie d'erreur pour faciliter le diagnostic côté UI.
   * - `network`      : ECONNREFUSED, ECONNRESET, échec DNS…
   * - `timeout`      : AbortError (dépassement du timeout de 5 s)
   * - `http`         : réponse HTTP reçue mais statut >= 400
   * - `parse`        : réponse non-JSON ou JSON invalide
   * - `unknown`      : autre
   */
  errorKind?: "network" | "timeout" | "http" | "parse" | "unknown";
}

function classifyError(e: unknown): "network" | "timeout" | "unknown" {
  const name = (e as { name?: string })?.name;
  const message = (e as Error)?.message ?? "";
  if (name === "AbortError" || /aborted|timeout/i.test(message)) {
    return "timeout";
  }
  if (
    name === "TypeError" ||
    /ECONNREFUSED|ECONNRESET|EHOSTUNREACH|ENOTFOUND|fetch failed|connection refused/i.test(
      message,
    )
  ) {
    return "network";
  }
  return "unknown";
}

export class OllamaManager {
  constructor(private settings: SettingsManager) {}

  private getHost(): string {
    return this.settings.get("ollamaHost") || "http://localhost:11434";
  }

  /**
   * Vérifie la disponibilité d'Ollama en interrogeant `/api/tags`.
   *
   * Retourne une structure enrichie `{ available, host, error?, errorKind? }`
   * plutôt qu'un simple booléen, afin que l'UI puisse afficher la cause
   * réelle d'un échec (très utile pour diagnostiquer le piège IPv6
   * `localhost` → `::1` vs Ollama bindé sur `127.0.0.1` sous Windows).
   */
  async isAvailable(): Promise<OllamaAvailability> {
    const host = this.getHost();
    const url = `${host}/api/tags`;
    logger.info(`[Ollama] isAvailable() → ${url}`);

    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (!res.ok) {
        const msg = `HTTP ${res.status} ${res.statusText}`;
        logger.warn(`[Ollama] Réponse non-OK depuis ${url} : ${msg}`);
        return { available: false, host, error: msg, errorKind: "http" };
      }
      const text = await res.text();
      let parsed: { models?: unknown[] };
      try {
        parsed = JSON.parse(text);
      } catch (parseErr) {
        const msg = `Réponse non-JSON depuis ${url} : ${(parseErr as Error).message}`;
        logger.warn(`[Ollama] ${msg}`);
        return { available: false, host, error: msg, errorKind: "parse" };
      }
      const count = Array.isArray(parsed.models) ? parsed.models.length : 0;
      logger.info(`[Ollama] Connexion OK (${count} modèles)`);
      return { available: true, host };
    } catch (e) {
      const err = e as Error & { code?: string };
      const kind = classifyError(e);
      const code = (err as { code?: string }).code;
      const detail = code ? `${err.name}: ${err.message} (code=${code})` : `${err.name}: ${err.message}`;
      logger.warn(`[Ollama] Échec de connexion à ${url} — [${kind}] ${detail}`);
      return { available: false, host, error: detail, errorKind: kind };
    }
  }

  async listModels(): Promise<OllamaModelInfo[]> {
    const host = this.getHost();
    const res = await fetch(`${host}/api/tags`, { signal: AbortSignal.timeout(10000) });
    if (!res.ok) {throw new Error(`HTTP ${res.status}`);}
    const parsed = await res.json();
    return (parsed.models ?? []).map((m: { name: string; size: number; details?: { parameter_size?: string; quantization_level?: string } }) => ({
      name: m.name,
      size: m.size,
      parameterSize: m.details?.parameter_size,
      quantizationLevel: m.details?.quantization_level,
    }));
  }

  async pullModel(
    name: string,
    onProgress?: (progress: {
      completed?: number;
      total?: number;
      status: string;
    }) => void,
  ): Promise<void> {
    const host = this.getHost();
    const url = `${host}/api/pull`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, stream: true }),
    });
    if (!res.ok) {throw new Error(`HTTP ${res.status}`);}
    const reader = res.body?.getReader();
    if (!reader) {throw new Error("No response body");}
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {break;}
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n").filter(Boolean);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        try {
          const progress = JSON.parse(line);
          onProgress?.(progress);
          if (progress.status === "success") {return;}
        } catch { /* ignore partial lines */ }
      }
    }
  }

  /** SDD §2.5 : envoie une courte requête pour vérifier que le modèle répond */
  async testModel(name: string): Promise<string> {
    const host = this.getHost();
    const url = `${host}/api/chat`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: name,
        messages: [{ role: "user", content: "Réponds uniquement par 'ok'." }],
        stream: false,
      }),
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) {throw new Error(`HTTP ${res.status}`);}
    const parsed = await res.json();
    return parsed.message?.content ?? "";
  }
}

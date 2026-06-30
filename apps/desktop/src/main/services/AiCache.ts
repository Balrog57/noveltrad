import type { ProjectDatabase } from "../db/connection.js";
import { createHash } from "node:crypto";

/**
 * Cache des réponses IA (SDD §22.1).
 * Stocke les réponses LLM dans SQLite pour éviter les appels redondants.
 * Chaque entrée a une TTL (durée de vie) après laquelle elle est considérée expirée.
 */
export class AiCache {
  constructor(private db: ProjectDatabase) {
    this.ensureTable();
  }

  /**
   * Crée la table `ai_cache` si elle n'existe pas déjà.
   */
  private ensureTable(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS ai_cache (
        key TEXT PRIMARY KEY,
        response TEXT NOT NULL,
        created_at TEXT NOT NULL,
        ttl_days INTEGER NOT NULL DEFAULT 7
      )
    `);
  }

  /**
   * Récupère une réponse mise en cache.
   * Vérifie la TTL : si l'entrée est expirée, elle est supprimée et `null` est retourné.
   * @returns La réponse JSON string ou `null` si absente ou expirée.
   */
  get(key: string): string | null {
    const row = this.db
      .prepare(
        "SELECT response, created_at, ttl_days FROM ai_cache WHERE key = ?",
      )
      .get([key]) as
      { response: string; created_at: string; ttl_days: number } | undefined;

    if (!row) return null;

    const createdAt = new Date(row.created_at);
    const expiresAt = new Date(createdAt);
    expiresAt.setDate(expiresAt.getDate() + row.ttl_days);

    if (new Date() > expiresAt) {
      // Entrée expirée, suppression
      this.db.prepare("DELETE FROM ai_cache WHERE key = ?").run([key]);
      return null;
    }

    return row.response;
  }

  /**
   * Stocke une réponse dans le cache.
   * Utilise INSERT OR REPLACE pour écraser les entrées existantes.
   * @param key Clé de cache
   * @param response Réponse textuelle du LLM
   * @param ttlDays Durée de vie en jours (défaut 7)
   */
  set(key: string, response: string, ttlDays = 7): void {
    this.db
      .prepare(
        "INSERT OR REPLACE INTO ai_cache (key, response, created_at, ttl_days) VALUES (?, ?, ?, ?)",
      )
      .run([key, response, new Date().toISOString(), ttlDays]);
  }

  /**
   * Génère une clé de cache déterministe à partir du prompt, du modèle et de la température.
   * Utilise SHA-256 pour produire un hash de 64 caractères hex.
   */
  generateKey(prompt: string, model: string, temperature: number): string {
    const input = `${model}:${temperature.toFixed(2)}:${prompt}`;
    return createHash("sha256").update(input).digest("hex");
  }
}

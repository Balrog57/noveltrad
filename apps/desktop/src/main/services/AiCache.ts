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

    if (!row) {return null;}

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
   * Après insertion, déclenche un nettoyage LRU si la taille totale dépasse le seuil.
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
    this.evictLru();
  }

  /**
   * Évince les entrées les plus anciennes du cache si la taille totale dépasse
   * le seuil spécifié (SDD §22.4 — Limite de taille 1 Go par défaut).
   * Supprime les entrées les plus anciennes (par created_at) jusqu'à repasser sous le seuil.
   *
   * @param maxSizeBytes Taille maximale du cache en octets (défaut 1 Go)
   */
  evictLru(maxSizeBytes: number = 1_073_741_824): void {
    const sizeRow = this.db
      .prepare(
        "SELECT COALESCE(SUM(LENGTH(key) + LENGTH(response)), 0) AS total_size FROM ai_cache",
      )
      .get() as { total_size: number } | undefined;

    if (!sizeRow || sizeRow.total_size <= maxSizeBytes) {return;}

    // Récupère les entrées les plus anciennes triées par created_at ASC
    const entries = this.db
      .prepare(
        "SELECT key, LENGTH(key) + LENGTH(response) AS entry_size FROM ai_cache ORDER BY created_at ASC",
      )
      .all() as Array<{ key: string; entry_size: number }>;

    let toFree = sizeRow.total_size - maxSizeBytes;

    for (const entry of entries) {
      if (toFree <= 0) {break;}
      this.db.prepare("DELETE FROM ai_cache WHERE key = ?").run([entry.key]);
      toFree -= entry.entry_size;
    }
  }

  /**
   * Génère une clé de cache déterministe à partir des prompts système/utilisateur,
   * du modèle et de la température (SDD §22.1).
   * Hash = SHA-256(systemPrompt + userPrompt + modelId + temperature), tronqué à 32 caractères hex.
   */
  generateKey(
    systemPrompt: string,
    userPrompt: string,
    modelId: string,
    temperature: number,
  ): string {
    const input = systemPrompt + userPrompt + modelId + String(temperature);
    return createHash("sha256").update(input).digest("hex").substring(0, 32);
  }
}

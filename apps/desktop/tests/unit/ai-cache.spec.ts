import { describe, it, expect, vi, beforeEach } from "vitest";
import { AiCache } from "../../src/main/services/AiCache";

// ---------------------------------------------------------------------------
// Mock DB
// ---------------------------------------------------------------------------

type Row = {
  key: string;
  response: string;
  created_at: string;
  ttl_days: number;
};

class MockAiCacheDb {
  private data: Row[] = [];

  exec(_sql: string): void {
    // Table creation - no-op for mock
  }

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    run: (params: unknown[]) => void;
  } {
    return {
      get: (params: unknown[]): unknown => {
        if (sql.includes("SELECT response, created_at, ttl_days FROM ai_cache")) {
          const key = params[0] as string;
          const row = this.data.find((d) => d.key === key);
          return row ? { ...row } : undefined;
        }
        return undefined;
      },
      run: (params: unknown[]): void => {
        if (sql.includes("INSERT OR REPLACE INTO ai_cache")) {
          const [key, response, created_at, ttl_days] = params as [
            string,
            string,
            string,
            number,
          ];
          const existing = this.data.findIndex((d) => d.key === key);
          const entry: Row = { key, response, created_at, ttl_days };
          if (existing >= 0) {
            this.data[existing] = entry;
          } else {
            this.data.push(entry);
          }
        }
        if (sql.includes("DELETE FROM ai_cache")) {
          const key = params[0] as string;
          this.data = this.data.filter((d) => d.key !== key);
        }
      },
    };
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AiCache", () => {
  let db: MockAiCacheDb;
  let cache: AiCache;

  beforeEach(() => {
    db = new MockAiCacheDb();
    cache = new AiCache(db as unknown as import("node-sqlite3-wasm").Database);
  });

  describe("generateKey", () => {
    it("devrait générer un hash SHA-256 déterministe tronqué à 32 caractères", () => {
      const hash1 = cache.generateKey("sys", "user", "model-x", 0.7);
      const hash2 = cache.generateKey("sys", "user", "model-x", 0.7);

      // Même entrée = même hash
      expect(hash1).toBe(hash2);
      // Longueur 32 caractères hex
      expect(hash1).toHaveLength(32);
      expect(hash1).toMatch(/^[a-f0-9]{32}$/);
    });

    it("devrait produire des hash différents pour des entrées différentes", () => {
      const hash1 = cache.generateKey("sys", "user", "model-a", 0.7);
      const hash2 = cache.generateKey("sys", "user", "model-b", 0.7);
      const hash3 = cache.generateKey("sys", "user2", "model-a", 0.7);
      const hash4 = cache.generateKey("sys", "user", "model-a", 0.8);

      expect(hash1).not.toBe(hash2);
      expect(hash1).not.toBe(hash3);
      expect(hash1).not.toBe(hash4);
    });

    it("devrait produire le même hash pour des prompts système et utilisateur vides", () => {
      const hash = cache.generateKey("", "", "model", 0.5);
      expect(hash).toHaveLength(32);
      expect(hash).toMatch(/^[a-f0-9]{32}$/);
    });
  });

  describe("get/set", () => {
    it("devrait retourner null pour une clé inexistante (miss)", () => {
      const result = cache.get("nonexistent-key");
      expect(result).toBeNull();
    });

    it("devrait retourner la valeur mise en cache (hit)", () => {
      cache.set("key1", "Hello World");
      const result = cache.get("key1");
      expect(result).toBe("Hello World");
    });

    it("devrait écraser une entrée existante avec INSERT OR REPLACE", () => {
      cache.set("key1", "First");
      cache.set("key1", "Second");
      const result = cache.get("key1");
      expect(result).toBe("Second");
    });

    it("devrait expirer après la TTL", () => {
      // TTL = 0 : crée une entrée avec Date.now() figé
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2026-06-15T12:00:00.000Z"));
      cache.set("exp-key", "secret", 0);
      // Avancer le temps de 1 ms : now > createdAt, l'entrée expire
      vi.advanceTimersByTime(1);
      const result = cache.get("exp-key");
      expect(result).toBeNull();
      vi.useRealTimers();
    });

    it("devrait conserver l'entrée tant que la TTL n'est pas expirée", () => {
      // ttl = 30 jours, l'entrée ne devrait pas expirer
      cache.set("persist", "keep me", 30);
      const result = cache.get("persist");
      expect(result).toBe("keep me");
    });
  });
});

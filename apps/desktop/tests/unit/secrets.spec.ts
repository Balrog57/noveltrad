/**
 * Tests pour le stockage sécurisé des clés API (SDD §21.4)
 *
 * Vérifie que SecretStore encrypte/décrypte correctement avec AES-256-GCM.
 * La clé maîtresse utilise safeStorage (si disponible) ou scrypt fallback.
 */

import { vi, describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

// Controllable flag for safeStorage mock (captured by closure in vi.mock factory)
let mockSafeStorageAvailable = false;

vi.mock("electron", () => {
  const secrets = new Map<string, string>();
  let counter = 0;
  return {
    safeStorage: {
      isEncryptionAvailable: () => mockSafeStorageAvailable,
      encryptString: (str: string) => {
        const id = String(counter++);
        secrets.set(id, str);
        return Buffer.from(id);
      },
      decryptString: (buf: Buffer) => secrets.get(buf.toString()) || "",
    },
    app: {
      getPath: () => path.join(os.tmpdir(), "noveltrad-test-electron-app"),
    },
  };
});

import { SecretStore, migratePlaintextApiKeys } from "../../src/main/utils/secrets.js";

const TEST_USER_DATA = path.join(os.tmpdir(), "noveltrad-test-secrets");

function cleanTestPath(dir: string): void {
  try {
    const keyFile = path.join(dir, ".noveltrad-master-key");
    if (fs.existsSync(keyFile)) { fs.unlinkSync(keyFile); }
    if (fs.existsSync(dir)) { fs.rmdirSync(dir); }
  } catch {
    // Ignore cleanup errors
  }
}

describe("SecretStore (SDD §21.4)", () => {
  // Clean slate before each test to avoid cross-test pollution
  beforeEach(() => {
    cleanTestPath(TEST_USER_DATA);
  });

  const store = new SecretStore(TEST_USER_DATA);

  describe("encrypt / decrypt", () => {
    it("encrypt puis decrypt retourne la valeur originale", () => {
      const original = "sk-1234567890abcdef";
      const encrypted = store.encrypt(original);
      const decrypted = store.decrypt(encrypted);
      expect(decrypted).toBe(original);
    });

    it("produit un texte chiffré différent pour chaque appel (IV aléatoire)", () => {
      const original = "sk-test-key";
      const r1 = store.encrypt(original);
      const r2 = store.encrypt(original);
      expect(r1).not.toBe(r2);
    });

    it("gère les clés API longues", () => {
      const longKey = "sk-" + "a".repeat(100);
      const encrypted = store.encrypt(longKey);
      const decrypted = store.decrypt(encrypted);
      expect(decrypted).toBe(longKey);
    });

    it("gère les clés API avec caractères spéciaux", () => {
      const original = "~!@#$%^&*()_+-=[]{}|;':\",./<>?`";
      const encrypted = store.encrypt(original);
      const decrypted = store.decrypt(encrypted);
      expect(decrypted).toBe(original);
    });
  });

  describe("gestion des valeurs vides", () => {
    it("encrypt d'une chaîne vide retourne chaîne vide", () => {
      expect(store.encrypt("")).toBe("");
    });

    it("decrypt d'une chaîne vide retourne chaîne vide", () => {
      expect(store.decrypt("")).toBe("");
    });

    it("decrypt d'une chaîne invalide retourne chaîne vide sans erreur", () => {
      expect(store.decrypt("not-base64!!!")).toBe("");
    });
  });

  describe("mauvaise clé", () => {
    it("decrypt avec une clé différente ne retourne pas la valeur originale", () => {
      const store1 = new SecretStore(path.join(os.tmpdir(), "noveltrad-key1"));
      const store2 = new SecretStore(path.join(os.tmpdir(), "noveltrad-key2"));

      const original = "sk-secret";
      const encrypted = store1.encrypt(original);
      const decrypted = store2.decrypt(encrypted);
      expect(decrypted).not.toBe(original);
    });
  });

  describe("withKey", () => {
    it("crée une instance avec une clé différente", () => {
      const store2 = store.withKey(path.join(os.tmpdir(), "noveltrad-other-key"));
      const encrypted = store2.encrypt("test");
      const decrypted = store2.decrypt(encrypted);
      expect(decrypted).toBe("test");
    });
  });

  describe("migratePlaintextApiKeys", () => {
    it("ne migre pas les clés déjà chiffrées", () => {
      const rows: Array<{ id: string; api_key: string | null }> = [];
      const db = {
        prepare: () => ({
          all: () => [{ id: "m1", api_key: "a".repeat(50) }],
          run: (..._params: string[]) => {
            rows.push({ id: _params[1], api_key: _params[0] });
          },
        }),
      };

      const migrated = migratePlaintextApiKeys(db as any, store);
      expect(migrated).toBe(0);
    });

    it("migre les clés en clair", () => {
      const rows: Array<{ id: string; api_key: string }> = [];
      const db = {
        prepare: () => ({
          all: () => [{ id: "m1", api_key: "sk-plaintext-key" }],
          run: (encrypted: string, id: string) => {
            rows.push({ id, api_key: encrypted });
          },
        }),
      };

      const migrated = migratePlaintextApiKeys(db as any, store);
      expect(migrated).toBe(1);
      expect(rows).toHaveLength(1);
      expect(rows[0].id).toBe("m1");
      // Vérifier que c'est chiffré (base64, plus long que l'original)
      expect(rows[0].api_key.length).toBeGreaterThan(20);
      expect(rows[0].api_key).not.toBe("sk-plaintext-key");
    });
  });

  describe("safeStorage integration", () => {
    it("utilise safeStorage quand disponible", () => {
      mockSafeStorageAvailable = true;

      const ssPath = path.join(os.tmpdir(), "noveltrad-test-safe-storage");
      cleanTestPath(ssPath);

      const ssStore = new SecretStore(ssPath);
      const original = "sk-safe-stored-key";
      const encrypted = ssStore.encrypt(original);
      const decrypted = ssStore.decrypt(encrypted);
      expect(decrypted).toBe(original);

      // Vérifier que le fichier de clé existe (safeStorage blob)
      const keyFile = path.join(ssPath, ".noveltrad-master-key");
      expect(fs.existsSync(keyFile)).toBe(true);

      // Vérifier que la clé est persistée entre instances
      const ssStore2 = new SecretStore(ssPath);
      const decrypted2 = ssStore2.decrypt(encrypted);
      expect(decrypted2).toBe(original);

      cleanTestPath(ssPath);
      mockSafeStorageAvailable = false;
    });

    it("utilise scrypt fallback quand safeStorage indisponible", () => {
      mockSafeStorageAvailable = false;

      const scryptPath = path.join(os.tmpdir(), "noveltrad-test-scrypt");
      cleanTestPath(scryptPath);

      const scryptStore = new SecretStore(scryptPath);
      const original = "sk-scrypt-fallback-key";
      const encrypted = scryptStore.encrypt(original);
      const decrypted = scryptStore.decrypt(encrypted);
      expect(decrypted).toBe(original);

      // Vérifier que le fichier de clé existe (scrypt blob)
      const keyFile = path.join(scryptPath, ".noveltrad-master-key");
      expect(fs.existsSync(keyFile)).toBe(true);

      // Vérifier la persistance entre instances
      const scryptStore2 = new SecretStore(scryptPath);
      const decrypted2 = scryptStore2.decrypt(encrypted);
      expect(decrypted2).toBe(original);

      cleanTestPath(scryptPath);
    });
  });
});

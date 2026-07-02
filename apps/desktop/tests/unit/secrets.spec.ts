/**
 * Tests pour le stockage sécurisé des clés API (SDD §21.4)
 *
 * Vérifie que SecretStore encrypte/décrypte correctement avec AES-256-GCM.
 */

import { describe, it, expect } from "vitest";
import { SecretStore, migratePlaintextApiKeys } from "../../src/main/utils/secrets.js";

// Clé de test (différente de la clé de production pour isolation)
const TEST_USER_DATA = "/tmp/noveltrad-test-secrets";

describe("SecretStore (SDD §21.4)", () => {
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
      const store1 = new SecretStore("/tmp/noveltrad-key1");
      const store2 = new SecretStore("/tmp/noveltrad-key2");

      const original = "sk-secret";
      const encrypted = store1.encrypt(original);
      const decrypted = store2.decrypt(encrypted);
      expect(decrypted).not.toBe(original);
    });
  });

  describe("withKey", () => {
    it("crée une instance avec une clé différente", () => {
      const store2 = store.withKey("/tmp/noveltrad-other-key");
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
});

/**
 * SDD §21.4 — Stockage sécurisé des clés API
 *
 * Utilise AES-256-GCM pour chiffrer les clés API avant stockage en SQLite.
 * La clé maîtresse est dérivée via electron.safeStorage quand disponible,
 * sinon via scrypt avec sel aléatoire stocké sur disque.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { app, safeStorage } from "electron";

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 16; // 128 bits
const AUTH_TAG_LENGTH = 16; // 128 bits
const MASTER_KEY_FILENAME = ".noveltrad-master-key";

export class SecretStore {
  private masterKey: Buffer;

  constructor(userData?: string) {
    const data = userData ?? app.getPath("userData");
    this.masterKey = this.loadOrCreateMasterKey(data);
  }

  /**
   * Charge ou crée la clé maîtresse AES-256.
   *
   * Stratégie :
   * 1. Si `safeStorage` est disponible (OS keyring), génère une clé aléatoire
   *    et la stocke chiffrée via `safeStorage.encryptString()`.
   * 2. Fallback (Linux sans keyring) : `scryptSync(userData, random salt, 32)`,
   *    le sel est stocké à côté du blob chiffré.
   */
  private loadOrCreateMasterKey(userDataPath: string): Buffer {
    const keyFilePath = path.join(userDataPath, MASTER_KEY_FILENAME);

    const safeStorageAvailable = this.isSafeStorageAvailable();

    // Load existing key file
    if (fs.existsSync(keyFilePath)) {
      const blob = fs.readFileSync(keyFilePath);
      const version = blob[0];

      if (version === 0x01 && safeStorageAvailable) {
        // safeStorage-encrypted blob
        try {
          const encrypted = blob.subarray(1);
          const decrypted = safeStorage.decryptString(encrypted);
          return Buffer.from(decrypted, "base64");
        } catch {
          // Decryption failed — recreate below
        }
      } else if (version === 0x02) {
        // scrypt-derived blob: [0x02, salt(32), key(32)]
        const salt = blob.subarray(1, 33);
        const storedKey = blob.subarray(33);
        if (storedKey.length === 32) {
          const derived = crypto.scryptSync(userDataPath, salt, 32);
          if (derived.equals(storedKey)) {
            return derived;
          }
        }
      }
    }

    // Create new master key
    fs.mkdirSync(userDataPath, { recursive: true });

    if (safeStorageAvailable) {
      const key = crypto.randomBytes(32);
      const encrypted = safeStorage.encryptString(key.toString("base64"));
      const blob = Buffer.concat([Buffer.from([0x01]), encrypted]);
      fs.writeFileSync(keyFilePath, blob);
      return key;
    }

    // Fallback: scrypt with random salt
    const salt = crypto.randomBytes(32);
    const derived = crypto.scryptSync(userDataPath, salt, 32);
    const blob = Buffer.concat([Buffer.from([0x02]), salt, derived]);
    fs.writeFileSync(keyFilePath, blob);
    return derived;
  }

  /**
   * Vérifie si safeStorage est disponible sans lever d'exception.
   */
  private isSafeStorageAvailable(): boolean {
    try {
      return safeStorage.isEncryptionAvailable();
    } catch {
      return false;
    }
  }

  /**
   * Chiffre une valeur en clair avec AES-256-GCM.
   * Retourne une chaîne base64 qui encapsule : iv + authTag + ciphertext.
   *
   * Format : base64(iv + authTag + ciphertext)
   * - iv : 16 bytes (128 bits)
   * - authTag : 16 bytes (128 bits, tag d'authentification GCM)
   * - ciphertext : données chiffrées
   */
  encrypt(plaintext: string): string {
    if (!plaintext) {return "";}

    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, this.masterKey, iv);

    const encrypted = Buffer.concat([
      cipher.update(Buffer.from(plaintext, "utf8")),
      cipher.final(),
    ]);

    const authTag = cipher.getAuthTag();

    // Concaténer iv + authTag + ciphertext
    const combined = Buffer.concat([iv, authTag, encrypted]);
    return combined.toString("base64");
  }

  /**
   * Déchiffre une valeur précédemment chiffrée.
   * Retourne la chaîne en clair, ou chaîne vide si l'entrée est vide.
   */
  decrypt(encrypted: string): string {
    if (!encrypted) {return "";}

    try {
      const combined = Buffer.from(encrypted, "base64");

      // Vérifier la longueur minimale
      if (combined.length < IV_LENGTH + AUTH_TAG_LENGTH + 1) {
        return "";
      }

      const iv = combined.subarray(0, IV_LENGTH);
      const authTag = combined.subarray(IV_LENGTH, IV_LENGTH + AUTH_TAG_LENGTH);
      const ciphertext = combined.subarray(IV_LENGTH + AUTH_TAG_LENGTH);

      const decipher = crypto.createDecipheriv(ALGORITHM, this.masterKey, iv);
      decipher.setAuthTag(authTag);

      const decrypted = Buffer.concat([
        decipher.update(ciphertext),
        decipher.final(),
      ]);

      return decrypted.toString("utf8");
    } catch {
      // En cas d'erreur (mauvaise clé, données corrompues), retourner vide
      return "";
    }
  }

  /**
   * Crée une nouvelle instance avec une clé différente (utile pour les tests).
   */
  withKey(userData: string): SecretStore {
    return new SecretStore(userData);
  }
}

/**
 * Migration des clés API en clair vers le stockage chiffré.
 * À appeler lors d'une mise à jour de la base de données.
 */
export function migratePlaintextApiKeys(
  db: {
    prepare: (sql: string) => {
      all: () => Array<{ id: string; api_key: string | null }>;
      run: (...params: string[]) => void;
    };
  },
  secretStore: SecretStore,
): number {
  const rows = db
    .prepare("SELECT id, api_key FROM models WHERE api_key IS NOT NULL AND api_key != ''")
    .all();

  let migrated = 0;
  for (const row of rows) {
    // Vérifier si déjà chiffré (détection simple : un AES-256-GCM fait > 44 chars en base64)
    if (row.api_key && row.api_key.length > 44) {
      continue;
    }
    const encrypted = secretStore.encrypt(row.api_key ?? "");
    (db.prepare("UPDATE models SET api_key = ? WHERE id = ?") as { run: (...params: string[]) => void }).run(encrypted, row.id);
    migrated++;
  }

  return migrated;
}

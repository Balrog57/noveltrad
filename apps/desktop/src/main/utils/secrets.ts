/**
 * SDD §21.4 — Stockage sécurisé des clés API
 *
 * Utilise AES-256-GCM pour chiffrer les clés API avant stockage en SQLite.
 * La clé maîtresse est dérivée du userData (SHA-256) car keytar n'est pas
 * disponible (pas dans les dépendances).
 *
 * En production, envisager de migrer vers :
 * - keytar (keyring OS : macOS Keychain, Windows Credential Manager, Linux secret-service)
 * - electron-store avec chiffrement
 * - safeStorage (Electron ≥ 28)
 */

import crypto from "node:crypto";
import { app } from "electron";

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 16; // 128 bits
const AUTH_TAG_LENGTH = 16; // 128 bits
const SALT = "NovelTrad-v1-key-derivation";

/**
 * Dérive une clé AES-256 à partir du chemin userData de l'application.
 * L'utilisation de userData garantit que la clé est liée à l'installation
 * (portable : chaque machine/session a sa propre clé).
 */
function deriveMasterKey(userData: string): Buffer {
  return crypto.scryptSync(userData, SALT, 32);
}

export class SecretStore {
  private masterKey: Buffer;

  constructor(userData?: string) {
    const data = userData ?? app.getPath("userData");
    this.masterKey = deriveMasterKey(data);
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
    if (!plaintext) return "";

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
    if (!encrypted) return "";

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

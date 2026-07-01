import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

// ── Mock DB SQLite en mémoire ──

/** Représente une entrée de la table translation_memory */
interface TmRow {
  id: string;
  project_id: string;
  source_text: string;
  target_text: string;
  source_language: string;
  target_language: string;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
}

/**
 * Mock minimal de la DB SQLite simulant le comportement de
 * `db.prepare(sql).get/all/run()` pour les requêtes utilisées par
 * TranslationMemoryEngine (store, importTmx, exportTmx).
 */
class MockDatabase {
  private rows: Map<string, TmRow> = new Map();
  private counter = 0;

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    all: (params: unknown[]) => unknown[];
    run: (params: unknown[]) => void;
  } {
    return {
      get: (params: unknown[]): unknown => {
        // SELECT id FROM translation_memory WHERE project_id = ? AND source_text = ?
        if (sql.includes("SELECT id") && sql.includes("source_text = ?")) {
          const projectId = params[0] as string;
          const sourceText = params[1] as string;
          for (const row of this.rows.values()) {
            if (row.project_id === projectId && row.source_text === sourceText) {
              return { id: row.id };
            }
          }
          return undefined;
        }
        // SELECT target_text FROM translation_memory WHERE project_id = ? AND source_text = ?
        if (sql.includes("SELECT target_text") && sql.includes("source_text = ?")) {
          const projectId = params[0] as string;
          const sourceText = params[1] as string;
          for (const row of this.rows.values()) {
            if (row.project_id === projectId && row.source_text === sourceText) {
              return { target_text: row.target_text };
            }
          }
          return undefined;
        }
        return undefined;
      },
      all: (params: unknown[]): unknown[] => {
        // SELECT source_text, target_text, source_language, target_language FROM translation_memory WHERE project_id = ?
        if (sql.includes("SELECT source_text, target_text, source_language, target_language")) {
          const projectId = params[0] as string;
          const result: TmRow[] = [];
          for (const row of this.rows.values()) {
            if (row.project_id === projectId) {
              result.push(row);
            }
          }
          return result;
        }
        // SELECT source_text, target_text, usage_count FROM translation_memory WHERE project_id = ?
        if (sql.includes("usage_count")) {
          const projectId = params[0] as string;
          const result: Array<{
            source_text: string;
            target_text: string;
            usage_count: number;
          }> = [];
          for (const row of this.rows.values()) {
            if (row.project_id === projectId) {
              result.push({
                source_text: row.source_text,
                target_text: row.target_text,
                usage_count: row.usage_count,
              });
            }
          }
          return result;
        }
        return [];
      },
      run: (params: unknown[]): void => {
        // INSERT INTO translation_memory (id, project_id, source_text, target_text, source_language, target_language, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)
        if (sql.includes("INSERT INTO translation_memory")) {
          const row: TmRow = {
            id: params[0] as string,
            project_id: params[1] as string,
            source_text: params[2] as string,
            target_text: params[3] as string,
            source_language: params[4] as string,
            target_language: params[5] as string,
            usage_count: 1,
            last_used_at: null,
            created_at: params[6] as string,
          };
          this.rows.set(row.id, row);
          this.counter++;
          return;
        }
        // UPDATE translation_memory SET target_text = ?, usage_count = usage_count + 1, last_used_at = ? WHERE id = ?
        if (sql.includes("UPDATE translation_memory")) {
          const targetText = params[0] as string;
          const lastUsedAt = params[1] as string;
          const id = params[2] as string;
          const row = this.rows.get(id);
          if (row) {
            row.target_text = targetText;
            row.usage_count += 1;
            row.last_used_at = lastUsedAt;
          }
          return;
        }
      },
    };
  }

  close(): void {
    // No-op pour le mock
  }

  /** Nombre total d'entrées stockées */
  get size(): number {
    return this.rows.size;
  }

  /** Récupère toutes les entrées (pour vérifications dans les tests) */
  getAllRows(): TmRow[] {
    return Array.from(this.rows.values());
  }
}

// ── Helpers ──

const PROJECT_ID = "00000000-0000-0000-0000-000000000001";

/** Crée un dossier temporaire unique */
function tmpDir(): string {
  return path.join(os.tmpdir(), `noveltrad-test-tmx-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
}

/** Génère un fichier TMX 1.4 valide avec les paires données */
function writeTmxFile(filePath: string, pairs: Array<{ source: string; target: string; sourceLang: string; targetLang: string }>): void {
  const tuEntries = pairs
    .map(
      (p) =>
        `    <tu>\n` +
        `      <tuv xml:lang="${p.sourceLang}"><seg>${p.source}</seg></tuv>\n` +
        `      <tuv xml:lang="${p.targetLang}"><seg>${p.target}</seg></tuv>\n` +
        `    </tu>`,
    )
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header creationtool="TestTool" segtype="sentence" o-tmf="TestTM" adminlang="en" srclang="en" datatype="plaintext"/>
  <body>
${tuEntries}
  </body>
</tmx>`;

  fs.writeFileSync(filePath, xml, "utf-8");
}

// ── Tests ──

describe("TranslationMemoryEngine — importTmx", () => {
  let dir: string;
  let db: MockDatabase;
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    dir = tmpDir();
    fs.mkdirSync(dir, { recursive: true });
    db = new MockDatabase();
    engine = new TranslationMemoryEngine(db as unknown as import("node-sqlite3-wasm").Database);
  });

  afterEach(() => {
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch {
      // Ignorer les erreurs de nettoyage
    }
  });

  it("devrait importer un fichier TMX valide et retourner le nombre d'entrées", () => {
    const tmxPath = path.join(dir, "import.tmx");
    writeTmxFile(tmxPath, [
      { source: "Hello world", target: "Bonjour le monde", sourceLang: "en", targetLang: "fr" },
      { source: "Good morning", target: "Bonjour", sourceLang: "en", targetLang: "fr" },
      { source: "Good night", target: "Bonne nuit", sourceLang: "en", targetLang: "fr" },
    ]);

    const count = engine.importTmx(tmxPath, PROJECT_ID);

    expect(count).toBe(3);
    expect(db.size).toBe(3);
  });

  it("devrait stocker les textes source et cible correctement", () => {
    const tmxPath = path.join(dir, "import.tmx");
    writeTmxFile(tmxPath, [
      { source: "Hello world", target: "Bonjour le monde", sourceLang: "en", targetLang: "fr" },
    ]);

    engine.importTmx(tmxPath, PROJECT_ID);

    const rows = db.getAllRows();
    expect(rows).toHaveLength(1);
    expect(rows[0].source_text).toBe("Hello world");
    expect(rows[0].target_text).toBe("Bonjour le monde");
    expect(rows[0].source_language).toBe("en");
    expect(rows[0].target_language).toBe("fr");
    expect(rows[0].project_id).toBe(PROJECT_ID);
  });

  it("devrait mettre à jour une entrée existante (usage_count incrémenté) lors d'un ré-import", () => {
    const tmxPath = path.join(dir, "import.tmx");
    writeTmxFile(tmxPath, [
      { source: "Hello world", target: "Bonjour le monde", sourceLang: "en", targetLang: "fr" },
    ]);

    // Premier import
    engine.importTmx(tmxPath, PROJECT_ID);
    expect(db.size).toBe(1);

    // Deuxième import de la même paire
    engine.importTmx(tmxPath, PROJECT_ID);
    expect(db.size).toBe(1); // Pas de doublon

    const rows = db.getAllRows();
    expect(rows[0].usage_count).toBe(2); // Incrémenté
  });

  it("devrait lever une erreur si le fichier TMX est invalide (sans balise <tmx>)", () => {
    const tmxPath = path.join(dir, "invalid.tmx");
    fs.writeFileSync(tmxPath, "<?xml version=\"1.0\"?>\n<notTmx><body></body></notTmx>", "utf-8");

    expect(() => engine.importTmx(tmxPath, PROJECT_ID)).toThrow(/tmx/i);
  });

  it("devrait retourner 0 si le fichier TMX ne contient aucune unité de traduction", () => {
    const tmxPath = path.join(dir, "empty.tmx");
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header creationtool="TestTool" segtype="sentence" o-tmf="TestTM" adminlang="en" srclang="en" datatype="plaintext"/>
  <body></body>
</tmx>`;
    fs.writeFileSync(tmxPath, xml, "utf-8");

    const count = engine.importTmx(tmxPath, PROJECT_ID);
    expect(count).toBe(0);
    expect(db.size).toBe(0);
  });
});

describe("TranslationMemoryEngine — exportTmx", () => {
  let dir: string;
  let db: MockDatabase;
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    dir = tmpDir();
    fs.mkdirSync(dir, { recursive: true });
    db = new MockDatabase();
    engine = new TranslationMemoryEngine(db as unknown as import("node-sqlite3-wasm").Database);
  });

  afterEach(() => {
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch {
      // Ignorer les erreurs de nettoyage
    }
  });

  it("devrait générer un fichier XML valide avec les balises TMX 1.4", () => {
    // Pré-remplir la DB via importTmx
    const importPath = path.join(dir, "source.tmx");
    writeTmxFile(importPath, [
      { source: "Hello", target: "Bonjour", sourceLang: "en", targetLang: "fr" },
    ]);
    engine.importTmx(importPath, PROJECT_ID);

    // Exporter
    const exportPath = path.join(dir, "export.tmx");
    engine.exportTmx(exportPath, PROJECT_ID);

    // Vérifier que le fichier existe et n'est pas vide
    expect(fs.existsSync(exportPath)).toBe(true);
    const stat = fs.statSync(exportPath);
    expect(stat.size).toBeGreaterThan(0);

    // Vérifier le contenu XML
    const content = fs.readFileSync(exportPath, "utf-8");
    expect(content).toContain("<?xml");
    expect(content).toContain("<tmx");
    expect(content).toContain('version="1.4"');
    expect(content).toContain("<header");
    expect(content).toContain("NovelTrad 2.0");
    expect(content).toContain("<body>");
    expect(content).toContain("<tu>");
    expect(content).toContain("<tuv");
    expect(content).toContain("<seg>");
    expect(content).toContain("Hello");
    expect(content).toContain("Bonjour");
  });

  it("devrait générer un TMX valide mais vide pour un projet sans entrées", () => {
    const exportPath = path.join(dir, "empty-export.tmx");
    engine.exportTmx(exportPath, PROJECT_ID);

    expect(fs.existsSync(exportPath)).toBe(true);
    const stat = fs.statSync(exportPath);
    expect(stat.size).toBeGreaterThan(0);

    const content = fs.readFileSync(exportPath, "utf-8");
    // Le XML doit être bien formé avec la structure TMX
    expect(content).toContain("<?xml");
    expect(content).toContain("<tmx");
    expect(content).toContain('version="1.4"');
    expect(content).toContain("<header");
    expect(content).toContain("<body>");
    // Aucune unité de traduction
    expect(content).not.toContain("<tu>");
  });
});

describe("TranslationMemoryEngine — round-trip export → import", () => {
  let dir: string;
  let dbSource: MockDatabase;
  let dbTarget: MockDatabase;

  beforeEach(() => {
    dir = tmpDir();
    fs.mkdirSync(dir, { recursive: true });
    dbSource = new MockDatabase();
    dbTarget = new MockDatabase();
  });

  afterEach(() => {
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch {
      // Ignorer les erreurs de nettoyage
    }
  });

  it("devrait préserver les données lors d'un round-trip export puis import", () => {
    // 1. Remplir la DB source avec des entrées via importTmx
    const sourceEngine = new TranslationMemoryEngine(
      dbSource as unknown as import("node-sqlite3-wasm").Database,
    );
    const importPath = path.join(dir, "source.tmx");
    writeTmxFile(importPath, [
      { source: "Hello world", target: "Bonjour le monde", sourceLang: "en", targetLang: "fr" },
      { source: "Good morning", target: "Bonjour", sourceLang: "en", targetLang: "fr" },
      { source: "Thank you very much", target: "Merci beaucoup", sourceLang: "en", targetLang: "fr" },
    ]);
    sourceEngine.importTmx(importPath, PROJECT_ID);
    expect(dbSource.size).toBe(3);

    // 2. Exporter depuis la DB source
    const exportPath = path.join(dir, "roundtrip.tmx");
    sourceEngine.exportTmx(exportPath, PROJECT_ID);
    expect(fs.existsSync(exportPath)).toBe(true);

    // 3. Importer dans une nouvelle DB cible (vide)
    const targetEngine = new TranslationMemoryEngine(
      dbTarget as unknown as import("node-sqlite3-wasm").Database,
    );
    const count = targetEngine.importTmx(exportPath, PROJECT_ID);

    // 4. Vérifier que les données sont préservées
    expect(count).toBe(3);
    expect(dbTarget.size).toBe(3);

    const targetRows = dbTarget.getAllRows();
    const sources = targetRows.map((r) => r.source_text).sort();
    const targets = targetRows.map((r) => r.target_text).sort();

    expect(sources).toEqual(["Good morning", "Hello world", "Thank you very much"]);
    expect(targets).toEqual(["Bonjour", "Bonjour le monde", "Merci beaucoup"]);
  });

  it("devrait préserver les langues source et cible lors du round-trip", () => {
    // Remplir la DB source
    const sourceEngine = new TranslationMemoryEngine(
      dbSource as unknown as import("node-sqlite3-wasm").Database,
    );
    const importPath = path.join(dir, "source.tmx");
    writeTmxFile(importPath, [
      { source: "Hello", target: "Bonjour", sourceLang: "en", targetLang: "fr" },
    ]);
    sourceEngine.importTmx(importPath, PROJECT_ID);

    // Exporter
    const exportPath = path.join(dir, "roundtrip-lang.tmx");
    sourceEngine.exportTmx(exportPath, PROJECT_ID);

    // Importer dans la cible
    const targetEngine = new TranslationMemoryEngine(
      dbTarget as unknown as import("node-sqlite3-wasm").Database,
    );
    targetEngine.importTmx(exportPath, PROJECT_ID);

    const targetRows = dbTarget.getAllRows();
    expect(targetRows).toHaveLength(1);
    expect(targetRows[0].source_language).toBe("en");
    expect(targetRows[0].target_language).toBe("fr");
  });
});

describe("TranslationMemoryEngine — schémas Zod tmxImportSchema / tmxExportSchema", () => {
  it("devrait valider un payload d'import TMX valide", async () => {
    const { tmxImportSchema } = await import("@shared/schemas/tmx.js");
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      filePath: "/tmp/test.tmx",
    };
    const result = tmxImportSchema.parse(payload);
    expect(result.projectId).toBe(payload.projectId);
    expect(result.filePath).toBe(payload.filePath);
  });

  it("devrait rejeter un payload d'import sans projectId", async () => {
    const { tmxImportSchema } = await import("@shared/schemas/tmx.js");
    expect(() => tmxImportSchema.parse({ filePath: "/tmp/test.tmx" })).toThrow();
  });

  it("devrait rejeter un payload d'import sans filePath", async () => {
    const { tmxImportSchema } = await import("@shared/schemas/tmx.js");
    expect(() =>
      tmxImportSchema.parse({ projectId: "00000000-0000-0000-0000-000000000001" }),
    ).toThrow();
  });

  it("devrait rejeter un projectId non-UUID", async () => {
    const { tmxImportSchema } = await import("@shared/schemas/tmx.js");
    expect(() =>
      tmxImportSchema.parse({ projectId: "not-a-uuid", filePath: "/tmp/test.tmx" }),
    ).toThrow();
  });

  it("devrait valider un payload d'export TMX valide", async () => {
    const { tmxExportSchema } = await import("@shared/schemas/tmx.js");
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      filePath: "/tmp/export.tmx",
    };
    const result = tmxExportSchema.parse(payload);
    expect(result.projectId).toBe(payload.projectId);
    expect(result.filePath).toBe(payload.filePath);
  });

  it("devrait rejeter un payload d'export sans filePath", async () => {
    const { tmxExportSchema } = await import("@shared/schemas/tmx.js");
    expect(() =>
      tmxExportSchema.parse({ projectId: "00000000-0000-0000-0000-000000000001" }),
    ).toThrow();
  });
});
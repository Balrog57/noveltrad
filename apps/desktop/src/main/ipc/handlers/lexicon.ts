import { ipcMain } from "electron";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase, runMigrations } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { LexiconRepository } from "../../db/repositories/LexiconRepository.js";
import { LexiconEngine } from "../../services/LexiconEngine.js";
import { AiRouter } from "../../services/AiRouter.js";
import { OllamaProvider } from "../../services/providers/OllamaProvider.js";
import {
  lexiconListSchema,
  lexiconSaveSchema,
  lexiconDeleteSchema,
  lexiconImportSchema,
  lexiconExportSchema,
  lexiconExtractCandidatesSchema,
  lexiconFindConflictsSchema,
  lexiconSuggestSchema,
} from "@shared/schemas/lexicon.js";
import type { LexiconEntry } from "@shared/types/index.js";
import type { Database as SqliteDatabase } from "node-sqlite3-wasm";
import path from "node:path";
import fs from "node:fs";
import { assertWithinProject } from "../../utils/paths.js";

const settings = new SettingsManager();
const migrationsDir = path.join(__dirname, "../../db/migrations");
const lexiconEngine = new LexiconEngine();

/**
 * Résout le chemin du dossier projet à partir de `projectId`.
 */
function resolveProjectPath(projectId: string): string {
  const recent = (settings.get("recentProjects") as string[] | undefined) ?? [];
  const projectPath = recent.find((p) => {
    if (!fs.existsSync(path.join(p, "project.db"))) return false;
    const db = createProjectDatabase(p);
    const found = new ProjectRepository(db).getById(projectId);
    db.close();
    return found !== undefined;
  });
  if (!projectPath) throw new Error(`Projet non trouvé : ${projectId}`);
  // SDD §21.3 — Vérifier que le chemin projet est dans un répertoire légitime
  const allRecent = (settings.get("recentProjects") as string[] | undefined) ?? [];
  const validBase = allRecent.find((base) => {
    try {
      assertWithinProject(path.dirname(base), projectPath);
      return true;
    } catch {
      return false;
    }
  });
  if (!validBase) {
    throw new Error(`Path traversal détecté pour le projet : ${projectPath}`);
  }
  return projectPath;
}

/** Ouvre la DB du projet et exécute les migrations */
function openProjectDb(projectPath: string) {
  const db = createProjectDatabase(projectPath);
  runMigrations(db, migrationsDir);
  return db;
}

export function registerLexiconHandlers(): void {
  // Lister les entrées de lexique
  ipcMain.handle("lexicon:list", async (_event, payload) => {
    const { projectId } = lexiconListSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    const db = openProjectDb(projectPath);
    try {
      const entries = new LexiconRepository(db).listByProject(projectId);
      // Restaurer les champs metadata (gender, pronunciation)
      return entries.map((e) => mapFromDb(e));
    } finally {
      db.close();
    }
  });

  // Sauvegarder (insert ou update) une entrée de lexique
  ipcMain.handle("lexicon:save", async (_event, payload) => {
    const { projectId, entry } = lexiconSaveSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    const db = openProjectDb(projectPath);
    try {
      const repo = new LexiconRepository(db);
      // Stocker gender et pronunciation dans metadata si présents
      const mapped = mapToDb(entry);
      // Vérifier si l'entrée existe déjà (insert vs update)
      const existing = repo.getById(entry.id);
      if (existing) {
        repo.update(mapped);
      } else {
        repo.create(mapped);
      }
      return { success: true, entry: mapFromDb(mapped) };
    } finally {
      db.close();
    }
  });

  // Supprimer une entrée de lexique
  ipcMain.handle("lexicon:delete", async (_event, payload) => {
    const { projectId, entryId } = lexiconDeleteSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    const db = openProjectDb(projectPath);
    try {
      new LexiconRepository(db).delete(entryId);
      return { success: true };
    } finally {
      db.close();
    }
  });

  // Importer des entrées
  ipcMain.handle("lexicon:import", async (_event, payload) => {
    const { projectId, format, data } = lexiconImportSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    const db = openProjectDb(projectPath);
    try {
      const repo = new LexiconRepository(db);
      const imported = parseImportData(format, data, projectId);
      // Charger les IDs existants une seule fois pour éviter O(n²)
      const existingIds = new Set(
        repo.listByProject(projectId).map((e) => e.id),
      );
      let count = 0;
      for (const entry of imported) {
        const mapped = mapToDb(entry);
        if (existingIds.has(entry.id)) {
          repo.update(mapped);
        } else {
          repo.create(mapped);
        }
        count++;
      }
      return { success: true, count };
    } finally {
      db.close();
    }
  });

  // Exporter les entrées
  ipcMain.handle("lexicon:export", async (_event, payload) => {
    const { projectId, format } = lexiconExportSchema.parse(payload);
    const projectPath = resolveProjectPath(projectId);
    const db = openProjectDb(projectPath);
    try {
      const entries = new LexiconRepository(db)
        .listByProject(projectId)
        .map((e) => mapFromDb(e));
      return lexiconEngine.exportEntries(entries, format);
    } finally {
      db.close();
    }
  });

  // Extraire les termes candidats
  ipcMain.handle("lexicon:extract-candidates", async (_event, payload) => {
    const { text, language } = lexiconExtractCandidatesSchema.parse(payload);
    return lexiconEngine.extractCandidates(text, language);
  });

  // Détecter les conflits dans le lexique
  ipcMain.handle("lexicon:find-conflicts", async (_event, payload) => {
    const { entries } = lexiconFindConflictsSchema.parse(payload);
    return lexiconEngine.findConflicts(entries);
  });

  // Suggérer une traduction pour un terme inconnu via IA
  ipcMain.handle("lexicon:suggest", async (_event, payload) => {
    const { term, context, projectId } = lexiconSuggestSchema.parse(payload);

    // Résoudre le chemin projet et récupérer les paramètres LLM
    const projectPath = resolveProjectPath(projectId);
    const ollamaHost = (settings.get("ollamaHost") as string) ?? "http://localhost:11434";
    const defaultModel = (settings.get("defaultModel") as string) ?? "qwen3.5:9b";

    // Créer un AiRouter avec le provider Ollama
    const aiRouter = new AiRouter();
    aiRouter.register(
      new OllamaProvider("ollama-default", "Ollama local", defaultModel, ollamaHost),
    );

    return lexiconEngine.suggestTranslation(term, context, aiRouter, "ollama-default");
  });
}

/** Parse des données importées selon le format */
function parseImportData(
  format: "csv" | "json" | "tsv",
  data: string,
  projectId: string,
): LexiconEntry[] {
  switch (format) {
    case "json": {
      const parsed = JSON.parse(data);
      const arr = Array.isArray(parsed) ? parsed : [parsed];
      return arr.map((item: Record<string, unknown>) => ({
        id: crypto.randomUUID(),
        projectId,
        term: String(item.term ?? ""),
        translation: String(item.translation ?? ""),
        category: String(item.category ?? "general"),
        aliases: Array.isArray(item.aliases) ? item.aliases.map(String) : [],
        locked: Boolean(item.locked),
        forbidden: Array.isArray(item.forbidden)
          ? item.forbidden.map(String)
          : undefined,
        priority: Number(item.priority ?? 5),
        description: item.description ? String(item.description) : undefined,
        notes: item.notes ? String(item.notes) : undefined,
        gender: item.gender ? String(item.gender) : undefined,
        pronunciation: item.pronunciation
          ? String(item.pronunciation)
          : undefined,
      }));
    }
    case "csv":
    case "tsv": {
      const sep = format === "csv" ? "," : "\t";
      const lines = data.trim().split("\n");
      if (lines.length < 2) return [];
      const headers = parseCsvLine(lines[0], sep);
      const entries: LexiconEntry[] = [];
      for (let i = 1; i < lines.length; i++) {
        const values = parseCsvLine(lines[i], sep);
        const row: Record<string, string> = {};
        headers.forEach((h, idx) => {
          row[h] = values[idx] ?? "";
        });
        entries.push({
          id: crypto.randomUUID(),
          projectId,
          term: row.term ?? "",
          translation: row.translation ?? "",
          category: row.category ?? "general",
          aliases: row.aliases ? row.aliases.split(";").filter(Boolean) : [],
          locked: row.locked === "1" || row.locked === "true",
          forbidden: row.forbidden
            ? row.forbidden.split(";").filter(Boolean)
            : undefined,
          priority: Number(row.priority ?? 5),
          description: row.description || undefined,
          notes: row.notes || undefined,
        });
      }
      return entries;
    }
  }
}

/** Parse une ligne CSV/TSV en respectant les guillemets */
function parseCsvLine(line: string, sep: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;
  for (const ch of line) {
    if (ch === '"') {
      inQuotes = !inQuotes;
    } else if (ch === sep && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  result.push(current.trim());
  return result;
}

/**
 * Mappe une entrée DB vers le type LexiconEntry (restaure metadata).
 * Les champs `gender` et `pronunciation` sont stockés dans le champ
 * `metadata` JSON de la table lexicon. Pas de migration nécessaire.
 */
function mapFromDb(entry: LexiconEntry): LexiconEntry {
  const meta = entry.metadata ?? {};
  return {
    ...entry,
    gender: (meta as Record<string, unknown>).gender
      ? String((meta as Record<string, unknown>).gender)
      : undefined,
    pronunciation: (meta as Record<string, unknown>).pronunciation
      ? String((meta as Record<string, unknown>).pronunciation)
      : undefined,
  };
}

/**
 * Mappe une entrée vers le format DB (sauvegarde gender/pronunciation dans metadata).
 */
function mapToDb(entry: LexiconEntry): LexiconEntry {
  const meta: Record<string, unknown> = { ...(entry.metadata ?? {}) };
  if (entry.gender) meta.gender = entry.gender;
  if (entry.pronunciation) meta.pronunciation = entry.pronunciation;
  return {
    ...entry,
    metadata: Object.keys(meta).length > 0 ? meta : undefined,
  };
}

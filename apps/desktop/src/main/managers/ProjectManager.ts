import fs from "node:fs";
import path from "node:path";

import type {
  CreateProjectPayload,
  Project,
  Chapter,
} from "@shared/types/index.js";
import type { SettingsManager } from "./SettingsManager.js";
import { createProjectDatabase, runMigrations } from "../db/connection.js";
import { ProjectRepository } from "../db/repositories/ProjectRepository.js";
import { expandHome } from "../utils/paths.js";
import chardet from "chardet";
import iconv from "iconv-lite";
import mammoth from "mammoth";
import AdmZip from "adm-zip";
import * as cheerio from "cheerio";
import { franc, francAll } from "franc";

/** Formats de fichiers supportés pour l'import */
const SUPPORTED_EXTENSIONS = [".txt", ".md", ".docx", ".epub"] as const;

/** Patterns de détection de chapitres (SDD §5.5) */
const DEFAULT_CHAPTER_PATTERNS = [
  /^Chapter\s+\d+/im,
  /^Chapitre\s+\d+/im,
  /^第\s*\d+\s*章/im,
  /^CHAPTER\s+\d+/im,
];

/** Seuil de confiance minimal pour la détection de langue (SDD §5.7) */
const LANGUAGE_CONFIDENCE_THRESHOLD = 0.8;

const migrationsDir = path.join(__dirname, "../../db/migrations");

export class ProjectManager {
  constructor(private settings: SettingsManager) {}

  async create(payload: CreateProjectPayload): Promise<Project> {
    const parentPath = expandHome(payload.parentPath);
    const projectDir = path.join(parentPath, payload.name);

    if (fs.existsSync(projectDir)) {
      throw new Error(`Le projet existe deja : ${projectDir}`);
    }

    fs.mkdirSync(projectDir, { recursive: true });
    fs.mkdirSync(path.join(projectDir, "chapitres"));
    fs.mkdirSync(path.join(projectDir, "source"));
    fs.mkdirSync(path.join(projectDir, "traductions"));
    fs.mkdirSync(path.join(projectDir, "lexique"));
    fs.mkdirSync(path.join(projectDir, "exports"));
    fs.mkdirSync(path.join(projectDir, "cache"));
    fs.mkdirSync(path.join(projectDir, "logs"));

    // SDD §5.1 — Écrire le fichier de configuration du projet
    const projectConfig = {
      id: crypto.randomUUID(),
      name: payload.name,
      author: payload.author ?? "",
      sourceLanguage: payload.sourceLanguage,
      targetLanguage: payload.targetLanguage,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: "1.0.0",
      parser: {
        chapterSeparator: "^Chapter\\s+\\d+",
        paragraphSeparator: "\\n\\n",
      },
    };
    fs.writeFileSync(
      path.join(projectDir, "config.json"),
      JSON.stringify(projectConfig, null, 2),
      "utf-8",
    );

    const db = createProjectDatabase(projectDir);
    runMigrations(db, migrationsDir);

    const project: Project = {
      id: crypto.randomUUID(),
      name: payload.name,
      author: payload.author,
      sourceLanguage: payload.sourceLanguage,
      targetLanguage: payload.targetLanguage,
      path: projectDir,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    new ProjectRepository(db).create(project);
    db.close();

    await this.addToRecent(project);
    return project;
  }

  async open(projectPath: string): Promise<Project> {
    const db = createProjectDatabase(projectPath);
    runMigrations(db, migrationsDir);
    const repo = new ProjectRepository(db);
    let project = repo.getByPath(projectPath);

    if (!project) {
      const projectName = path.basename(projectPath);
      project = {
        id: crypto.randomUUID(),
        name: projectName,
        sourceLanguage: "zh",
        targetLanguage: "fr",
        path: projectPath,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      repo.create(project);
    }

    db.close();
    await this.addToRecent(project);
    return project;
  }

  async listRecent(): Promise<Project[]> {
    const recent =
      (this.settings.get("recentProjects") as string[] | undefined) ?? [];
    const projects: Project[] = [];
    for (const projectPath of recent) {
      try {
        const project = await this.open(projectPath);
        projects.push(project);
      } catch (err) {
        console.warn(
          `Impossible d'ouvrir le projet recent ${projectPath}:`,
          err,
        );
      }
    }
    return projects;
  }

  async delete(projectId: string, removeFiles: boolean): Promise<void> {
    const recent =
      (this.settings.get("recentProjects") as string[] | undefined) ?? [];
    const projectPath = recent.find((p) => {
      const dbPath = path.join(p, "project.db");
      if (!fs.existsSync(dbPath)) return false;
      const db = createProjectDatabase(p);
      const project = new ProjectRepository(db).getById(projectId);
      db.close();
      return project !== undefined;
    });

    if (!projectPath) {
      throw new Error(`Projet non trouve : ${projectId}`);
    }

    if (removeFiles && fs.existsSync(projectPath)) {
      fs.rmSync(projectPath, { recursive: true, force: true });
    }

    const nextRecent = recent.filter((p) => p !== projectPath);
    this.settings.set("recentProjects", nextRecent);
  }

  async importSource(projectId: string, filePath: string): Promise<Chapter[]> {
    const projectPath = this.resolveProjectPath(projectId);

    const ext = path.extname(filePath).toLowerCase();
    if (!(SUPPORTED_EXTENSIONS as readonly string[]).includes(ext)) {
      throw new Error(
        `Format non supporte : ${ext}. Formats accepts : ${SUPPORTED_EXTENSIONS.join(", ")}`,
      );
    }

    // Extraction du texte selon le format (SDD §5.4, §5.9)
    let text: string;
    switch (ext) {
      case ".docx":
        text = await this.extractDocx(filePath);
        break;
      case ".epub":
        text = await this.extractEpub(filePath);
        break;
      default:
        // .txt et .md — détection d'encodage avec chardet
        text = this.extractPlainText(filePath);
        break;
    }

    // Détection de langue (SDD §5.7)
    const detectedLanguage = this.detectLanguage(text);

    // Découpage en chapitres (SDD §5.5)
    const chapterTexts = this.splitIntoChapters(text, projectPath);

    // Copie du fichier source dans le dossier du projet
    const fileName = path.basename(filePath, ext);
    fs.copyFileSync(
      filePath,
      path.join(projectPath, "chapitres", `${fileName}${ext}`),
    );

    // Récupérer le dernier orderIndex existant
    const existingChapters = await this.listChapters(projectId);
    let nextOrderIndex =
      existingChapters.length > 0
        ? Math.max(...existingChapters.map((c) => c.orderIndex)) + 1
        : 0;

    const db = createProjectDatabase(projectPath);
    runMigrations(db, migrationsDir);

    const createdChapters: Chapter[] = [];

    for (const chapterText of chapterTexts) {
      const chapterId = crypto.randomUUID();
      const title =
        chapterTexts.length === 1
          ? fileName
          : `${fileName} — Chapitre ${createdChapters.length + 1}`;

      // Stocker la source nettoyée en .md
      fs.writeFileSync(
        path.join(projectPath, "source", `${chapterId}.md`),
        chapterText,
        "utf-8",
      );

      // Métadonnées de détection de langue
      const metadata: Record<string, unknown> = {};
      if (detectedLanguage) {
        metadata.detectedLanguage = detectedLanguage.code;
        metadata.detectedLanguageName = detectedLanguage.name;
        metadata.detectedLanguageConfidence = detectedLanguage.confidence;
      }

      // Créer le chapitre dans la DB
      db.prepare(
        `
        INSERT INTO chapters (id, project_id, title, source_path, order_index, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `,
      ).run([
        chapterId,
        projectId,
        title,
        filePath,
        nextOrderIndex,
        "pending",
        new Date().toISOString(),
        new Date().toISOString(),
      ]);

      // Découper en paragraphes
      const paragraphs = chapterText
        .split(/\n\n+/)
        .map((t) => t.trim())
        .filter(Boolean)
        .map((sourceText, index) => ({
          id: crypto.randomUUID(),
          chapter_id: chapterId,
          index_in_chapter: index + 1,
          source_text: sourceText,
          translated_text: null,
          status: "pending",
        }));

      const insertParagraph = db.prepare(`
        INSERT INTO paragraphs (id, chapter_id, index_in_chapter, source_text, translated_text, status)
        VALUES (?, ?, ?, ?, ?, ?)
      `);
      for (const p of paragraphs) {
        insertParagraph.run([
          p.id,
          p.chapter_id,
          p.index_in_chapter,
          p.source_text,
          p.translated_text,
          p.status,
        ]);
      }

      createdChapters.push({
        id: chapterId,
        projectId,
        title,
        sourcePath: filePath,
        orderIndex: nextOrderIndex,
        status: "pending",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      nextOrderIndex++;
    }

    db.close();
    return createdChapters;
  }

  async listChapters(projectId: string): Promise<Chapter[]> {
    const projectPath = (
      (this.settings.get("recentProjects") as string[]) ?? []
    ).find((p) => {
      const db = createProjectDatabase(p);
      const found = new ProjectRepository(db).getById(projectId);
      db.close();
      return found !== undefined;
    });

    if (!projectPath) {
      throw new Error(`Projet non trouve : ${projectId}`);
    }

    const db = createProjectDatabase(projectPath);
    const rows = db
      .prepare(
        "SELECT * FROM chapters WHERE project_id = ? ORDER BY order_index",
      )
      .all([projectId]) as Record<string, unknown>[];
    db.close();

    return rows.map((row) => ({
      id: String(row.id),
      projectId: String(row.project_id),
      title: row.title ? String(row.title) : undefined,
      sourcePath: row.source_path ? String(row.source_path) : undefined,
      orderIndex: Number(row.order_index),
      status: String(row.status) as Chapter["status"],
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at),
    }));
  }
  private async addToRecent(project: Project): Promise<void> {
    const recent =
      (this.settings.get("recentProjects") as string[] | undefined) ?? [];
    const next = [
      project.path,
      ...recent.filter((p) => p !== project.path),
    ].slice(0, 10);
    this.settings.set("recentProjects", next);
  }

  /**
   * Résout le chemin d'un projet à partir de son ID.
   */
  private resolveProjectPath(projectId: string): string {
    const projectPath = (
      (this.settings.get("recentProjects") as string[]) ?? []
    ).find((p) => {
      const db = createProjectDatabase(p);
      const found = new ProjectRepository(db).getById(projectId);
      db.close();
      return found !== undefined;
    });

    if (!projectPath) {
      throw new Error(`Projet non trouve : ${projectId}`);
    }

    return projectPath;
  }

  /**
   * Extrait le texte d'un fichier DOCX via mammoth (SDD §5.4).
   */
  private async extractDocx(filePath: string): Promise<string> {
    const buffer = fs.readFileSync(filePath);
    const result = await mammoth.convertToHtml({ buffer });
    return this.htmlToMarkdown(result.value);
  }

  /**
   * Extrait le texte d'un fichier EPUB via adm-zip + cheerio (SDD §5.9).
   */
  private async extractEpub(filePath: string): Promise<string> {
    const zip = new AdmZip(filePath);
    const entries = zip.getEntries();
    const textParts: string[] = [];

    for (const entry of entries) {
      // Ignorer les fichiers non-HTML/XHTML et les fichiers système
      const entryName = entry.entryName.toLowerCase();
      if (
        entryName.startsWith("mimetype") ||
        entryName.startsWith("meta-inf") ||
        entryName.startsWith(".")
      ) {
        continue;
      }

      const isContent =
        entryName.endsWith(".xhtml") ||
        entryName.endsWith(".html") ||
        entryName.endsWith(".htm");

      if (isContent && !entry.isDirectory) {
        try {
          const content = entry.getData().toString("utf-8");
          const $ = cheerio.load(content);
          // Extraire le texte en préservant la structure
          $("script, style, nav, header, footer, .toc, .nav").remove();
          const text = $.text();
          if (text.trim()) {
            textParts.push(text);
          }
        } catch {
          // Fichier EPUB corrompu ou non lisible — ignorer cet entry
          console.warn(
            `[ProjectManager] Entry EPUB illisible : ${entry.entryName}`,
          );
        }
      }
    }

    if (textParts.length === 0) {
      throw new Error("Aucun contenu texte trouve dans le fichier EPUB.");
    }

    return textParts.join("\n\n");
  }

  /**
   * Extrait le texte d'un fichier TXT/MD avec détection d'encodage.
   */
  private extractPlainText(filePath: string): string {
    const encoding = chardet.detectFileSync(filePath) ?? "utf-8";
    const buffer = fs.readFileSync(filePath);
    return iconv.decode(buffer, encoding as string);
  }

  /**
   * Convertit du HTML en texte markdown simple (SDD §5.4).
   * Utilisé pour le conversion DOCX → texte.
   */
  htmlToMarkdown(html: string): string {
    let text = html;

    // Supprimer les balises script, style, nav, header, footer
    text = text.replace(/<script[\s\S]*?<\/script>/gi, "");
    text = text.replace(/<style[\s\S]*?<\/style>/gi, "");
    text = text.replace(/<nav[\s\S]*?<\/nav>/gi, "");
    text = text.replace(/<header[\s\S]*?<\/header>/gi, "");
    text = text.replace(/<footer[\s\S]*?<\/footer>/gi, "");

    // Convertir les titres en markdown
    for (let i = 6; i >= 1; i--) {
      const regex = new RegExp(`<h${i}[^>]*>([\\s\\S]*?)<\\/h${i}>`, "gi");
      text = text.replace(regex, (_match, content) => {
        return `${"#".repeat(i)} ${content.trim()}\n`;
      });
    }

    // Convertir les listes
    text = text.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_match, content) => {
      return `- ${content.trim()}\n`;
    });

    // Gras
    text = text.replace(
      /<(?:strong|b)[^>]*>([\s\S]*?)<\/(?:strong|b)>/gi,
      (_match, content) => `**${content.trim()}**`,
    );

    // Italique
    text = text.replace(
      /<(?:em|i)[^>]*>([\s\S]*?)<\/(?:em|i)>/gi,
      (_match, content) => `*${content.trim()}*`,
    );

    // Sauts de ligne
    text = text.replace(/<br\s*\/?>/gi, "\n");

    // Paragraphes — convertir en double saut de ligne
    text = text.replace(/<\/p>/gi, "\n\n");
    text = text.replace(/<p[^>]*>/gi, "");

    // Supprimer toutes les balises restantes
    text = text.replace(/<[^>]+>/g, "");

    // Décoder les entités HTML courantes
    text = text.replace(/&amp;/g, "&");
    text = text.replace(/&lt;/g, "<");
    text = text.replace(/&gt;/g, ">");
    text = text.replace(/&quot;/g, '"');
    text = text.replace(/&#39;/g, "'");
    text = text.replace(/&nbsp;/g, " ");

    // Nettoyer les espaces multiples et les sauts de ligne excessifs
    text = text
      .replace(/[ \t]+/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();

    return text;
  }

  /**
   * Détecte la langue du texte (SDD §5.7).
   * Retourne le code ISO 639-3, le nom et la confiance, ou null si indéterminé.
   */
  private detectLanguage(
    text: string,
  ): { code: string; name: string; confidence: number } | null {
    if (text.length < 20) {
      return null;
    }

    try {
      const results = francAll(text, { minLength: 20 });
      if (results.length === 0) return null;

      const [code, score] = results[0];

      // 'und' = indéterminé
      if (code === "und") return null;

      if (score < LANGUAGE_CONFIDENCE_THRESHOLD) {
        console.warn(
          `[ProjectManager] Confiance de détection de langue faible : ${code} (${(score * 100).toFixed(1)}%). Seuil : ${LANGUAGE_CONFIDENCE_THRESHOLD * 100}%`,
        );
      }

      return {
        code,
        name: this.getLanguageName(code),
        confidence: score,
      };
    } catch {
      console.warn("[ProjectManager] Erreur lors de la détection de langue.");
      return null;
    }
  }

  /**
   * Convertit un code ISO 639-3 en nom de langue lisible.
   */
  private getLanguageName(code: string): string {
    const names: Record<string, string> = {
      zho: "chinois",
      cmn: "chinois mandarin",
      fra: "francais",
      eng: "anglais",
      jpn: "japonais",
      kor: "coreen",
      spa: "espagnol",
      deu: "allemand",
      ita: "italien",
      por: "portugais",
      rus: "russe",
      ara: "arabe",
      hin: "hindi",
      tha: "thaï",
      vie: "vietnamien",
      nld: "neerlandais",
      pol: "polonais",
      tur: "turc",
      swe: "suedois",
      dan: "danois",
      fin: "finnois",
      nor: "norvegien",
      ces: "tcheque",
      ell: "grec",
      hun: "hongrois",
      ron: "roumain",
      heb: "hebreu",
      ukr: "ukrainien",
      ind: "indonesien",
      may: "malais",
      tgl: "tagalog",
      ben: "bengali",
      tam: "tamoul",
      tel: "télougou",
      mar: "marathi",
      guj: "gujarati",
      pan: "pendjabi",
      urd: "ourdou",
      fas: "persan",
      lit: "lituanien",
      lav: "letton",
      est: "estonien",
      slk: "slovaque",
      slv: "slovène",
      bul: "bulgare",
      hrv: "croate",
      srp: "serbe",
      mkd: "macédonien",
      alb: "albanais",
      kat: "géorgien",
      arm: "arménien",
      eus: "basque",
      glg: "galicien",
      cat: "catalan",
      zul: "zoulou",
      afr: "afrikaans",
      swa: "swahili",
    };
    return names[code] ?? code;
  }

  /**
   * Découpe le texte en chapitres selon des patterns (SDD §5.5).
   * Si aucun pattern ne correspond, retourne le texte entier comme un seul chapitre.
   */
  splitIntoChapters(text: string, projectPath?: string): string[] {
    // Charger la config du projet si disponible
    let separatorPattern: string | undefined;
    if (projectPath) {
      try {
        const configPath = path.join(projectPath, "config.json");
        if (fs.existsSync(configPath)) {
          const config = JSON.parse(
            fs.readFileSync(configPath, "utf-8"),
          ) as Record<string, unknown>;
          const parser = config.parser as Record<string, unknown> | undefined;
          separatorPattern = parser?.chapterSeparator as string | undefined;
        }
      } catch {
        // Config illisible — utiliser les patterns par défaut
      }
    }

    // Construire les patterns à tester
    const patterns: RegExp[] = [];
    if (separatorPattern) {
      try {
        const flags = separatorPattern.includes("i") ? "im" : "m";
        const source = separatorPattern.replace(/\/[gimsuy]*/g, "").trim();
        patterns.push(new RegExp(source, flags));
      } catch {
        // Pattern invalide — ignorer
      }
    }
    patterns.push(...DEFAULT_CHAPTER_PATTERNS);

    // Tenter de découper selon les patterns
    for (const pattern of patterns) {
      const parts = text.split(pattern);
      if (parts.length > 1) {
        // Reconstruire les chapitres avec le séparateur conservé
        const result: string[] = [];
        let current = "";
        const lines = text.split("\n");
        let matchFound = false;

        for (const line of lines) {
          if (pattern.test(line)) {
            if (current.trim()) {
              result.push(current.trim());
            }
            current = line;
            matchFound = true;
          } else {
            current += (current ? "\n" : "") + line;
          }
        }
        if (current.trim()) {
          result.push(current.trim());
        }

        if (matchFound && result.length > 1) {
          return result;
        }
      }
    }

    // Aucun pattern n'a fonctionné — retourner le texte entier
    return [text];
  }
}

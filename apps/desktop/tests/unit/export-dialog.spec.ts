import { describe, it, expect, vi } from "vitest";

// Mock electron-log before any imports that trigger the logger
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    transports: { file: { level: false }, console: { level: false } },
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { ExportEngine } from "../../src/main/services/ExportEngine";
import { exportRunSchema } from "@shared/schemas/export.js";
import type { ExportInput } from "@shared/types/index.js";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

// --- Tests ExportEngine validation ---

describe("ExportEngine", () => {
  const engine = new ExportEngine();

  /** Créer un dossier temporaire */
  function tmpDir(): string {
    return path.join(os.tmpdir(), `noveltrad-test-export-${Date.now()}`);
  }

  it("doit créer le dossier parent si nécessaire", async () => {
    const baseDir = path.join(
      os.tmpdir(),
      `noveltrad-test-export-${Date.now()}`,
    );
    const dir = path.join(baseDir, "non-existant", "export");
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Test export",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Bonjour le monde",
          translatedText: "Hello world",
          status: "translated",
        },
      ],
      format: "markdown",
      outputPath: path.join(dir, "export.md"),
    };

    const outputPath = await engine.export(input);

    // Vérifier que le dossier a été créé
    expect(fs.existsSync(dir)).toBe(true);
    // Vérifier que le fichier existe
    expect(fs.existsSync(outputPath)).toBe(true);
    // Vérifier que le fichier n'est pas vide
    const stat = fs.statSync(outputPath);
    expect(stat.size).toBeGreaterThan(0);

    // Nettoyer
    try {
      fs.rmSync(baseDir, { recursive: true, force: true });
    } catch {
      // Ignorer les erreurs de nettoyage
    }
  });

  it("doit produire un fichier non vide pour le format texte", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Chapitre 1",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Premier paragraphe.",
          translatedText: "First paragraph.",
          status: "translated",
        },
        {
          id: "00000000-0000-0000-0000-000000000002",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 1,
          sourceText: "Deuxième paragraphe.",
          translatedText: "Second paragraph.",
          status: "translated",
        },
      ],
      format: "txt",
      outputPath: path.join(dir, "chapitre.txt"),
    };

    const outputPath = await engine.export(input);
    expect(fs.existsSync(outputPath)).toBe(true);
    const stat = fs.statSync(outputPath);
    expect(stat.size).toBeGreaterThan(0);

    // Vérifier le contenu
    const content = fs.readFileSync(outputPath, "utf-8");
    expect(content).toContain("First paragraph.");
    expect(content).toContain("Second paragraph.");

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("doit produire un fichier non vide pour le format HTML", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Mon chapitre",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Texte source",
          translatedText: "Texte traduit",
          status: "translated",
        },
      ],
      format: "html",
      outputPath: path.join(dir, "chapitre.html"),
    };

    const outputPath = await engine.export(input);
    expect(fs.existsSync(outputPath)).toBe(true);
    const stat = fs.statSync(outputPath);
    expect(stat.size).toBeGreaterThan(0);

    const content = fs.readFileSync(outputPath, "utf-8");
    expect(content).toContain("<!DOCTYPE html>");
    expect(content).toContain("Texte traduit");

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("doit produire un fichier non vide pour le format DOCX", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Document Word",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Paragraphe DOCX",
          translatedText: "DOCX paragraph",
          status: "translated",
        },
      ],
      format: "docx",
      outputPath: path.join(dir, "doc.docx"),
    };

    const outputPath = await engine.export(input);
    expect(fs.existsSync(outputPath)).toBe(true);
    const stat = fs.statSync(outputPath);
    expect(stat.size).toBeGreaterThan(0);

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("doit produire un fichier non vide pour le format EPUB", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Mon EPUB",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Contenu EPUB",
          translatedText: "EPUB content",
          status: "translated",
        },
      ],
      format: "epub",
      outputPath: path.join(dir, "livre.epub"),
    };

    const outputPath = await engine.export(input);
    expect(fs.existsSync(outputPath)).toBe(true);
    const stat = fs.statSync(outputPath);
    expect(stat.size).toBeGreaterThan(0);

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("doit lever une erreur si le chemin de sortie est invalide (répertoire inaccessible)", async () => {
    // Test avec un chemin invalide (sous Windows, un chemin comme NUL: est invalide)
    // Sur d'autres OS, on utilise un chemin qui causera un échec d'écriture
    let invalidPath: string;
    if (process.platform === "win32") {
      invalidPath = "NUL:";
    } else {
      invalidPath = "/root/non-existent-should-fail/export.md";
    }

    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Test échec",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Test",
          translatedText: "Test",
          status: "translated",
        },
      ],
      format: "markdown",
      outputPath: invalidPath,
    };

    // La création du dossier parent échouera ou l'écriture échouera
    await expect(engine.export(input)).rejects.toThrow();
  });

  it("doit respecter le mode bilingue", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Mode bilingue",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Source text",
          translatedText: "Target text",
          status: "translated",
        },
      ],
      format: "markdown",
      outputPath: path.join(dir, "bilingue.md"),
      options: { bilingual: true },
    };

    const outputPath = await engine.export(input);
    const content = fs.readFileSync(outputPath, "utf-8");
    expect(content).toContain("Source text");
    expect(content).toContain("Target text");

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("doit inclure le titre quand includeTitle est true", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Mon titre",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Texte",
          translatedText: "Text",
          status: "translated",
        },
      ],
      format: "markdown",
      outputPath: path.join(dir, "titre.md"),
      options: { includeTitle: true },
    };

    const outputPath = await engine.export(input);
    const content = fs.readFileSync(outputPath, "utf-8");
    expect(content).toContain("Mon titre");

    // Nettoyer
    fs.rmSync(dir, { recursive: true, force: true });
  });
});

// --- Tests schéma exportRunSchema ---

describe("exportRunSchema", () => {
  it("doit valider un payload d'export valide", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Test export",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Hello",
          translatedText: "Bonjour",
          status: "translated",
        },
      ],
      format: "markdown",
      outputPath: "/tmp/test.md",
    };

    const result = exportRunSchema.parse(payload);
    expect(result.projectId).toBe(payload.projectId);
    expect(result.paragraphs).toHaveLength(1);
  });

  it("doit rejeter un payload sans projectId", () => {
    const payload = {
      title: "Test",
      paragraphs: [],
      format: "markdown",
      outputPath: "/tmp/test.md",
    };

    expect(() => exportRunSchema.parse(payload)).toThrow();
  });

  it("doit rejeter un payload avec un format invalide", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Test",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Hello",
          status: "pending",
        },
      ],
      format: "pdf", // Format non supporté
      outputPath: "/tmp/test.pdf",
    };

    expect(() => exportRunSchema.parse(payload)).toThrow();
  });

  it("doit accepter les options facultatives", () => {
    const payload = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Test options",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "Hello",
          status: "pending",
        },
      ],
      format: "txt",
      outputPath: "/tmp/test.txt",
      options: {
        bilingual: true,
        includeTitle: false,
        includeParagraphNumbers: true,
      },
    };

    const result = exportRunSchema.parse(payload);
    expect(result.options?.bilingual).toBe(true);
    expect(result.options?.includeTitle).toBe(false);
  });
});

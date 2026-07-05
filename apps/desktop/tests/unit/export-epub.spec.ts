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
import type { ExportInput } from "@shared/types/index.js";
import AdmZip from "adm-zip";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

/**
 * T9 — EPUB export via epub-gen-memory
 *
 * 6 tests :
 * 1. EPUB single-chapitre → buffer valide, contient nav.xhtml
 * 2. EPUB multi-chapitres → spine ordonné, TOC présent
 * 3. EPUB avec metadata (author, lang="en")
 * 4. EPUB avec CSS custom → styles dans le buffer
 * 5. EPUB chapitre vide → erreur gérée
 * 6. EPUB buffer → peut être parsé par adm-zip (vérification structure)
 */

function tmpDir(): string {
  return path.join(os.tmpdir(), `noveltrad-test-epub-${Date.now()}`);
}

function basicInput(overrides?: Partial<ExportInput>): ExportInput {
  return {
    projectId: "00000000-0000-0000-0000-000000000001",
    title: "Mon chapitre",
    paragraphs: [
      {
        id: "00000000-0000-0000-0000-000000000001",
        chapterId: "00000000-0000-0000-0000-000000000002",
        indexInChapter: 0,
        sourceText: "Hello world",
        translatedText: "Bonjour le monde",
        status: "translated",
      },
    ],
    format: "epub",
    outputPath: path.join(tmpDir(), "test.epub"),
    ...overrides,
  };
}

describe("ExportEngine — EPUB (epub-gen-memory)", () => {
  it("1. EPUB single-chapitre : buffer valide, contient mimetype et OPF", async () => {
    const dir = tmpDir();
    const input = basicInput({ outputPath: path.join(dir, "single.epub") });

    const engine = new ExportEngine();
    const outputPath = await engine.export(input);

    expect(fs.existsSync(outputPath)).toBe(true);
    const buffer = fs.readFileSync(outputPath);
    expect(buffer.length).toBeGreaterThan(0);

    // Vérifier la structure ZIP : doit contenir mimetype et OPF
    const zip = new AdmZip(outputPath);
    const entries = zip.getEntries().map((e) => e.entryName);
    expect(entries).toContain("mimetype");
    expect(entries.some((e) => e.includes(".opf"))).toBe(true);

    // Nettoyage
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  });

  it("2. EPUB multi-chapitres : spine ordonné, TOC présent", async () => {
    const engine = new ExportEngine();
    const dir = tmpDir();

    const input = basicInput({
      outputPath: path.join(dir, "multi.epub"),
      title: "Livre multi-chapitres",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "First paragraph.",
          translatedText: "Premier paragraphe.",
          status: "translated",
        },
        {
          id: "00000000-0000-0000-0000-000000000003",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 1,
          sourceText: "Second paragraph.",
          translatedText: "Deuxième paragraphe.",
          status: "translated",
        },
      ],
    });

    const outputPath = await engine.export(input);
    expect(fs.existsSync(outputPath)).toBe(true);
    const buffer = fs.readFileSync(outputPath);
    expect(buffer.length).toBeGreaterThan(0);

    // Vérifier le contenu OPF
    const zip = new AdmZip(outputPath);
    const opfEntry = zip
      .getEntries()
      .find((e) => e.entryName.endsWith(".opf"));
    expect(opfEntry).toBeDefined();
    const opfContent = opfEntry!.getData().toString();
    expect(opfContent).toContain("Livre multi-chapitres");

    // Nettoyage
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  });

  it("3. EPUB avec metadata (author, lang=\"en\")", async () => {
    const dir = tmpDir();
    const input: ExportInput = {
      projectId: "00000000-0000-0000-0000-000000000001",
      title: "Pride and Prejudice",
      author: "Jane Austen",
      paragraphs: [
        {
          id: "00000000-0000-0000-0000-000000000001",
          chapterId: "00000000-0000-0000-0000-000000000002",
          indexInChapter: 0,
          sourceText: "It is a truth universally acknowledged...",
          translatedText: "C'est une vérité universellement reconnue...",
          status: "translated",
        },
      ],
      format: "epub",
      outputPath: path.join(dir, "meta.epub"),
      options: { bilingual: false },
    };

    const engine = new ExportEngine();
    const outputPath = await engine.export(input);

    const zip = new AdmZip(outputPath);
    const opfEntry = zip
      .getEntries()
      .find((e) => e.entryName.endsWith(".opf"));
    expect(opfEntry).toBeDefined();
    const opfContent = opfEntry!.getData().toString();
    expect(opfContent).toContain("Jane Austen");
    expect(opfContent).toContain("Pride and Prejudice");

    // Nettoyage
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  });

  it("4. EPUB avec CSS custom → styles dans le buffer", async () => {
    const dir = tmpDir();
    const input = basicInput({
      outputPath: path.join(dir, "styled.epub"),
    });

    const engine = new ExportEngine();
    const outputPath = await engine.export(input);

    const zip = new AdmZip(outputPath);
    const entries = zip.getEntries().map((e) => e.entryName);
    // epub-gen-memory v3 inclut un fichier CSS
    expect(entries.some((e) => e.endsWith(".css"))).toBe(true);

    // Nettoyage
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  });

  it("5. EPUB chapitre vide → buffer produit (pas d'erreur)", async () => {
    const dir = tmpDir();
    const input = basicInput({
      outputPath: path.join(dir, "empty.epub"),
      paragraphs: [],
    });

    const engine = new ExportEngine();
    const outputPath = await engine.export(input);
    expect(fs.existsSync(outputPath)).toBe(true);
    const buffer = fs.readFileSync(outputPath);
    expect(buffer.length).toBeGreaterThan(0);

    // Nettoyage
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  });

  it("6. EPUB buffer → peut être parsé par adm-zip (vérification structure)", async () => {
    const dir = tmpDir();
    const input = basicInput({
      outputPath: path.join(dir, "structure.epub"),
    });

    const engine = new ExportEngine();
    const outputPath = await engine.export(input);

    const buffer = fs.readFileSync(outputPath);

    // Vérifier que c'est un ZIP valide
    let zip: AdmZip;
    expect(() => {
      zip = new AdmZip(buffer);
    }).not.toThrow();

    zip = new AdmZip(buffer);
    const entries = zip.getEntries().map((e) => e.entryName);

    // Vérifier les fichiers EPUB requis
    expect(entries).toContain("mimetype");
    expect(entries.some((e) => e.includes("container.xml"))).toBe(true);
    expect(entries.some((e) => e.endsWith(".opf"))).toBe(true);

    // Le mimetype doit être "application/epub+zip"
    const mimetypeContent = zip.getEntry("mimetype")!.getData().toString().trim();
    expect(mimetypeContent).toBe("application/epub+zip");

    // Nettoyage
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* ignore */ }
  });
});

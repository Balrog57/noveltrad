import path from "node:path";
import fs from "node:fs";
import { randomUUID } from "node:crypto";
import { execFile } from "node:child_process";
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
} from "docx";
import AdmZip from "adm-zip";
import epub from "epub-gen-memory";
import type {
  ExportInput,
  ExportFormat,
  Paragraph as NtParagraph,
} from "@shared/types/index.js";

/** Renderer personnalisé enregistré par un plugin */
export type CustomRenderer = (input: ExportInput) => string | Buffer | Promise<string | Buffer>;
import type { ProjectDatabase } from "../db/connection.js";
import { assertWithinProject } from "../utils/paths.js";
import { logger } from "../utils/logger.js";

/** SDD §13.6 : entrée d'un chapitre pour l'export par lots */
export interface BatchChapterInput {
  chapterId: string;
  title: string;
  paragraphs: NtParagraph[];
}

/** SDD §13.6 : résultat d'export par lots */
export interface BatchExportResult {
  /** Chemins des fichiers générés (un pour EPUB agrégé, un par chapitre sinon) */
  paths: string[];
  /** Format utilisé */
  format: ExportFormat;
}

export class ExportEngine {
  private db?: ProjectDatabase;

  /**
   * Renderers personnalisés enregistrés par des plugins (SDD §15).
   * Map<format, renderer>. Vérifié avant le switch built-in dans render().
   */
  private customRenderers: Map<string, CustomRenderer> = new Map();

  /** Enregistre un renderer pour un format d'export (utilisé par PluginHost) */
  registerRenderer(format: string, renderer: CustomRenderer): void {
    this.customRenderers.set(format, renderer);
  }

  /** Désenregistre un renderer pour un format (utilisé à la désactivation d'un plugin) */
  unregisterRenderer(format: string): void {
    this.customRenderers.delete(format);
  }

  /** Définit la base de données projet pour le traçage des exports (SDD §6.2) */
  setDatabase(db: ProjectDatabase): void {
    this.db = db;
  }
  async export(input: ExportInput): Promise<string> {
    // Bug fix : si outputPath est un dossier (le workflow passe
    // path.join(project.path, "exports")), on construit le nom de fichier
    // via defaultOutputPath au lieu d'essayer d'écrire directement dans le
    // dossier (EISDIR). Si outputPath est déjà un fichier, on l'utilise tel quel.
    let outputPath: string;
    if (input.outputPath && fs.statSync(input.outputPath, { throwIfNoEntry: false })?.isDirectory()) {
      // C'est un dossier → construire le nom de fichier
      outputPath = this.defaultOutputPath(input);
    } else if (input.outputPath) {
      // C'est déjà un fichier → utiliser tel quel
      outputPath = input.outputPath;
    } else {
      // Pas de outputPath → default
      outputPath = this.defaultOutputPath(input);
    }

    // SDD §21.3 — Protection contre le path traversal
    const basePath = input.outputPath
      ? path.dirname(path.resolve(input.outputPath))
      : path.resolve(".");
    assertWithinProject(basePath, outputPath);

    // Créer le dossier parent si nécessaire
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });

    const content = await this.render(input);
    fs.writeFileSync(outputPath, content);

    // Validation : le fichier doit exister, ne pas être vide, taille > 0
    if (!fs.existsSync(outputPath)) {
      throw new Error(
        `Échec de validation de l'export : le fichier "${outputPath}" est introuvable après l'écriture.`,
      );
    }
    const stat = fs.statSync(outputPath);
    if (stat.size === 0) {
      throw new Error(
        `Échec de validation de l'export : le fichier "${outputPath}" est vide.`,
      );
    }

    // Validation EPUB structurelle (SDD §13.8)
    if (input.format === "epub") {
      this.validateEpub(outputPath);
    }

    // SDD §6.2 : traçage des exports dans la table `exports`
    if (this.db) {
      const stmt = this.db.prepare(
        `INSERT INTO exports (id, project_id, chapter_id, format, output_path, file_size, bilingual, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      );
      stmt.run([
        randomUUID(),
        input.projectId,
        input.chapterId ?? null,
        input.format,
        outputPath,
        stat.size,
        input.options?.bilingual ? 1 : 0,
        new Date().toISOString(),
      ]);
    }

    return outputPath;
  }

  /**
   * SDD §13.6 : Export par lots de plusieurs chapitres.
   * - EPUB : génère un seul fichier agrégé multi-chapitres.
   * - Autres formats : génère un fichier par chapitre.
   * @param projectId ID du projet
   * @param projectTitle Titre du projet (utilisé pour le fichier EPUB agrégé)
   * @param author Auteur du projet (optionnel)
   * @param chapters Liste des chapitres à exporter
   * @param format Format d'export
   * @param outputDir Dossier de sortie
   * @param options Options d'export (bilingue, titre, numérotation)
   * @returns Résultat avec les chemins des fichiers générés
   */
  async exportBatch(
    projectId: string,
    projectTitle: string,
    author: string | undefined,
    chapters: BatchChapterInput[],
    format: ExportFormat,
    outputDir: string,
    options?: {
      includeTitle?: boolean;
      includeParagraphNumbers?: boolean;
      bilingual?: boolean;
      targetLanguage?: string;
    },
  ): Promise<BatchExportResult> {
    if (chapters.length === 0) {
      throw new Error("Aucun chapitre à exporter.");
    }

    // Créer le dossier de sortie si nécessaire
    fs.mkdirSync(outputDir, { recursive: true });

    const paths: string[] = [];

    if (format === "epub") {
      // SDD §13.6 : EPUB agrégé multi-chapitres
      const allParagraphs: NtParagraph[] = [];
      for (const ch of chapters) {
        for (const p of ch.paragraphs) {
          allParagraphs.push({
            ...p,
            // Préfixer le texte avec le titre du chapitre pour séparer visuellement
            sourceText: p.sourceText,
            translatedText: p.translatedText,
          });
        }
      }

      const safeName = projectTitle.replace(/[^a-z0-9]/gi, "_");
      const outputPath = path.join(outputDir, `${safeName}.epub`);

      // Pour l'EPUB multi-chapitres, on génère un EPUB avec un chapitre par chapitre
      const buffer = await this.toEpubMultiChapter(
        projectTitle,
        author ?? projectTitle,
        chapters,
        options,
      );
      fs.writeFileSync(outputPath, buffer);

      // Validation
      if (!fs.existsSync(outputPath)) {
        throw new Error(
          `Échec de validation de l'export batch : le fichier "${outputPath}" est introuvable.`,
        );
      }
      const stat = fs.statSync(outputPath);
      if (stat.size === 0) {
        throw new Error(
          `Échec de validation de l'export batch : le fichier "${outputPath}" est vide.`,
        );
      }

      this.validateEpub(outputPath);
      paths.push(outputPath);
    } else {
      // SDD §13.6 : un fichier par chapitre pour les autres formats
      for (const ch of chapters) {
        const safeName = (ch.title || ch.chapterId).replace(/[^a-z0-9]/gi, "_");
        const ext = this.extensionFor(format);
        const outputPath = path.join(outputDir, `${safeName}.${ext}`);

        const input: ExportInput = {
          projectId,
          chapterId: ch.chapterId,
          title: ch.title,
          author,
          paragraphs: ch.paragraphs,
          format,
          outputPath,
          options,
        };

        const resultPath = await this.export(input);
        paths.push(resultPath);
      }
    }

    return { paths, format };
  }

  /** Retourne l'extension de fichier pour un format donné */
  private extensionFor(format: ExportFormat): string {
    switch (format) {
      case "markdown":
        return "md";
      case "txt":
        return "txt";
      case "html":
        return "html";
      case "docx":
        return "docx";
      case "epub":
        return "epub";
    }
  }

  /**
   * SDD §13.6 : génère un EPUB multi-chapitres agrégé.
   * Chaque chapitre devient un item dans le manifest + spine.
   */
  private async toEpubMultiChapter(
    title: string,
    author: string,
    chapters: BatchChapterInput[],
    options?: {
      includeTitle?: boolean;
      includeParagraphNumbers?: boolean;
      bilingual?: boolean;
      targetLanguage?: string;
    },
  ): Promise<Buffer> {
    const css = `body { font-family: Georgia, serif; line-height: 1.6; max-width: 700px; margin: 2em auto; }
h1, h2 { text-align: center; }
p { margin: 1em 0; text-align: justify; }
[lang="source"] { color: #64748b; font-style: italic; }`;

    const content = chapters.map((ch, _index) => {
      const chapterTitle = ch.title || `Chapitre ${_index + 1}`;
      const paragraphsHtml = ch.paragraphs
        .map((p) => {
          const prefix = options?.includeParagraphNumbers
            ? `${p.indexInChapter + 1}. `
            : "";
          const text = options?.bilingual
            ? `<p lang="source">${this.escapeHtml(p.sourceText)}</p><p>${this.escapeHtml(prefix + (p.translatedText ?? ""))}</p>`
            : `<p>${this.escapeHtml(prefix + (p.translatedText ?? ""))}</p>`;
          return text;
        })
        .join("\n");

      return {
        title: chapterTitle,
        content: `<h2>${this.escapeHtml(chapterTitle)}</h2>\n${paragraphsHtml}`,
      };
    });

    // T9 fix : la langue de l'EPUB provient de la targetLanguage du projet
    // (propagée via options), avec fallback "fr" — cohérent avec toEpub() single.
    const epubOptions = {
      title,
      author: author || "NovelTrad",
      lang: options?.targetLanguage ?? "fr",
      css,
      version: 3 as const,
    };

    return await epub(epubOptions, content);
  }

  private defaultOutputPath(input: ExportInput): string {
    const baseDir = input.outputPath || process.cwd();
    const safeName = input.title.replace(/[^a-z0-9]/gi, "_");
    const base = path.join(baseDir, safeName);
    switch (input.format) {
      case "markdown":
        return `${base}.md`;
      case "txt":
        return `${base}.txt`;
      case "html":
        return `${base}.html`;
      case "docx":
        return `${base}.docx`;
      case "epub":
        return `${base}.epub`;
      default:
        return `${base}.md`;
    }
  }

  /**
   * Valide la structure d'un fichier EPUB (SDD §13.8).
   * Vérifie : ZIP valide, mimetype premier fichier non compressé,
   * container.xml présent, OPF existant avec metadata minimales.
   * Log des avertissements pour les problèmes non-critiques, lève une erreur pour les critiques.
   */
  private validateEpub(outputPath: string): void {
    const warnings: string[] = [];

    // 1. Ouvrir le ZIP
    let zip: AdmZip;
    try {
      zip = new AdmZip(outputPath);
    } catch {
      throw new Error(
        "Validation EPUB échouée : le fichier n'est pas un ZIP valide.",
      );
    }

    const entries = zip.getEntries();
    const entryNames = entries.map((e) => e.entryName);

    // 2. Vérifier mimetype : doit exister, être le premier, et avoir le bon contenu
    if (!entryNames.includes("mimetype")) {
      throw new Error("Validation EPUB échouée : fichier 'mimetype' manquant.");
    }
    if (entryNames[0] !== "mimetype") {
      warnings.push(
        "Le fichier 'mimetype' n'est pas la première entrée du ZIP (recommandation EPUB).",
      );
    }
    const mimetypeEntry = zip.getEntry("mimetype");
    if (mimetypeEntry) {
      const mimetypeContent = mimetypeEntry.getData().toString().trim();
      if (mimetypeContent !== "application/epub+zip") {
        warnings.push(
          `Contenu du mimetype inattendu : "${mimetypeContent}" au lieu de "application/epub+zip".`,
        );
      }
      // Vérifier que mimetype n'est pas compressé (spec EPUB exige STORED)
      if (mimetypeEntry.header.method !== 0) {
        warnings.push(
          "Le fichier 'mimetype' est compressé — la spécification EPUB exige qu'il soit stocké sans compression.",
        );
        // Correction automatique : définir la compression sur STORED
        mimetypeEntry.header.method = 0;
      }
    }

    // 3. Vérifier META-INF/container.xml
    if (!entryNames.includes("META-INF/container.xml")) {
      throw new Error(
        "Validation EPUB échouée : 'META-INF/container.xml' manquant.",
      );
    }

    // 4. Vérifier qu'au moins un fichier OPF référencé existe
    const containerContent = zip
      .getEntry("META-INF/container.xml")!
      .getData()
      .toString();
    const opfMatch = /full-path="([^"]+\.opf)"/i.exec(containerContent);
    if (!opfMatch) {
      throw new Error(
        "Validation EPUB échouée : aucun fichier OPF référencé dans container.xml.",
      );
    }
    const opfPath = opfMatch[1];
    if (!entryNames.includes(opfPath)) {
      throw new Error(
        `Validation EPUB échouée : le fichier OPF "${opfPath}" référencé dans container.xml est introuvable.`,
      );
    }

    // 5. Vérifier les métadonnées OPF minimales (title, language)
    const opfContent = zip.getEntry(opfPath)!.getData().toString();
    if (!/<dc:title[>\s]/i.test(opfContent)) {
      warnings.push(
        "Métadonnées OPF : <dc:title> manquant (recommandé pour la compatibilité).",
      );
    }
    if (!/<dc:language[>\s]/i.test(opfContent)) {
      warnings.push(
        "Métadonnées OPF : <dc:language> manquant (recommandé pour la compatibilité).",
      );
    }

    // Logger les avertissements non-critiques
    for (const w of warnings) {
      logger.warn(`[ExportEngine] EPUB validation: ${w}`);
    }

    // SDD §13.8 : validation externe optionnelle via epubcheck (Java)
    this.validateEpubWithEpubcheck(outputPath).catch((err) => {
      logger.warn(`[ExportEngine] epubcheck: ${err.message}`);
    });
  }

  /**
   * Validation externe optionnelle via epubcheck.
   * Délègue à la fonction autonome `runEpubcheck`.
   * Non-bloquante : les erreurs sont simplement loguées.
   */
  private async validateEpubWithEpubcheck(filePath: string): Promise<void> {
    const result = await runEpubcheck(filePath);
    if (!result.success && !result.skipped) {
      throw new Error(`Validation epubcheck échouée: ${result.message}`);
    }
  }

  private async render(input: ExportInput): Promise<Buffer | string> {
    // SDD §15 : vérifier d'abord les renderers personnalisés (plugins)
    const customRenderer = this.customRenderers.get(input.format);
    if (customRenderer) {
      return customRenderer(input);
    }

    // Renderers built-in
    switch (input.format) {
      case "markdown":
        return this.toMarkdown(input);
      case "txt":
        return this.toTxt(input);
      case "html":
        return this.toHtml(input);
      case "docx":
        return this.toDocx(input);
      case "epub":
        return this.toEpub(input);
      default:
        return this.toMarkdown(input);
    }
  }

  /** Préfixe un paragraphe avec son numéro si l'option includeParagraphNumbers est activée */
  private pn(input: ExportInput, indexInChapter: number): string {
    return input.options?.includeParagraphNumbers
      ? `${indexInChapter + 1}. `
      : "";
  }

  private toMarkdown(input: ExportInput): string {
    const lines: string[] = [];
    if (input.options?.includeTitle !== false && input.title) {
      lines.push(`# ${input.title}`, "");
    }
    for (const p of input.paragraphs) {
      const prefix = this.pn(input, p.indexInChapter);
      const text = input.options?.bilingual
        ? `**${p.sourceText}**\n\n${prefix}${p.translatedText ?? ""}`
        : `${prefix}${p.translatedText ?? ""}`;
      lines.push(text, "");
    }
    return lines.join("\n").trim();
  }

  private toTxt(input: ExportInput): string {
    const parts: string[] = [];
    if (input.title) {parts.push(input.title, "");}
    for (const p of input.paragraphs) {
      const prefix = this.pn(input, p.indexInChapter);
      const text = input.options?.bilingual
        ? `${p.sourceText}\n${prefix}${p.translatedText ?? ""}`
        : `${prefix}${p.translatedText ?? ""}`;
      parts.push(text);
    }
    return parts.join("\n\n").trim();
  }

  private toHtml(input: ExportInput): string {
    const paragraphs = input.paragraphs
      .map((p) => {
        const prefix = this.pn(input, p.indexInChapter);
        const text = input.options?.bilingual
          ? `<p lang="source">${this.escapeHtml(p.sourceText)}</p><p>${this.escapeHtml(prefix + (p.translatedText ?? ""))}</p>`
          : `<p>${this.escapeHtml(prefix + (p.translatedText ?? ""))}</p>`;
        return text;
      })
      .join("\n");

    const authorMeta = input.author
      ? `\n  <meta name="author" content="${this.escapeHtml(input.author)}">`
      : "";

    return `<!DOCTYPE html>
<html lang="${this.targetLang(input)}">
<head>
  <meta charset="UTF-8">
  <title>${this.escapeHtml(input.title)}</title>${authorMeta}
  <style>
    body { font-family: Georgia, serif; line-height: 1.6; max-width: 700px; margin: 2em auto; }
    h1 { text-align: center; }
    p { margin: 1em 0; text-align: justify; }
    [lang="source"] { color: #64748b; font-style: italic; }
  </style>
</head>
<body>
  <h1>${this.escapeHtml(input.title)}</h1>
  ${paragraphs}
</body>
</html>`;
  }

  private async toDocx(input: ExportInput): Promise<Buffer> {
    const children: Paragraph[] = [];
    if (input.title) {
      children.push(
        new Paragraph({
          text: input.title,
          heading: HeadingLevel.TITLE,
          alignment: AlignmentType.CENTER,
        }),
      );
    }

    for (const p of input.paragraphs) {
      const prefix = this.pn(input, p.indexInChapter);
      const text = input.options?.bilingual
        ? `${p.sourceText}\n${prefix}${p.translatedText ?? ""}`
        : `${prefix}${p.translatedText ?? ""}`;
      children.push(
        new Paragraph({
          children: [new TextRun(text)],
          spacing: { after: 200 },
        }),
      );
    }

    const doc = new Document({ sections: [{ children }] });
    return Packer.toBuffer(doc);
  }

  private async toEpub(input: ExportInput): Promise<Buffer> {
    const css = `body { font-family: Georgia, serif; line-height: 1.6; max-width: 700px; margin: 2em auto; }
h1 { text-align: center; }
p { margin: 1em 0; text-align: justify; }
[lang="source"] { color: #64748b; font-style: italic; }`;

    const contentHtml = this.toHtml(input);
    // Strip the outer HTML wrapper since epub-gen-memory provides its own
    const bodyMatch = /<body>\s*([\s\S]*?)\s*<\/body>/i.exec(contentHtml);
    const bodyContent = bodyMatch ? bodyMatch[1] : contentHtml;

    const epubOptions = {
      title: input.title,
      author: input.author || "NovelTrad",
      lang: this.targetLang(input),
      css,
      version: 3 as const,
    };

    const content = [
      {
        title: input.title,
        content: bodyContent,
      },
    ];

    return await epub(epubOptions, content);
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  private escapeXml(text: string): string {
    return this.escapeHtml(text).replace(/'/g, "&apos;");
  }

  private targetLang(input: ExportInput): string {
    return (
      (input.options as { targetLanguage?: string })?.targetLanguage ?? "fr"
    );
  }
}

// ── Fonctions autonomes (exportées pour testabilité, SDD §13.8) ─────────────

export interface RunEpubcheckResult {
  success: boolean;
  skipped?: boolean;
  message?: string;
}

/**
 * Exécute epubcheck.jar sur un fichier EPUB en sous-processus (SDD §13.8).
 * Si epubcheck.jar est introuvable, log un avertissement et ne bloque pas.
 * @param filePath Chemin absolu du fichier EPUB à valider
 * @returns Résultat de la validation
 */
export async function runEpubcheck(
  filePath: string,
): Promise<RunEpubcheckResult> {
  const epubcheckPath = findEpubcheckJar();
  if (!epubcheckPath) {
    logger.warn(
      "[ExportEngine] epubcheck.jar introuvable — validation externe ignorée. Définissez EPUBCHECK_PATH ou placez epubcheck.jar dans l'application.",
    );
    return { success: true, skipped: true };
  }

  try {
    await new Promise<void>((resolve, reject) => {
      execFile(
        "java",
        ["-jar", epubcheckPath, filePath],
        { timeout: 30000 },
        (error, stdout, stderr) => {
          if (error) {
            const message = stderr || stdout || error.message;
            reject(new Error(`Validation epubcheck échouée: ${message}`));
          } else {
            resolve();
          }
        },
      );
    });
    logger.info("[ExportEngine] epubcheck : validation réussie");
    return { success: true };
  } catch (err) {
    return {
      success: false,
      message: err instanceof Error ? err.message : "Erreur inconnue",
    };
  }
}

/** Cherche epubcheck.jar dans des chemins courants */
function findEpubcheckJar(): string | null {
  const candidates = [
    // Variable d'environnement
    ...(process.env.EPUBCHECK_PATH ? [process.env.EPUBCHECK_PATH] : []),
    // Dans le dossier resources de l'application
    path.join(process.resourcesPath || "", "epubcheck", "epubcheck.jar"),
    // Dans le dossier courant
    path.join(process.cwd(), "epubcheck", "epubcheck.jar"),
    // Dans les dossiers parent
    path.join(process.cwd(), "..", "epubcheck", "epubcheck.jar"),
    // Dans le dossier de l'utilisateur
    path.join(
      process.env.USERPROFILE || process.env.HOME || "",
      "epubcheck",
      "epubcheck.jar",
    ),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

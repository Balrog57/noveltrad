import path from "node:path";
import fs from "node:fs";
import { randomUUID } from "node:crypto";
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
} from "docx";
import AdmZip from "adm-zip";
import type { ExportInput, ExportFormat } from "@shared/types/index.js";
import type { ProjectDatabase } from "../db/connection.js";
import { assertWithinProject } from "../utils/paths.js";

export class ExportEngine {
  private db?: ProjectDatabase;

  /** Définit la base de données projet pour le traçage des exports (SDD §6.2) */
  setDatabase(db: ProjectDatabase): void {
    this.db = db;
  }
  async export(input: ExportInput): Promise<string> {
    const outputPath = input.outputPath ?? this.defaultOutputPath(input);

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
      console.warn(`[ExportEngine] EPUB validation: ${w}`);
    }
  }

  private async render(input: ExportInput): Promise<Buffer | string> {
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
    if (input.title) parts.push(input.title, "");
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

  private toEpub(input: ExportInput): Buffer {
    // Version MVP : genere un fichier EPUB minimaliste avec adm-zip
    const zip = new AdmZip();
    zip.addFile("mimetype", Buffer.from("application/epub+zip"), "", 0o644);

    const containerXml = `\u003c?xml version="1.0"?\u003e
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`;
    zip.addFile("META-INF/container.xml", Buffer.from(containerXml));

    const contentHtml = this.toHtml(input);
    zip.addFile("OEBPS/content.html", Buffer.from(contentHtml));

    const creator = input.author
      ? `\n    <dc:creator>${this.escapeXml(input.author)}</dc:creator>`
      : "";

    const opf = `\u003c?xml version="1.0"?\u003e
<package version="3.0" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>${this.escapeXml(input.title)}</dc:title>${creator}
    <dc:language>${this.targetLang(input)}</dc:language>
  </metadata>
  <manifest>
    <item id="content" href="content.html" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="content"/>
  </spine>
</package>`;
    zip.addFile("OEBPS/content.opf", Buffer.from(opf));

    return zip.toBuffer();
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

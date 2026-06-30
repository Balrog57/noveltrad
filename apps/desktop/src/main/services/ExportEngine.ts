import path from 'node:path'
import fs from 'node:fs'
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx'
import AdmZip from 'adm-zip'
import type { ExportInput, ExportFormat } from '@shared/types/index.js'

export class ExportEngine {
  async export(input: ExportInput): Promise<string> {
    const outputPath = input.outputPath ?? this.defaultOutputPath(input)
    const content = await this.render(input)
    fs.writeFileSync(outputPath, content)
    return outputPath
  }

  private defaultOutputPath(input: ExportInput): string {
    const base = path.join(input.outputPath ?? '', input.title.replace(/[^a-z0-9]/gi, '_'))
    switch (input.format) {
      case 'markdown': return `${base}.md`
      case 'txt': return `${base}.txt`
      case 'html': return `${base}.html`
      case 'docx': return `${base}.docx`
      case 'epub': return `${base}.epub`
      default: return `${base}.md`
    }
  }

  private async render(input: ExportInput): Promise<Buffer | string> {
    switch (input.format) {
      case 'markdown': return this.toMarkdown(input)
      case 'txt': return this.toTxt(input)
      case 'html': return this.toHtml(input)
      case 'docx': return this.toDocx(input)
      case 'epub': return this.toEpub(input)
      default: return this.toMarkdown(input)
    }
  }

  private toMarkdown(input: ExportInput): string {
    const lines: string[] = []
    if (input.options?.includeTitle !== false && input.title) {
      lines.push(`# ${input.title}`, '')
    }
    for (const p of input.paragraphs) {
      const text = input.options?.bilingual
        ? `${p.sourceText}\n\n${p.translatedText ?? ''}`
        : (p.translatedText ?? '')
      lines.push(text, '')
    }
    return lines.join('\n').trim()
  }

  private toTxt(input: ExportInput): string {
    const parts: string[] = []
    if (input.title) parts.push(input.title, '')
    for (const p of input.paragraphs) {
      const text = input.options?.bilingual
        ? `${p.sourceText}\n${p.translatedText ?? ''}`
        : (p.translatedText ?? '')
      parts.push(text)
    }
    return parts.join('\n\n').trim()
  }

  private toHtml(input: ExportInput): string {
    const paragraphs = input.paragraphs
      .map((p) => {
        const text = input.options?.bilingual
          ? `<p lang="source">${this.escapeHtml(p.sourceText)}</p><p>${this.escapeHtml(p.translatedText ?? '')}</p>`
          : `<p>${this.escapeHtml(p.translatedText ?? '')}</p>`
        return text
      })
      .join('\n')

    return `<!DOCTYPE html>
<html lang="${this.targetLang(input)}">
<head>
  <meta charset="UTF-8">
  <title>${this.escapeHtml(input.title)}</title>
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
</html>`
  }

  private async toDocx(input: ExportInput): Promise<Buffer> {
    const children: Paragraph[] = []
    if (input.title) {
      children.push(
        new Paragraph({
          text: input.title,
          heading: HeadingLevel.TITLE,
          alignment: AlignmentType.CENTER
        })
      )
    }

    for (const p of input.paragraphs) {
      const text = input.options?.bilingual
        ? `${p.sourceText}\n${p.translatedText ?? ''}`
        : (p.translatedText ?? '')
      children.push(
        new Paragraph({
          children: [new TextRun(text)],
          spacing: { after: 200 }
        })
      )
    }

    const doc = new Document({ sections: [{ children }] })
    return Packer.toBuffer(doc)
  }

  private toEpub(input: ExportInput): Buffer {
    // Version MVP : genere un fichier EPUB minimaliste avec adm-zip
    const zip = new AdmZip()
    zip.addFile('mimetype', Buffer.from('application/epub+zip'), '', 0o644)

    const containerXml = `\u003c?xml version="1.0"?\u003e
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`
    zip.addFile('META-INF/container.xml', Buffer.from(containerXml))

    const contentHtml = this.toHtml(input)
    zip.addFile('OEBPS/content.html', Buffer.from(contentHtml))

    const opf = `\u003c?xml version="1.0"?\u003e
<package version="3.0" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>${this.escapeXml(input.title)}</dc:title>
    <dc:language>${this.targetLang(input)}</dc:language>
  </metadata>
  <manifest>
    <item id="content" href="content.html" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="content"/>
  </spine>
</package>`
    zip.addFile('OEBPS/content.opf', Buffer.from(opf))

    return zip.toBuffer()
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  private escapeXml(text: string): string {
    return this.escapeHtml(text).replace(/'/g, '&apos;')
  }

  private targetLang(input: ExportInput): string {
    return (input.options as { targetLanguage?: string })?.targetLanguage ?? 'fr'
  }
}





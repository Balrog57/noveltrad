# Volume 13 — Export

## 13.1 Formats supportés

| Format | v1.0 | Priorité | Librairie |
|--------|------|----------|-----------|
| Markdown | ✓ | Must | Natif |
| TXT | ✓ | Must | Natif |
| DOCX | ✓ | Must | `docx` (dolanmiu/docx) |
| EPUB | ✓ | Should | `epub-gen-memory` |
| HTML | ✓ | Could | Natif |

---

## 13.2 Pipeline d’export

```text
Paragraphes traduits + métadonnées
    ↓
Assemblage (titre, séparateurs, styles)
    ↓
Conversion selon le format cible
    ↓
Écriture dans exports/
    ↓
Validation (taille, ouverture, epubcheck pour EPUB)
    ↓
Entrée dans table exports
    ↓
Notification UI
```

### Données d’entrée

```typescript
interface ExportInput {
  chapterId?: string
  projectId: string
  title: string
  author?: string
  paragraphs: Paragraph[]
  format: ExportFormat
  outputPath?: string
  options?: ExportOptions
}

interface ExportOptions {
  includeTitle?: boolean
  includeParagraphNumbers?: boolean
  lineSpacing?: 'single' | '1.5' | 'double'
  pageSize?: 'A4' | 'letter'
  margins?: { top: number; bottom: number; left: number; right: number }
}
```

---

## 13.3 Implémentation par format

### Markdown

```typescript
function toMarkdown(input: ExportInput): string {
  const lines: string[] = []
  if (input.options?.includeTitle !== false && input.title) {
    lines.push(`# ${input.title}`, '')
  }
  for (const p of input.paragraphs) {
    lines.push(p.translatedText ?? '', '')
  }
  return lines.join('\n').trim()
}
```

### TXT

```typescript
function toTxt(input: ExportInput): string {
  const parts: string[] = []
  if (input.title) parts.push(input.title, '')
  parts.push(...input.paragraphs.map(p => p.translatedText ?? ''))
  return parts.join('\n').trim()
}
```

### HTML

```typescript
function toHtml(input: ExportInput): string {
  const paragraphs = input.paragraphs
    .map(p => `<p>${escapeHtml(p.translatedText ?? '')}</p>`)
    .join('\n')

  return `<!DOCTYPE html>
<html lang="${input.project.targetLanguage}">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(input.title)}</title>
  <style>
    body { font-family: Georgia, serif; line-height: 1.6; max-width: 700px; margin: 2em auto; }
    h1 { text-align: center; }
    p { margin: 1em 0; text-align: justify; }
  </style>
</head>
<body>
  <h1>${escapeHtml(input.title)}</h1>
  ${paragraphs}
</body>
</html>`
}
```

### DOCX via `docx`

```typescript
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx'
import { writeFile } from 'node:fs/promises'

async function toDocx(input: ExportInput): Promise<Buffer> {
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
    children.push(
      new Paragraph({
        children: [new TextRun(p.translatedText ?? '')],
        spacing: { after: 200 }
      })
    )
  }

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 1440,
              right: 1440,
              bottom: 1440,
              left: 1440
            }
          }
        },
        children
      }
    ]
  })

  return Packer.toBuffer(doc)
}
```

**Référence** (Context7: `/dolanmiu/docx`) : `Document`, `Paragraph`, `TextRun`, `HeadingLevel`, `Packer.toBuffer` pour générer un fichier DOCX binaire. Les marges sont en twips (1440 twips = 1 pouce).

### EPUB via `epub-gen-memory`

```typescript
import epub from 'epub-gen-memory'
import { writeFile } from 'node:fs/promises'

async function toEpub(input: ExportInput): Promise<Buffer> {
  const htmlParagraphs = input.paragraphs
    .map(p => `<p>${escapeHtml(p.translatedText ?? '')}</p>`)
    .join('\n')

  const content = `<h2>${escapeHtml(input.title)}</h2>\n${htmlParagraphs}`

  const buffer = await epub(
    {
      title: input.title,
      author: input.author ?? 'Unknown',
      publisher: 'NovelTrad 2.0',
      version: 3
    },
    [
      {
        title: input.title,
        content
      }
    ]
  )

  return buffer
}
```

**Référence** (Context7: `/cpiber/epub-gen-memory`) : `epub(metadata, chapters)` retourne un `Buffer`. À valider au moment de l'implémentation ; si le package n'est pas assez maintenu, privilégier `epub-gen` ou une génération manuelle avec `archiver` + `jsdom`. Les chapitres sont des objets `{ title, content }` où `content` est du HTML.

---

## 13.4 Métadonnées incluses

Selon le format, les métadonnées suivantes sont injectées :

| Métadonnée | Markdown | TXT | HTML | DOCX | EPUB |
|------------|----------|-----|------|------|------|
| Titre | `#` | première ligne | `<title>`, `<h1>` | titre | titre |
| Auteur | frontmatter optionnel | première ligne optionnel | meta | propriété | auteur |
| Langue | — | — | `lang` | propriété | langue |
| Date export | — | — | — | — | date |
| Générateur | — | — | commentaire | — | NovelTrad 2.0 |

---

## 13.5 ExportEngine

```typescript
class ExportEngine {
  constructor(private projectPath: string) {}

  async export(input: ExportInput): Promise<ExportResult> {
    const outputPath = input.outputPath ?? this.defaultOutputPath(input)
    const content = await this.generate(input)
    await writeFile(outputPath, content)
    await this.validate(input.format, outputPath)
    return { outputPath, format: input.format, size: (await stat(outputPath)).size }
  }

  private async generate(input: ExportInput): Promise<Buffer | string> {
    switch (input.format) {
      case 'markdown': return toMarkdown(input)
      case 'txt': return toTxt(input)
      case 'html': return toHtml(input)
      case 'docx': return toDocx(input)
      case 'epub': return toEpub(input)
      default: throw new Error(`Unsupported format: ${input.format}`)
    }
  }

  private async validate(format: ExportFormat, path: string): Promise<void> {
    if (format === 'epub') {
      const zipError = validateEpubZip(path)
      if (zipError) throw new Error(`EPUB invalid: ${zipError}`)

      const epubcheck = await runEpubcheck(path)
      if (!epubcheck.valid) {
        // Si epubcheck est installé, bloquer ; sinon avertir
        throw new Error(`EPUB epubcheck errors: ${epubcheck.errors.join('; ')}`)
      }
    }
  }

  private defaultOutputPath(input: ExportInput): string {
    const safeTitle = sanitizeFilename(input.title)
    const ext = input.format === 'markdown' ? 'md' : input.format
    return join(this.projectPath, 'exports', `${safeTitle}.${ext}`)
  }
}
```

---

## 13.5b Mode bilingue

Inspiré d’[epub-translator](https://github.com/oomol-lab/epub-translator), de [bbook-maker](https://pypi.org/project/bbook-maker/) et de [PolyglotShelf](https://gitlab.com/sansors/polyglotshelf).

Option d’export où chaque paragraphe source est suivi de sa traduction :

```text
Paragraph 1 source
→ Paragraph 1 traduction

Paragraph 2 source
→ Paragraph 2 traduction
```

### Formats supportés

- **EPUB** : alternance de paragraphes ou colonnes (selon le reader).
- **HTML** : balisage sémantique `lang` par bloc.
- **Markdown / TXT** : préfixe `>` ou séparateur configurable.

### UI

- Option "Mode bilingue" dans la boîte d’export.
- Prévisualisation côte à côte avant validation.

## 13.6 Export par lots

- Sélection multiple de chapitres dans l’UI.
- Génération d’un fichier par chapitre, ou d’un seul fichier agrégé (pour EPUB).
- File d’attente avec progression.

### EPUB multi-chapitres

```typescript
const chapters = selectedChapters.map(ch => ({
  title: ch.title,
  content: ch.paragraphs.map(p => `<p>${escapeHtml(p.translatedText ?? '')}</p>`).join('\n')
}))

const buffer = await epub(
  { title: project.name, author: project.author ?? 'Unknown', version: 3 },
  chapters
)
```

---

## 13.7 Plugins d’export

Le système de plugins (Volume 15) permet d’ajouter des formats (PDF, MOBI, etc.).

```typescript
interface ExportPlugin {
  id: string
  name: string
  supportedFormats: string[]
  export(input: ExportInput): Promise<Buffer | string>
}
```

---

## 13.8 Validation des exports

| Format | Validation |
|--------|------------|
| Markdown | Fichier non vide, balises équilibrées. |
| TXT | Fichier non vide. |
| HTML | HTML valide (balises fermées). |
| DOCX | Fichier ouvrable sans corruption, taille > 0. |
| EPUB | Vérification structurelle ZIP + OPF + `epubcheck` si disponible. |

### Validation EPUB détaillée

#### 1. Vérification ZIP

Un EPUB valide est un ZIP dont :

- le premier fichier est `mimetype` (non compressé, contenu `application/epub+zip`) ;
- les fichiers `META-INF/container.xml`, `OEBPS/content.opf` (ou équivalent) existent ;
- aucun fichier n’est corrompu (`zipfile.testzip()` retourne `null`).

```typescript
import { readFileSync } from 'node:fs'
import AdmZip from 'adm-zip'

function validateEpubZip(path: string): string | null {
  try {
    const zip = new AdmZip(path)
    if (zip.testZip() !== null) return 'ZIP corrompu'

    const mimetype = zip.readAsText('mimetype')
    if (mimetype !== 'application/epub+zip') return 'mimetype invalide'

    const container = zip.readAsText('META-INF/container.xml')
    if (!container.includes('.opf')) return 'container.xml invalide'

    return null
  } catch (err) {
    return `Erreur ZIP: ${err instanceof Error ? err.message : 'unknown'}`
  }
}
```

#### 2. Vérification OPF

Le package document (`content.opf`) doit contenir :

- un `metadata` avec `dc:title`, `dc:language` ;
- un `manifest` listant tous les fichiers référencés ;
- un `spine` définissant l’ordre de lecture ;
- des `itemref` valides pointant vers des ressources du `manifest`.

#### 3. epubcheck

Si `epubcheck` est installé (Java), lancer en sous-processus :

```typescript
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

async function runEpubcheck(path: string): Promise<{ valid: boolean; errors: string[] }> {
  try {
    const { stdout } = await execFileAsync('java', ['-jar', 'epubcheck.jar', path, '-q'])
    return { valid: stdout.trim().length === 0, errors: stdout.split('\n').filter(Boolean) }
  } catch (err) {
    return { valid: false, errors: [err instanceof Error ? err.message : 'epubcheck failed'] }
  }
}
```

**Politique.** En v1.0, `epubcheck` est optionnel : la validation ZIP + OPF est obligatoire, `epubcheck` est un avertissement si non installé et un critère bloquant si installé.

---

## ✅ Critères d’acceptation de l’export

- [ ] Markdown et TXT sont générés nativement et non vides.
- [ ] DOCX est généré sans corruption, ouvrable dans LibreOffice/Word, taille > 0.
- [ ] EPUB passe la validation ZIP (`mimetype`, `META-INF/container.xml`, OPF présents) ; si `epubcheck` est installé, aucune erreur.
- [ ] HTML est autonome avec CSS intégré et balises fermées.
- [ ] L’export est enregistré dans la table `exports` avec `format`, `file_path`, `size`, `created_at`.
- [ ] Les métadonnées `title`, `author`, `language` sont injectées selon le format.
- [ ] Le mode bilingue est disponible pour EPUB, HTML, Markdown et TXT.
- [ ] Les plugins peuvent ajouter des formats via l’interface `ExportPlugin`.
- [ ] L’export par lots génère un fichier agrégé pour EPUB et un fichier par chapitre pour les autres formats.

---

## 📚 Références Context7

- /dolanmiu/docx — Génération DOCX.
- /cpiber/epub-gen-memory — Génération EPUB (à valider ; alternatives : pub-gen, rchiver + jsdom).
- /wladimir-tm/adm-zip — Validation de l’archive ZIP EPUB.
- pubcheck (W3C) — Validation EPUB via Java.


# Volume 5 — Gestion des projets

## 5.1 Structure d’un projet

Chaque projet est un dossier autonome et portable.

```text
MonProjet/
├── chapitres/              # Fichiers source importés (copie brute)
├── source/                 # Copie brute des sources (EPUB, DOCX, TXT…)
├── traductions/            # Traductions générées (Markdown par défaut)
├── lexique/                # Export/import du lexique
├── exports/                # Fichiers exportés (DOCX, EPUB, HTML)
├── cache/                  # Cache IA, embeddings, résultats intermédiaires
├── logs/                   # Logs du projet
├── project.db              # Base SQLite du projet
└── config.json             # Configuration locale du projet
```

### Conventions

| Dossier | Contenu | Immutable | Usage |
|---|---|---|---|
| `chapitres/` | Fichiers source tels que téléchargés/importés par l’utilisateur (EPUB, DOCX, TXT, etc.). | Oui | Archive de référence ; permet de relancer un import si `source/` est corrompu. |
| `source/` | Copie de travail normalisée en Markdown, un fichier par chapitre (`ch001.md`, `ch002.md`, …). | Non (régénérée à chaque import) | Point d’entrée du pipeline : découpage en paragraphes, affichage côte à côte, comparaison de versions. |
| `traductions/` | Sorties Markdown générées par l’agent Export avant conversion finale (DOCX, EPUB, HTML). | Non | Permet de relire / corriger sans repasser par l’agent. |
| `lexique/` | Exports/imports CSV, JSON, TSV du lexique. | Non | Partage et sauvegarde du lexique entre projets. |
| `exports/` | Fichiers finaux exportés (DOCX, EPUB, HTML, TXT). | Non | Livrables utilisateur. |
| `cache/` | Réponses IA, embeddings, résultats intermédiaires de parsing. | Non | Réduction des appels IA et accélération du rechargement. |
| `logs/` | Logs spécifiques au projet (rotation 30 jours). | Non | Debug et audit projet. |

**Règle d’or.** L’agent `Split` lit toujours `source/`, jamais `chapitres/`. L’agent `Export` écrit dans `traductions/` puis copie dans `exports/` après validation du format.

---

## 5.2 Création d’un projet

### Wizard

```text
┌─────────────────────────────────────┐
│  Nouveau projet                     │
│                                     │
│  Nom          [ MonRoman          ] │
│  Auteur       [                   ] │
│  Langue source [ ▼ 中文            ] │
│  Langue cible [ ▼ Français        ] │
│  Dossier      [ ~/NovelTrad/...   ] │
│                                     │
│  [ Créer ]                          │
└─────────────────────────────────────┘
```

### Données créées

1. Dossier projet avec sous-dossiers.
2. `project.db` avec les tables vides.
3. `config.json` avec les métadonnées.
4. Entrée dans la table `Projects`.
5. Entrée dans l’historique des projets récents.

### Configuration projet (`config.json`)

```json
{
  "id": "uuid",
  "name": "MonRoman",
  "author": "Auteur",
  "sourceLanguage": "zh",
  "targetLanguage": "fr",
  "createdAt": "2026-06-29T21:00:00Z",
  "updatedAt": "2026-06-29T21:00:00Z",
  "version": "1.0.0",
  "parser": {
    "chapterSeparator": "^Chapter\\s+\\d+",
    "paragraphSeparator": "\\n\\n"
  }
}
```

---

## 5.3 Ouverture d’un projet

- Vérification que `project.db` existe.
- Migration automatique si le schéma est ancien.
- Ajout à la liste des projets récents (max 10).
- Émission d’un événement `project:opened`.
- Vérification de l’intégrité (fichiers manquants, permissions).

### Fermeture d’un projet

- Sauvegarde des états modifiés.
- Fermeture des connexions SQLite.
- Retour à l’écran Accueil.

---

## 5.4 Import de sources

### Formats supportés v1.0

| Format | Extension | Méthode de parsing | Notes |
|--------|-----------|--------------------|-------|
| Texte brut | `.txt` | Lecture directe + détection encodage | UTF-8 par défaut, fallback Latin-1 |
| Markdown | `.md` | Lecture directe | Préservation balises Markdown |
| Microsoft Word | `.docx` | `mammoth.js` → HTML → Markdown | Extraction images optionnelle |
| EPUB | `.epub` | `@likecoin/epub-ts` | Extraction métadonnées + TOC |

### Processus d’import

```text
Fichier source
    ↓
Copie dans chapitres/
    ↓
Extraction du texte brut
    ↓
Détection de la langue source (si non précisée)
    ↓
Découpage en chapitres
    ↓
Découpage en paragraphes
    ↓
Insertion dans source/ + SQLite
    ↓
Indexation dans la Translation Memory (phrases exactes)
    ↓
Notification UI
```

### Implémentation par format

#### TXT

```typescript
import { readFile } from 'node:fs/promises'
import { detectEncoding } from './encoding'

async function parseTxt(filePath: string): Promise<ParsedChapter[]> {
  const buffer = await readFile(filePath)
  const encoding = detectEncoding(buffer)
  const text = new TextDecoder(encoding).decode(buffer)
  return splitIntoChapters(text)
}
```

---

## 5.4b Gestion des encodages

### Détection

```typescript
import chardet from 'chardet'
import iconv from 'iconv-lite'

function detectEncoding(buffer: Buffer): string {
  // chardet retourne le nom le plus probable ; fallback UTF-8
  return chardet.analyse(buffer)[0]?.name ?? 'UTF-8'
}
```

### Ordre de fallback

1. **UTF-8** : encodage par défaut ; testé d’abord via BOM ou validation.
2. **chardet** : si UTF-8 invalide, détection statistique.
3. **Latin-1 / Windows-1252** : fallback final pour les fichiers anciens.
4. **Confirmation utilisateur** : si la confiance est faible (< 0.7), afficher un sélecteur d’encodage.

### Normalisation

Tous les fichiers `source/` sont stockés en **UTF-8** après détection et conversion éventuelle. Cela garantit que les agents IA et le diff fonctionnent sur une base homogène.

### Implémentation

```typescript
import iconv from 'iconv-lite'

function normalizeToUtf8(buffer: Buffer, encoding: string): string {
  return iconv.decode(buffer, encoding)
}
```

**Référence** (Context7: `/chardet/chardet`, `/ashtuchkov/iconv-lite`) : `chardet.analyse(buffer)` retourne une liste de candidats avec score ; `iconv-lite` convertit depuis/vers de nombreux encodages.

#### Markdown

```typescript
async function parseMarkdown(filePath: string): Promise<ParsedChapter[]> {
  const text = await readFile(filePath, 'utf-8')
  return splitIntoChapters(text)
}
```

#### DOCX via Mammoth

```typescript
import mammoth from 'mammoth'
import { unified } from 'unified'
import rehypeParse from 'rehype-parse'
import rehypeRemark from 'rehype-remark'
import remarkStringify from 'remark-stringify'

async function parseDocx(filePath: string): Promise<ParsedChapter[]> {
  const result = await mammoth.convertToHtml({ path: filePath })
  const markdown = await unified()
    .use(rehypeParse)
    .use(rehypeRemark)
    .use(remarkStringify)
    .process(result.value)
  return splitIntoChapters(String(markdown))
}
```

**Référence** (Context7: `/mwilliamson/mammoth.js`) : `mammoth.convertToHtml({ path })` retourne `{ value: HTML, messages: [] }`. Conversion HTML → Markdown via `rehype-remark` recommandée car `convertToMarkdown` est déprécié.

#### EPUB via epub.ts

```typescript
import { Book } from '@likecoin/epub-ts/node'
import { readFileSync } from 'node:fs'

async function parseEpub(filePath: string): Promise<ParsedChapter[]> {
  const data = readFileSync(filePath)
  const arrayBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength)
  const book = new Book(arrayBuffer)
  await book.opened

  const chapters: ParsedChapter[] = []
  for (const section of book.spine.spineItems) {
    const html = await section.render(book.archive.request.bind(book.archive))
    const text = htmlToMarkdown(html) // via rehype/remark
    chapters.push({
      title: section.label || section.idref,
      content: text
    })
  }
  return chapters
}
```

**Référence** (Context7: `/likecoin/epub.ts`) : `@likecoin/epub-ts/node` permet le parsing côté serveur/Node. À valider au moment de l'implémentation : vérifier que le package est encore maintenu ou privilégier `epubjs`/`adm-zip` + `cheerio` comme alternative.

`book.spine.spineItems` itère les sections ; `section.render(...)` retourne le HTML de chaque chapitre.

---

## 5.5 Découpage en chapitres

### Stratégies

| Format | Stratégie |
|--------|-----------|
| Fichier unique (TXT, MD) | Découpage par motifs `Chapter N`, `Chapitre N`, `第N章`, sauts de ligne doubles entre blocs numérotés. |
| DOCX avec styles | Utilisation des styles Heading 1 comme délimiteurs de chapitre. |
| EPUB | Utilisation de la table des matières (TOC) ou des fichiers spine. |

### Algorithme générique

```typescript
function splitIntoChapters(text: string, options: ParserOptions): ParsedChapter[] {
  const separators = options.chapterSeparator
    ? [new RegExp(options.chapterSeparator, 'm')]
    : defaultSeparators

  const rawChapters = splitByPatterns(text, separators)

  return rawChapters.map((raw, index) => {
    const title = extractTitle(raw) || `Chapitre ${index + 1}`
    const paragraphs = splitIntoParagraphs(raw, options.paragraphSeparator)
    return { title, index, paragraphs }
  })
}
```

### Délimiteurs par défaut

```typescript
const defaultSeparators = [
  /^Chapter\s+\d+/im,
  /^Chapitre\s+\d+/im,
  /^第\s*\d+\s*章/im,
  /^\d+\.\s+/im
]
```

---

## 5.6 Découpage en paragraphes

### Règles

- Séparer par doubles sauts de ligne (`\n\n`).
- Préserver les dialogues : ne pas fusionner deux lignes commençant par `—`, `-`, guillemets.
- Préserver les balises Markdown (`#`, `**`, `*`) et HTML (`<p>`, `<br>`).
- Ignorer les paragraphes vides inutiles mais conserver les paragraphes vides intentionnels dans les dialogues.

```typescript
function splitIntoParagraphs(text: string, separator = '\n\n'): string[] {
  return text
    .split(separator)
    .map(p => p.trim())
    .filter(p => p.length > 0 || isDialoguePlaceholder(p))
}
```

---

## 5.7 Détection de la langue source

Si l’utilisateur n’a pas précisé la langue source au moment de l’import :

1. Prendre un échantillon des 1000 premiers caractères.
2. Utiliser `franc` pour détecter la langue.
3. Si la confiance est faible (< 0.8), demander confirmation à l’utilisateur.

```typescript
import { franc } from 'franc'

function detectLanguage(text: string): string {
  const sample = text.slice(0, 1000)
  return franc(sample) || 'und'
}
```

**Référence** (Context7: `/wooorm/franc`) : `franc(text)` retourne un code ISO 639-3 (`cmn` pour chinois mandarin, `jpn` pour japonais, etc.). Mapping vers les codes utilisés par l’application (`zh`, `ja`, `ko`, `fr`, `en`).

---

## 5.8 Synchronisation fichier ↔ Base de données

### Import initial

1. Le fichier source est copié dans `chapitres/`.
2. Le texte est extrait et stocké dans `source/` au format Markdown.
3. Les chapitres/paragraphes sont insérés dans SQLite.
4. Les IDs SQLite pointent vers les fichiers `source/`.

### Mise à jour d’un chapitre source

- L’utilisateur réimporte un fichier.
- L’application détecte les chapitres existants par titre ou index.
- Options :
  - **Remplacer** : écraser les paragraphes existants (traductions conservées si possible).
  - **Fusionner** : ajouter uniquement les nouveaux paragraphes.
  - **Nouvelle version** : créer un chapitre distinct.

### Re-synchronisation manuelle

- Bouton “Rafraîchir depuis le fichier source” sur un chapitre.
- Comparaison des hashes du fichier source.

---

## 5.9 Import par glisser-déposer

### Renderer

```vue
<script setup lang="ts">
function onDrop(event: DragEvent) {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (!files) return
  const paths = Array.from(files).map(f => f.path)
  window.novelTradAPI.importSourceFiles(paths)
}
</script>

<template>
  <div
    class="drop-zone"
    @dragover.prevent
    @drop="onDrop"
  >
    Glissez-déposez vos fichiers ici
  </div>
</template>
```

### Main process

```typescript
ipcMain.handle('source:import-files', async (_event, projectId: string, filePaths: string[]) => {
  const results = await projectManager.importSourceFiles(projectId, filePaths)
  return results
})
```

---

## 5.10 Gestion des doublons

### Détection

- Deux chapitres avec le même titre dans le même projet.
- Deux fichiers source identiques (hash SHA256).

### Comportement

- Avertissement à l’utilisateur.
- Options :
  - Ignorer le doublon.
  - Remplacer l’existant.
  - Renommer (`Chapitre 1 (2)`).

---

## 5.11 Suppression d’un projet

- Demande confirmation.
- Option “Supprimer les fichiers du disque” ou “Retirer de la liste seulement”.
- Si suppression fichiers :
  - Fermer les connexions SQLite.
  - Supprimer le dossier récursivement.
  - Supprimer de l’historique des projets récents.

---

## 5.12 ProjectManager

```typescript
interface ProjectManager {
  create(config: ProjectConfig): Promise<Project>
  open(path: string): Promise<Project>
  close(projectId: string): Promise<void>
  importSource(projectId: string, filePath: string, strategy?: ImportStrategy): Promise<Chapter[]>
  importSourceFiles(projectId: string, filePaths: string[]): Promise<ImportResult[]>
  delete(projectId: string, removeFiles: boolean): Promise<void>
  getRecentProjects(): ProjectSummary[]
  refreshSource(projectId: string, chapterId: string): Promise<Chapter>
  detectDuplicate(projectId: string, filePath: string): Promise<DuplicateInfo | null>
}
```

---

## 5.13 Fichier source normalisé

Pour chaque chapitre importé, un fichier Markdown est généré dans `source/` :

```text
source/
├── ch001.md
├── ch002.md
└── ch003.md
```

Format interne :

```markdown
# Chapitre 1 : Le réveil

林明站起身来，望向了远方的天空。

“今天，我一定要突破！”
```

Cette normalisation simplifie le rechargement, la comparaison et le versionnage.

---

## 5.14 Migration d’un projet v4

(À documenter en v2.0 — conversion depuis `.noveltrad_state.db`.)

---

## ✅ Critères d’acceptation de la gestion des projets

- [ ] Création d’un projet via UI génère l’arborescence complète (`chapitres/`, `source/`, `traductions/`, `lexique/`, `exports/`, `cache/`, `logs/`, `project.db`, `config.json`).
- [ ] Ouverture d’un projet charge le schéma SQLite, applique les migrations si nécessaire, et restaure les 10 projets récents.
- [ ] Import d’un fichier TXT/DOCX/EPUB crée des chapitres et paragraphes dans `source/` + SQLite.
- [ ] L’encodage des fichiers TXT est détecté automatiquement (`chardet`) avec fallback UTF-8 → Latin-1 ; les fichiers `source/` sont toujours UTF-8.
- [ ] Les 10 projets récents sont persistés globalement dans `%APPDATA%/NovelTrad/config.json`.
- [ ] Suppression demande une confirmation et permet deux modes (fichiers + liste, ou liste seulement).
- [ ] La détection de langue fonctionne sur les fichiers TXT/MD via `franc` avec confirmation utilisateur si confiance < 0.8.
- [ ] L’import drag-and-drop accepte plusieurs fichiers et signale les doublons.
- [ ] La distinction entre `chapitres/` (archive brute) et `source/` (Markdown normalisé) est respectée par tous les agents.

---

## 📚 Références Context7

- /mwilliamson/mammoth.js — Conversion DOCX → HTML.
- /likecoin/epub.ts — Parsing EPUB côté Node.js (à valider ; alternatives : pubjs, dm-zip + cheerio).
- /wooorm/franc — Détection de langue.
- /chardet/chardet — Détection d'encodage.
- /ashtuchkov/iconv-lite — Conversion d'encodages.



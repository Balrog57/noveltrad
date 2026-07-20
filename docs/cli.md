# Noveltrad CLI — Guide de référence

> La CLI Noveltrad permet de piloter l'application entièrement en ligne de commande, sans interface graphique. Elle est conçue pour être **scriptable** et **consommable par un agent IA** : sortie JSON structurée, exit codes sémantiques, progrès en NDJSON sur stderr.

## Installation

La CLI est incluse dans le dépôt. Depuis la racine du projet :

```bash
# Via npm script (recommandé)
npm run cli -- <command> [options]

# Ou directement via tsx (équivalent)
npx tsx --tsconfig apps/desktop/tsconfig.json \
  --import ./apps/desktop/src/cli/_cli-preload.ts \
  apps/desktop/src/cli/index.ts <command> [options]
```

La CLI partage le fichier de config avec l'app Electron (`%APPDATA%/NovelTrad/config.json` sur Windows). Les projets créés en CLI sont visibles dans l'UI et inversement.

## Commandes

### `doctor` — Diagnostiquer la configuration

Vérifie Ollama, liste les modèles installés, affiche les settings, et émet des recommandations.

```bash
npm run cli -- doctor --json
```

```json
{
  "ok": true,
  "data": {
    "version": "2.3.0",
    "ollama": {
      "available": true,
      "host": "http://localhost:11434",
      "models": ["qwen3.5:9b", "nomic-embed-text:latest"]
    },
    "settings": {
      "defaultModel": "qwen3.5:9b",
      "qualityThreshold": 70,
      "maxConcurrentJobs": 1
    },
    "recentProjects": 7,
    "recommendations": ["Configuration OK — prêt à traduire."]
  }
}
```

### `create` — Créer un projet

```bash
npm run cli -- create --name "Mon Roman" --src de --tgt fr --json
```

Options :
- `-n, --name <name>` (requis) — Nom du projet
- `-s, --src <lang>` — Langue source, code ISO 2 lettres (défaut: `de`)
- `-t, --tgt <lang>` — Langue cible (défaut: `fr`)
- `-p, --parent <path>` — Dossier parent (défaut: `~/NovelTrad Projects`)

Sortie : `{ id, name, path, sourceLanguage, targetLanguage }`

### `list` — Lister les projets récents

```bash
npm run cli -- list --json
```

Sortie : tableau de `{ id, name, sourceLanguage, targetLanguage, path }`

### `import` — Importer un fichier

```bash
npm run cli -- import <projectId> "<chemin/vers/fichier.epub>" --json
```

Formats supportés : `.epub`, `.docx`, `.txt`, `.md`

Pour les EPUB multi-fichiers (sammelbände), chaque fichier xhtml du spine devient un chapitre séparé. Un chapitre > 100 000 caractères est re-découpé au prochain séparateur de paragraphe.

Sortie : `{ projectId, importedChapters, chapters: [{ id, title, orderIndex, status }] }`

### `chapters` — Lister les chapitres

```bash
npm run cli -- chapters <projectId> --with-paragraphs --json
```

Options :
- `--with-paragraphs` — Inclut le nombre de paragraphes, caractères et paragraphes traduits

Sortie : `{ projectId, chapterCount, chapters: [{ id, title, orderIndex, status, paragraphs?, characters?, translatedParagraphs? }] }`

### `translate` — Lancer le workflow de traduction

```bash
# Un seul chapitre
npm run cli -- translate <projectId> -c <chapterId> --json

# Batch (tous les chapitres)
npm run cli -- translate <projectId> --json

# Non-bloquant (rend le jobId immédiatement)
npm run cli -- translate <projectId> --no-wait --json
```

Options :
- `-c, --chapter <id>` — Traduire un seul chapitre (sinon: batch complet)
- `--no-wait` — Renvoie le jobId immédiatement sans attendre la fin

**Prérequis** : Ollama doit être accessible et le modèle par défaut (`defaultModel` dans les settings) doit être installé. Utilisez `doctor` pour vérifier.

**Progrès** : émis sur **stderr** au format NDJSON (une ligne JSON par event) :
```json
{"type":"progress","payload":{"jobId":"...","step":{"stage":"translate","status":"running"},"totalSteps":12}}
```

Un agent IA peut parser ces lignes au fur et à mesure pour suivre l'avancement sans attendre la fin du process.

Sortie finale (sur stdout) : `{ jobId, status, type, startedAt, finishedAt, costUsd?, errorMessage? }`

### `export` — Exporter un chapitre traduit

```bash
# Un seul chapitre
npm run cli -- export <projectId> -f epub -c <chapterId> --json

# Batch complet
npm run cli -- export <projectId> -f epub --json
```

Options :
- `-f, --format <format>` (requis) — `md`, `txt`, `docx`, `epub`, `html`
- `-c, --chapter <id>` — Un seul chapitre (sinon: batch complet)
- `-o, --out <path>` — Dossier de sortie (défaut: `<project>/exports`)

**Prérequis** : au moins un chapitre doit avoir des paragraphes traduits (status `translated`). Sinon : erreur `NOT_TRANSLATED`.

Sortie : `{ projectId, format, exportedChapters, paths: [...] }`

### `status` — Consulter l'état d'un job

```bash
# Tous les jobs d'un projet
npm run cli -- status <projectId> --json

# Un job spécifique (avec ses steps)
npm run cli -- status <projectId> --job <jobId> --json
```

Sortie : `{ job: {...}, steps: [{ stage, status, score, durationMs, ... }] }` ou `{ projectId, jobs: [...] }`

## Exit codes sémantiques

Pour qu'un script shell ou un agent IA puisse distinguer les causes d'échec :

| Code | Cause | Exemples |
|------|-------|----------|
| `0`  | Succès | |
| `1`  | Erreur utilisateur | Projet existe, fichier absent, args invalides |
| `2`  | Ollama inaccessible | Réseau, modèle absent |
| `3`  | Erreur DB | Migration, corruption |
| `4`  | Traduction échouée | QA trop bas, timeout step |
| `5`  | Erreur inconnue | Bug non catégorisé |

## Format de sortie

### Mode texte (défaut)

Sortie lisible sur stdout, erreurs sur stderr.

### Mode JSON (`--json`)

Un unique objet JSON sur stdout :
```json
// Succès
{ "ok": true, "data": { ... } }

// Erreur
{ "ok": false, "error": { "code": "NOT_FOUND", "message": "Projet introuvable : abc-123" } }
```

## Session complète (exemple agent IA)

```bash
# 1. Diagnostiquer
npm run cli -- doctor --json

# 2. Créer un projet
PROJECT=$(npm run cli -- create --name "Perry Rhodan 1876-1899" --src de --tgt fr --json)
PROJECT_ID=$(echo "$PROJECT" | jq -r '.data.id')

# 3. Importer l'EPUB
npm run cli -- import "$PROJECT_ID" "~/Downloads/Perry Rhodan.epub" --json

# 4. Vérifier le découpage
npm run cli -- chapters "$PROJECT_ID" --with-paragraphs --json

# 5. Traduire le premier chapitre de contenu
FIRST_CHAPTER=$(npm run cli -- chapters "$PROJECT_ID" --with-paragraphs --json | jq -r '.data.chapters[] | select(.characters > 1000) | .id' | head -1)
npm run cli -- translate "$PROJECT_ID" -c "$FIRST_CHAPTER" --json

# 6. Exporter
npm run cli -- export "$PROJECT_ID" -f epub -c "$FIRST_CHAPTER" --json
```

## Notes techniques

- **Worker threads** : la CLI force `useWorkerThreads=false` (les workers réimportent du code couplé à Electron).
- **Plugins** : non supportés en CLI (`pluginHost` non connecté).
- **electron-log** : stubbé via un resolver ESM (`_cli-preload.ts`) car il crash hors Electron.
- **Settings** : partagés avec l'app Electron (même fichier `config.json`).

# Volume 6 — Base de données

## 6.1 Technologie

- **SQLite** via `better-sqlite3`.
- Schéma versionné, migrations en SQL pur.
- Repositories pour isoler la logique SQL.
- WAL mode activé pour meilleures performances en écriture.

## 6.2 Tables principales

| Table | Rôle |
|-------|------|
| `projects` | Méta-projet global |
| `chapters` | Chapitres du projet |
| `paragraphs` | Paragraphes avec source + traduction |
| `lexicon` | Entrées lexicales |
| `lexicon_aliases` | Alias des entrées lexicales |
| `translation_memory` | Phrases/traductions connues |
| `models` | Providers et modèles configurés |
| `jobs` | Workflow jobs en cours/passés |
| `job_steps` | Étapes d’un job |
| `history` | Versions de traduction |
| `exports` | Fichiers exportés |
| `prompts` | Prompt templates versionnés |
| `agents` | Définitions d’agents installés |
| `settings` | Préférences utilisateur |
| `statistics` | Métriques agrégées |

## 6.3 Schéma SQL (v1.0)

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  author TEXT,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  version TEXT NOT NULL
);

CREATE TABLE chapters (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT,
  source_path TEXT,
  order_index INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE paragraphs (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  index_in_chapter INTEGER NOT NULL,
  source_text TEXT NOT NULL,
  translated_text TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata TEXT -- JSON
);

CREATE TABLE lexicon (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  translation TEXT NOT NULL,
  category TEXT NOT NULL, -- character, sect, object, skill, place, etc.
  gender TEXT,
  description TEXT,
  notes TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  locked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE lexicon_aliases (
  id TEXT PRIMARY KEY,
  lexicon_id TEXT NOT NULL REFERENCES lexicon(id) ON DELETE CASCADE,
  alias TEXT NOT NULL
);

CREATE TABLE translation_memory (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_text TEXT NOT NULL,
  target_text TEXT NOT NULL,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  usage_count INTEGER NOT NULL DEFAULT 1,
  last_used_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE models (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL, -- ollama, openai, anthropic, gemini, openrouter, lmstudio, custom
  name TEXT NOT NULL,
  model TEXT NOT NULL,
  host TEXT,
  api_key TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  is_fallback INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT,
  metadata TEXT -- JSON
);

CREATE TABLE job_steps (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  input_snapshot TEXT, -- JSON
  output_snapshot TEXT, -- JSON
  score REAL,
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT
);

CREATE TABLE history (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  source_snapshot TEXT,
  translated_snapshot TEXT,
  quality_score REAL,
  created_at TEXT NOT NULL
);

CREATE TABLE exports (
  id TEXT PRIMARY KEY,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  format TEXT NOT NULL,
  file_path TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE prompts (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  role TEXT NOT NULL, -- system, user
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  stage TEXT NOT NULL, -- pre_translate, translate, consistency, lexicon, grammar, style, polish, qa, export
  enabled INTEGER NOT NULL DEFAULT 1,
  config_schema TEXT -- JSON
);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE statistics (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  total_chapters INTEGER NOT NULL DEFAULT 0,
  translated_chapters INTEGER NOT NULL DEFAULT 0,
  total_paragraphs INTEGER NOT NULL DEFAULT 0,
  translated_paragraphs INTEGER NOT NULL DEFAULT 0,
  total_words INTEGER NOT NULL DEFAULT 0,
  total_jobs INTEGER NOT NULL DEFAULT 0,
  average_quality_score REAL,
  updated_at TEXT NOT NULL
);

CREATE INDEX idx_paragraphs_chapter ON paragraphs(chapter_id);
CREATE INDEX idx_lexicon_project ON lexicon(project_id);
CREATE INDEX idx_history_chapter ON history(chapter_id);
CREATE INDEX idx_jobs_project ON jobs(project_id);
CREATE INDEX idx_tm_project_text ON translation_memory(project_id, source_text);
```

## 6.4 Migrations

Les migrations sont stockées dans `src/main/db/migrations/`.

```typescript
interface Migration {
  version: number
  name: string
  up: string
  down: string
}

class MigrationRunner {
  run(db: Database, targetVersion: number): void
  getCurrentVersion(db: Database): number
}
```

## 6.5 Repository pattern

```typescript
class ParagraphRepository {
  constructor(private db: Database) {}

  getByChapter(chapterId: string): Paragraph[]
  updateTranslation(id: string, text: string): void
  bulkInsert(paragraphs: ParagraphInsert[]): void
}
```

## ✅ Critères d’acceptation de la base de données

- [ ] Le schéma SQL crée toutes les tables sans erreur.
- [ ] Les migrations montent et descendent correctement.
- [ ] Les repositories couvrent CRUD pour chaque entité métier.
- [ ] Les index accélèrent les requêtes de lexique et de mémoire de traduction.
- [ ] Suppression d’un projet en cascade efface les données associées.

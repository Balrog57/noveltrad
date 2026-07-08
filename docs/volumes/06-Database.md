# Volume 6 — Base de données

## 6.1 Technologie

- **SQLite** via `node-sqlite3-wasm` (binding WASM synchrone).
  > **Décision de conception** : `better-sqlite3` était initialement prévu, mais le
  > rebuild natif pose problème lors du packaging Electron (gestion
  > `app.asar.unpacked`, recompilation par plateforme). `node-sqlite3-wasm` est
  > purement JavaScript (WASM), ce qui élimine cette friction. La migration vers
  > `better-sqlite3` est **WONTFIX** (cf. `docs/audit/GAP_ANALYSIS_2.1.3_to_SDD.md` §2.1).
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
| `history_snapshots` | Versions de traduction (snapshots JSON enrichis) |
  > **Décision de conception** : le SDD initial nommait cette table `history`. Le
  > code crée `history_snapshots` avec un schéma JSON plus riche (snapshots
  > incrémental/complet + métadonnées). Le nom `history_snapshots` est entériné
  > comme canonique (cf. Open Questions WORKFLOW_STATE.md).
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

CREATE TABLE history_snapshots (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  snapshot_type TEXT NOT NULL, -- 'full' | 'incremental'
  source_snapshot TEXT, -- JSON
  translated_snapshot TEXT, -- JSON
  quality_score REAL,
  metadata TEXT, -- JSON (score détaillé, étapes, coût, etc.)
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
CREATE INDEX idx_paragraphs_status ON paragraphs(status);
CREATE INDEX idx_lexicon_project ON lexicon(project_id);
CREATE INDEX idx_history_snapshots_chapter ON history_snapshots(chapter_id);
CREATE INDEX idx_history_snapshots_project ON history_snapshots(project_id);
CREATE INDEX idx_jobs_project ON jobs(project_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_job_steps_job ON job_steps(job_id);
CREATE INDEX idx_prompts_agent ON prompts(agent_id);
CREATE INDEX idx_tm_project_text ON translation_memory(project_id, source_text);
```

## 6.4 Migrations

Les migrations sont stockées dans `src/main/db/migrations/`.

### Index de couverture (v1.3)

La migration `013_index_cost.sql` ajoute les index manquants sur les colonnes de statut et de jointure fréquemment filtrées, ainsi que la colonne `cost_usd` sur `jobs` (SDD §3.8) :

| Index / Colonne | Usage (requêtes fréquentes) |
|-------|------------------------------|
| `idx_paragraphs_status` | Filtre des paragraphes par statut dans l'éditeur chapitres |
| `idx_prompts_agent` | Recherche des prompts par agent dans PromptLoader |
| `jobs.cost_usd` | Accumulation du coût estimé par job (providers cloud) |

> Note : `idx_jobs_status` et `idx_job_steps_job` existent déjà (migrations 006 et 002).

### Modèle de données (notes de conception)

- **Pas de table `books`** : la hiérarchie `project → chapter` est intentionnelle pour v1.0 (projets mono-ouvrage). Un tier intermédiaire `books` est prévu pour v2.0 (support des séries web-novel).
- **Pas de table `queue` dédiée** : la table `jobs` fait office de file d'attente via sa colonne `status`. Une table séparée n'est pas nécessaire en v1.0 (concurrence gérée en mémoire par PQueue, cf. Vol 07 §7.9).
- **Pas de table `providers` séparée** : les providers sont représentés par la colonne `models.provider` (texte). Un provider peut avoir plusieurs entrées `models`. Suffisant pour v1.0.

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
- [ ] Les index accélèrent les requêtes de lexique, de mémoire de traduction et les filtres par statut.
- [ ] Suppression d’un projet en cascade efface les données associées.
- [ ] La migration `013_index_cost.sql` s’applique sans erreur sur une DB existante (v1.0 → v1.3).

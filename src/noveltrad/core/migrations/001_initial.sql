-- Initial NovelTrad schema (SDD chapter 8, version 1).
-- All dates are stored as UTC ISO-8601 TEXT. Foreign keys enabled by core.

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    source_language TEXT,
    target_language TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Draft','Ready','Running','Paused','Completed','Failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completion_notice_claimed_at TEXT,
    completion_notice_acknowledged_at TEXT
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    import_format TEXT NOT NULL CHECK (import_format IN ('epub','docx','txt','md','srt')),
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    source_path TEXT NOT NULL UNIQUE,
    source_hash TEXT NOT NULL,
    translated_path TEXT UNIQUE,
    translated_hash TEXT,
    status TEXT NOT NULL CHECK (status IN ('ToTranslate','Running','Paused','Completed','Failed')),
    progress REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    word_count INTEGER NOT NULL DEFAULT 0 CHECK (word_count >= 0),
    character_count INTEGER NOT NULL DEFAULT 0 CHECK (character_count >= 0),
    detected_language TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL,
    CONSTRAINT uq_documents_project_order UNIQUE (project_id, order_index)
);

CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    title TEXT,
    source_start INTEGER NOT NULL,
    source_end INTEGER NOT NULL,
    source_hash TEXT NOT NULL,
    translated_start INTEGER,
    translated_end INTEGER,
    translated_hash TEXT,
    CONSTRAINT uq_chapters_document_order UNIQUE (document_id, order_index),
    CHECK (source_end > source_start)
);

CREATE TABLE segments (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL CHECK (order_index >= 0),
    source_start INTEGER NOT NULL,
    source_end INTEGER NOT NULL,
    source_hash TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','TRANSLATED','REVISED','COHERENCE_CHECKED','POLISHED')),
    checkpoint_path TEXT,
    checkpoint_hash TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0 AND retry_count <= 5),
    last_error TEXT,
    updated_at TEXT NOT NULL,
    CONSTRAINT uq_segments_chapter_order UNIQUE (chapter_id, order_index),
    CHECK (source_end > source_start),
    CHECK ((state = 'PENDING' AND checkpoint_path IS NULL AND checkpoint_hash IS NULL) OR state != 'PENDING')
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('Waiting','Queued','Running','Paused','Retrying','Completed','Failed')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    current_stage TEXT CHECK (current_stage IN ('translate','revise','context','polish')),
    current_segment_id INTEGER REFERENCES segments(id) ON DELETE SET NULL,
    progress REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    last_message TEXT,
    control_request TEXT CHECK (control_request IS NULL OR control_request = 'PAUSE'),
    control_requested_at TEXT,
    next_retry_at TEXT,
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);

CREATE INDEX idx_jobs_fifo ON jobs(state, queued_at, id);
CREATE UNIQUE INDEX uq_jobs_single_active ON jobs((1)) WHERE state IN ('Running','Retrying');
CREATE UNIQUE INDEX uq_jobs_document_open ON jobs(document_id) WHERE state IN ('Waiting','Queued','Running','Paused','Retrying','Failed');
CREATE INDEX idx_jobs_retry ON jobs(state, next_retry_at, id);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    is_secret INTEGER NOT NULL DEFAULT 0 CHECK (is_secret IN (0,1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')),
    event TEXT NOT NULL,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    correlation_id TEXT NOT NULL,
    error_code TEXT,
    message TEXT NOT NULL,
    details_json TEXT
);

CREATE INDEX idx_logs_created_at ON logs(created_at);
CREATE INDEX idx_logs_project ON logs(project_id, created_at);
CREATE INDEX idx_logs_correlation ON logs(correlation_id, created_at);

CREATE TABLE file_operations (
    id INTEGER PRIMARY KEY,
    operation TEXT NOT NULL CHECK (operation IN ('IMPORT_DOCUMENT','RESET_DOCUMENT','EDIT_DOCUMENT','EDIT_PROJECT','DELETE_DOCUMENT','DELETE_PROJECT')),
    project_id INTEGER,
    document_id INTEGER,
    staged_path TEXT,
    target_path TEXT NOT NULL,
    payload_hash TEXT,
    phase TEXT NOT NULL CHECK (phase IN ('PREPARED','DB_COMMITTED','PUBLISHED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_file_operations_phase ON file_operations(phase, id);

CREATE TABLE worker_runtime (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL CHECK (state IN ('Starting','Idle','Busy','StoppingAfterCall','Stopped')),
    heartbeat_at TEXT NOT NULL,
    started_at TEXT NOT NULL
);

CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_segments_resume ON segments(state, chapter_id, order_index);
CREATE INDEX idx_projects_completion_notice ON projects(status, completion_notice_acknowledged_at, id);

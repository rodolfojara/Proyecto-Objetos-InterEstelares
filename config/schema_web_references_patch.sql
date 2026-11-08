-- Web references curation patch: curated web/news/reference links (complement to media_resources/YouTube)
-- Method: trusted-first + ref-by-ref evaluation; keep above-average ("goyita") even if dated but well-informed.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS curated_references (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE NOT NULL,
  title TEXT,
  source TEXT,                 -- publisher/institution/authoring entity
  domain TEXT,                 -- extracted host
  source_date TEXT,            -- date of the material (may be old)
  ref_type TEXT,               -- institucional, divulgación, análisis, histórica, primaria, etc.
  summary TEXT,                -- curator short summary (what it says)
  evaluation_note TEXT,        -- why kept / what it adds ("goyita"); for rejected: why rejected
  value_score INTEGER,         -- 1-10 (10 = most interesting/valuable), NULL if not scored
  confidence INTEGER DEFAULT 3,-- 1-5
  historical_well_informed INTEGER DEFAULT 0, -- 1 = outdated but well-informed/adequately reported
  status TEXT DEFAULT 'pending', -- pending, accepted, watch, rejected (rejected stored w/ note, hidden in reports)
  tags TEXT,
  agent_review TEXT,           -- validator agent suggestions/flags (JSON/text)
  agent_suggested_status TEXT,
  agent_suggested_value INTEGER,
  added_by TEXT DEFAULT 'curador_referencias_web',
  provenance_url TEXT,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  last_checked_at TIMESTAMP,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS curated_reference_object_links (
  ref_id INTEGER NOT NULL,
  object_id INTEGER NOT NULL,
  relation TEXT DEFAULT 'mentions', -- mentions, explains, analyzes, historical, primary
  confidence INTEGER DEFAULT 3,
  PRIMARY KEY(ref_id, object_id),
  FOREIGN KEY(ref_id) REFERENCES curated_references(id) ON DELETE CASCADE,
  FOREIGN KEY(object_id) REFERENCES objects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_curef_status ON curated_references(status);
CREATE INDEX IF NOT EXISTS idx_curef_value ON curated_references(value_score);
CREATE INDEX IF NOT EXISTS idx_curef_domain ON curated_references(domain);
CREATE INDEX IF NOT EXISTS idx_cureflink_obj ON curated_reference_object_links(object_id);
CREATE INDEX IF NOT EXISTS idx_cureflink_ref ON curated_reference_object_links(ref_id);

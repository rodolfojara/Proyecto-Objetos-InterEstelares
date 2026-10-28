-- Fase 2 patch: aliases and helper structures
PRAGMA foreign_keys = ON;

-- Aliases for objects (provisional designations, old names, etc.)
CREATE TABLE IF NOT EXISTS object_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  alias TEXT NOT NULL,
  source_url TEXT,
  notes TEXT,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE,
  UNIQUE(object_id, alias)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_obj_aliases_obj ON object_aliases(object_id);
CREATE INDEX IF NOT EXISTS idx_obj_aliases_alias ON object_aliases(alias);

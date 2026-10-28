-- Fase 4 patch: retrospective search for hyperbolic candidates
PRAGMA foreign_keys = ON;

-- Retrospective candidates (objects found in historical data with e>1)
CREATE TABLE IF NOT EXISTS retro_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provisional_designation TEXT,
  packed_id TEXT,
  discovery_year INTEGER,
  epoch TEXT,
  a REAL,
  e REAL,
  q REAL,
  i REAL,
  peri REAL,
  node REAL,
  v_inf_est REAL,
  source_file TEXT,
  source_url TEXT,
  found_by TEXT DEFAULT 'historiador',
  status TEXT DEFAULT 'pending', -- pending, reviewed, rejected, confirmed_iso, needs_observation
  review_notes TEXT,
  confidence INTEGER DEFAULT 2,
  retrieved_at TIMESTAMP DEFAULT (datetime('now'))
);

-- Link retro candidates to potential objects
CREATE TABLE IF NOT EXISTS retro_candidate_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id INTEGER NOT NULL,
  reviewer_agent TEXT,
  action TEXT, -- match_existing, create_new, reject, needs_data
  object_id INTEGER,
  reason TEXT,
  evidence TEXT,
  reviewed_at TIMESTAMP DEFAULT (datetime('now')),
  FOREIGN KEY (candidate_id) REFERENCES retro_candidates(id) ON DELETE CASCADE,
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_retro_e ON retro_candidates(e);
CREATE INDEX IF NOT EXISTS idx_retro_status ON retro_candidates(status);
CREATE INDEX IF NOT EXISTS idx_retro_year ON retro_candidates(discovery_year);

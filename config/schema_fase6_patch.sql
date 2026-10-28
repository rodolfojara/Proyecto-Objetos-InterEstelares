-- Fase 6 patch: YouTube / multimedia resources
PRAGMA foreign_keys = ON;

-- Multimedia resources (YouTube, etc)
CREATE TABLE IF NOT EXISTS media_resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL DEFAULT 'youtube', -- youtube, vimeo, other
  url TEXT UNIQUE NOT NULL,
  video_id TEXT,
  title TEXT,
  channel TEXT,
  description TEXT,
  published_at TEXT,
  duration TEXT,
  language TEXT DEFAULT 'es/en',
  relevance_score INTEGER DEFAULT 3, -- 1-5 (5 = muy buen visualizador/resumen)
  tags TEXT,
  notes TEXT,
  added_by TEXT DEFAULT 'curador_multimedia',
  added_at TIMESTAMP DEFAULT (datetime('now')),
  provenance_url TEXT,
  last_checked_at TIMESTAMP DEFAULT (datetime('now'))
);

-- Link between media and objects
CREATE TABLE IF NOT EXISTS media_object_links (
  media_id INTEGER NOT NULL,
  object_id INTEGER NOT NULL,
  relation TEXT DEFAULT 'mentions', -- mentions, explains, visualizes, compares
  confidence INTEGER DEFAULT 3,
  PRIMARY KEY(media_id, object_id),
  FOREIGN KEY(media_id) REFERENCES media_resources(id) ON DELETE CASCADE,
  FOREIGN KEY(object_id) REFERENCES objects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_type ON media_resources(type);
CREATE INDEX IF NOT EXISTS idx_media_relevance ON media_resources(relevance_score);
CREATE INDEX IF NOT EXISTS idx_medialink_obj ON media_object_links(object_id);
CREATE INDEX IF NOT EXISTS idx_medialink_media ON media_object_links(media_id);

-- ISO Tracking System - Patch: cronologia de identificacion
-- Registra las fechas que marcan el paso de "objeto observado" a "objeto interestelar"
-- y sirve de corte para clasificar la literatura previa y posterior a la identificacion.

CREATE TABLE IF NOT EXISTS object_identification (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL UNIQUE,
  earliest_observation_date TEXT,  -- astrometria/imagen mas antigua conocida (aunque no se reconociera el objeto)
  discovery_date TEXT,             -- fecha en que se reconoce y reporta como objeto nuevo
  announcement_date TEXT,          -- primera publicacion oficial (MPEC/CBET/IAU)
  iso_confirmation_date TEXT,      -- fecha en que la orbita hiperbolica / origen interestelar queda establecido
  iso_designation_date TEXT,       -- fecha en que recibe la designacion 1I/2I/3I (desde cuando se le llama interestelar)
  designations_pre_iso TEXT,       -- designaciones previas separadas por ';'
  discoverer TEXT,
  discovery_site TEXT,
  mpc_code TEXT,
  reference_id TEXT,               -- MPEC/CBET/IAU de referencia
  source_url TEXT NOT NULL,
  notes TEXT,
  confidence INTEGER DEFAULT 3,    -- 1-5
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ident_object ON object_identification(object_id);

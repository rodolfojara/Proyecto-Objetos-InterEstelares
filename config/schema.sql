-- ISO Tracking System - Database Schema
-- Fase 0: Preparación

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Objects table (core)
CREATE TABLE IF NOT EXISTS objects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  designation TEXT UNIQUE NOT NULL,  -- 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS, etc.
  name TEXT,
  type TEXT,  -- interstellar_object
  discovery_date TEXT,  -- ISO8601
  status TEXT DEFAULT 'active',  -- active, lost, etc
  parent_system_hypothesis TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT (datetime('now')),
  updated_at TIMESTAMP DEFAULT (datetime('now'))
);

-- Orbital elements (versioned)
CREATE TABLE IF NOT EXISTS orbital_elements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  epoch TEXT,
  a REAL,
  e REAL,  -- eccentricity
  i REAL,  -- inclination
  q REAL,  -- perihelion distance
  incl REAL,
  omega REAL,
  arg_peri REAL,
  node REAL,
  e_hyperbolic_v_inf REAL,  -- hyperbolic excess velocity
  elements_string TEXT,
  solution_version TEXT,
  source_url TEXT NOT NULL,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  confidence INTEGER DEFAULT 3,  -- 1-5
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

-- Physical parameters (versioned)
CREATE TABLE IF NOT EXISTS physical_params (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  param TEXT NOT NULL,  -- diameter, albedo, color, rotation_period, absolute_magnitude
  value REAL,
  value_text TEXT,
  unit TEXT,
  error REAL,
  method TEXT,
  source_url TEXT NOT NULL,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  confidence INTEGER DEFAULT 3,
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

-- Composition
CREATE TABLE IF NOT EXISTS composition (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  species TEXT NOT NULL,  -- H2O, CO, CO2, CN, C2, C3, CH3OH, HCN, CH3D, etc
  production_rate REAL,
  production_rate_unit TEXT,  -- molecules/s
  ratio_to_water REAL,
  rh REAL,  -- heliocentric distance at measurement
  phase TEXT,  -- pre-perihelion, post-perihelion, perihelion
  method TEXT,
  source_url TEXT NOT NULL,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  confidence INTEGER DEFAULT 3,
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

-- Activity
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  rh REAL,
  activity_detected INTEGER DEFAULT 0,  -- 0/1
  coma_detected INTEGER DEFAULT 0,
  dust_detected INTEGER DEFAULT 0,
  source_url TEXT NOT NULL,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  confidence INTEGER DEFAULT 3,
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

-- Publications
CREATE TABLE IF NOT EXISTS publications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doi TEXT UNIQUE,
  arxiv_id TEXT UNIQUE,
  title TEXT NOT NULL,
  authors TEXT,
  journal TEXT,
  published_at TEXT,
  abstract TEXT,
  source_url TEXT,
  processed INTEGER DEFAULT 0,
  retrieved_at TIMESTAMP DEFAULT (datetime('now'))
);

-- Object-Publication link
CREATE TABLE IF NOT EXISTS object_publications (
  object_id INTEGER NOT NULL,
  publication_id INTEGER NOT NULL,
  relevance_score INTEGER DEFAULT 3,
  PRIMARY KEY (object_id, publication_id),
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE,
  FOREIGN KEY (publication_id) REFERENCES publications(id) ON DELETE CASCADE
);

-- Observations
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL,
  telescope TEXT,
  instrument TEXT,
  observation_date TEXT,
  type TEXT,  -- spectroscopy, photometry, imaging
  data_uri TEXT,
  source_url TEXT,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

-- Provenance log (immutable audit trail)
CREATE TABLE IF NOT EXISTS provenance_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity TEXT NOT NULL,  -- objects, orbital_elements, publications, etc
  entity_id INTEGER,
  action TEXT NOT NULL,  -- insert, update, link
  source_url TEXT,
  agent TEXT,  -- vigilante, recolector, normalizador, etc
  details TEXT,
  timestamp TIMESTAMP DEFAULT (datetime('now'))
);

-- Report metrics cache
CREATE TABLE IF NOT EXISTS report_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  metric_key TEXT UNIQUE NOT NULL,
  metric_value TEXT,
  updated_at TIMESTAMP DEFAULT (datetime('now'))
);

-- Identification timeline (Fase 2)
-- Fechas que separan "objeto observado" de "objeto interestelar"
CREATE TABLE IF NOT EXISTS object_identification (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  object_id INTEGER NOT NULL UNIQUE,
  earliest_observation_date TEXT,
  discovery_date TEXT,
  announcement_date TEXT,
  iso_confirmation_date TEXT,
  iso_designation_date TEXT,
  designations_pre_iso TEXT,
  discoverer TEXT,
  discovery_site TEXT,
  mpc_code TEXT,
  reference_id TEXT,
  source_url TEXT NOT NULL,
  notes TEXT,
  confidence INTEGER DEFAULT 3,
  retrieved_at TIMESTAMP DEFAULT (datetime('now')),
  FOREIGN KEY (object_id) REFERENCES objects(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_orbital_object ON orbital_elements(object_id);
CREATE INDEX IF NOT EXISTS idx_physical_object ON physical_params(object_id);
CREATE INDEX IF NOT EXISTS idx_comp_object ON composition(object_id);
CREATE INDEX IF NOT EXISTS idx_activity_object ON activity(object_id);
CREATE INDEX IF NOT EXISTS idx_pub_arxiv ON publications(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_pub_doi ON publications(doi);
CREATE INDEX IF NOT EXISTS idx_prov_entity ON provenance_log(entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_objpub_obj ON object_publications(object_id);
CREATE INDEX IF NOT EXISTS idx_objpub_pub ON object_publications(publication_id);
CREATE INDEX IF NOT EXISTS idx_ident_object ON object_identification(object_id);

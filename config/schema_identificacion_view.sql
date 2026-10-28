-- ISO Tracking System - Vista de clasificacion de literatura por epoca
-- Requiere: object_identification y object_publications.publication_class

DROP VIEW IF EXISTS v_publication_epoch;

CREATE VIEW v_publication_epoch AS
SELECT
  p.id                        AS publication_id,
  p.title                     AS title,
  p.published_at              AS published_at,
  op.object_id                AS object_id,
  o.designation               AS designation,
  oi.earliest_observation_date AS earliest_observation_date,
  oi.iso_confirmation_date    AS iso_confirmation_date,
  oi.iso_designation_date     AS iso_designation_date,
  op.publication_class        AS publication_class,
  CASE
    WHEN p.published_at IS NULL THEN 'desconocido'
    WHEN oi.earliest_observation_date IS NOT NULL
         AND date(p.published_at) < date(oi.earliest_observation_date) THEN 'archivo_previo'
    WHEN oi.iso_confirmation_date IS NOT NULL
         AND date(p.published_at) < date(oi.iso_confirmation_date) THEN 'observado_sin_identificar'
    ELSE 'literatura_interestelar'
  END AS epoch
FROM publications p
JOIN object_publications op ON op.publication_id = p.id
JOIN objects o ON o.id = op.object_id
LEFT JOIN object_identification oi ON oi.object_id = op.object_id;

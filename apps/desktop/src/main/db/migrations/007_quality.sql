-- 007_quality : Calibration des scores de qualité par modèle (SDD §12.5)
-- Stocke les paramètres de régression linéaire (slope, offset) pour chaque
-- couple (modèle, dimension de qualité). Permet de recalibrer les scores
-- heuristiques en fonction du modèle utilisé.

CREATE TABLE IF NOT EXISTS model_calibrations (
  model TEXT NOT NULL,
  dimension TEXT NOT NULL,
  slope REAL NOT NULL DEFAULT 1.0,
  offset REAL NOT NULL DEFAULT 0.0,
  sample_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (model, dimension)
);
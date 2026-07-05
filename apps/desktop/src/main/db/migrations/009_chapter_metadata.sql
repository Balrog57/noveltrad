-- 009_chapter_metadata : Ajout colonne metadata pour stocker les métadonnées des chapitres
ALTER TABLE chapters ADD COLUMN metadata TEXT;

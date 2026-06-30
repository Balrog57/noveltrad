-- 003_lexicon_metadata : Ajout colonne metadata pour stocker gender/pronunciation
ALTER TABLE lexicon ADD COLUMN metadata TEXT;

-- Fichier : db/migrations/005_add_gender_to_agents.sql
-- Description : Ajoute la colonne 'sexe' à la table 'agents'.

BEGIN TRANSACTION;

ALTER TABLE agents ADD COLUMN sexe TEXT;

COMMIT;
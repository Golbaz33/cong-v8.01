-- Fichier : db/migrations/007_add_new_agent_fields.sql
-- Description : Ajoute la situation familiale à tous les agents
-- et les champs de stage spécifiques aux médecins internes.

BEGIN TRANSACTION;

-- Ajoute la colonne 'situation_familiale' à la table 'agents'
-- On utilise ALTER TABLE car la colonne n'existe pas
ALTER TABLE agents ADD COLUMN situation_familiale TEXT;

-- Ajoute les colonnes de stage à la table de profil des médecins internes
-- On utilise ALTER TABLE car la table existe déjà
ALTER TABLE profil_medecin_interne ADD COLUMN site_stage_1 TEXT;
ALTER TABLE profil_medecin_interne ADD COLUMN site_stage_2 TEXT;
ALTER TABLE profil_medecin_interne ADD COLUMN site_stage_3 TEXT;
ALTER TABLE profil_medecin_interne ADD COLUMN site_stage_4 TEXT;
ALTER TABLE profil_medecin_interne ADD COLUMN prolongation TEXT;

COMMIT;
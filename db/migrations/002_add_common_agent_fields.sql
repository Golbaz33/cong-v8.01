-- Fichier : db/migrations/002_add_common_agent_fields.sql
-- VERSION FINALE SIMPLIFIÉE

BEGIN TRANSACTION;

-- L'opération RENAME n'est plus nécessaire.
-- On ajoute directement les nouvelles colonnes communes.
ALTER TABLE agents ADD COLUMN nom_arabe TEXT;
ALTER TABLE agents ADD COLUMN prenom_arabe TEXT;
ALTER TABLE agents ADD COLUMN cnie TEXT;
ALTER TABLE agents ADD COLUMN type_recrutement TEXT;
ALTER TABLE agents ADD COLUMN date_prise_service TEXT;
ALTER TABLE agents ADD COLUMN statut_hierarchique TEXT;
ALTER TABLE agents ADD COLUMN specialite TEXT;
ALTER TABLE agents ADD COLUMN service_affectation TEXT;
ALTER TABLE agents ADD COLUMN telephone_pro TEXT;
ALTER TABLE agents ADD COLUMN email_pro TEXT;
ALTER TABLE agents ADD COLUMN date_cessation_service TEXT;
ALTER TABLE agents ADD COLUMN motif_cessation_service TEXT;

COMMIT;
-- Fichier : db/migrations/006_add_agent_status.sql
-- Description : Ajoute la colonne 'statut_agent' pour la fonctionnalité d'archivage.

BEGIN TRANSACTION;

-- Ajoute la colonne pour le statut de l'agent (Actif / Archivé)
-- NOT NULL garantit que chaque agent aura un statut.
-- DEFAULT 'Actif' assigne automatiquement le statut 'Actif' à tous les agents existants.
ALTER TABLE agents ADD COLUMN statut_agent TEXT DEFAULT 'Actif' NOT NULL;

COMMIT;
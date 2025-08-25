-- Fichier : db/migrations/003_create_history_table.sql
-- Description : Crée la table pour tracer l'historique de carrière des agents.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS historique_carrieres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    date_evenement TEXT NOT NULL,
    type_evenement TEXT NOT NULL,
    service_affectation TEXT,
    specialite TEXT,
    centre_formation TEXT,
    details TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE
);

-- Créer un index sur agent_id pour accélérer les recherches de l'historique d'un agent spécifique.
CREATE INDEX IF NOT EXISTS idx_historique_agent_id ON historique_carrieres (agent_id);

COMMIT;
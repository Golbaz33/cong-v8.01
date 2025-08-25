-- Fichier : db/migrations/004_create_profiles_tables.sql
-- Description : Crée les tables de profils pour les types d'agents spécifiques.

BEGIN TRANSACTION;

-- Table pour les informations spécifiques aux Médecins Résidents
CREATE TABLE IF NOT EXISTS profil_medecin_resident (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL UNIQUE, -- UNIQUE pour garantir un seul profil par agent
    type_residanat TEXT,              -- "Sur titre" ou "Sur concours"
    statut_contrat TEXT,              -- "Bénévole" ou "Contractuel"
    date_fin_formation TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE
);

-- Table pour les informations spécifiques aux Médecins Internes
-- Actuellement vide de champs spécifiques, mais créée pour la cohérence de l'architecture
-- et pour pouvoir y ajouter des champs à l'avenir sans changer le modèle.
CREATE TABLE IF NOT EXISTS profil_medecin_interne (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL UNIQUE,
    -- Pas d'autres champs pour le moment
    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE
);

-- NOTE: Nous ne créons pas de table de profil pour les Enseignants-Chercheurs pour l'instant
-- car tous leurs champs requis ont été jugés "communs" et placés dans la table 'agents'.
-- Si des champs spécifiques apparaissent à l'avenir, nous pourrons créer leur table de profil.

COMMIT;
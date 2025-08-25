# Fichier : db/database.py
# VERSION FINALE - Utilisation de row_factory et ajout de create_solde_annuel.

import sqlite3
from tkinter import messagebox
import logging
import os
import re
from datetime import datetime
from collections import defaultdict

from db.models import Agent, Conge, SoldeAnnuel, HistoriqueCarriere, ProfilMedecinResident
from core.constants import SoldeStatus

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Erreur Base de Données", f"Impossible de se connecter : {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=(), fetch=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if fetch == "one":
                return cursor.fetchone()
            if fetch == "all":
                return cursor.fetchall()
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Erreur SQL: {query} avec params {params} -> {e}", exc_info=True)
            raise e

    def run_migrations(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS db_version (version INTEGER PRIMARY KEY)")
        current_version_row = self.execute_query("SELECT version FROM db_version", fetch="one")
        current_version = current_version_row['version'] if current_version_row else 0
        
        migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
        if not os.path.exists(migrations_path): return

        migrations = sorted([f for f in os.listdir(migrations_path) if f.endswith('.sql')])
        
        for migration_file in migrations:
            match = re.match(r'(\d+)_.*\.sql', migration_file)
            if match:
                version = int(match.group(1))
                if version > current_version:
                    logging.info(f"Tentative d'application de la migration : {migration_file}")
                    script_path = os.path.join(migrations_path, migration_file)
                    with open(script_path, 'r', encoding='utf-8') as f:
                        script = f.read()
                    
                    sql_commands = [cmd.strip() for cmd in script.split(';') if cmd.strip()]
                    try:
                        for command in sql_commands:
                            try:
                                self.conn.cursor().execute(command)
                            except sqlite3.OperationalError as e:
                                if "duplicate column name" in str(e) or "already exists" in str(e) or "no such column" in str(e):
                                    logging.warning(f"Commande ignorée (potentiellement déjà appliquée) : {command.splitlines()[0]}...")
                                else: raise e
                        
                        self.execute_query("REPLACE INTO db_version (version) VALUES (?)", (version,))
                        self.conn.commit()
                        logging.info(f"Migration {migration_file} appliquée avec succès.")
                    except sqlite3.Error as e:
                        logging.critical(f"ÉCHEC CRITIQUE de la migration {migration_file}: {e}")
                        self.conn.rollback(); raise e

    def get_annee_exercice(self):
        result = self.execute_query("SELECT config_value FROM system_config WHERE config_key = 'annee_exercice'", fetch="one")
        if result: return int(result['config_value'])
        current_year = datetime.now().year; self.set_annee_exercice(current_year); return current_year

    def set_annee_exercice(self, annee):
        self.execute_query("REPLACE INTO system_config (config_key, config_value) VALUES ('annee_exercice', ?)", (str(annee),))

    def get_soldes_by_status(self, statut):
        query = "SELECT s.*, a.nom, a.prenom FROM soldes_annuels s JOIN agents a ON s.agent_id = a.id WHERE s.statut = ? AND s.solde > 0 ORDER BY a.nom, s.annee"
        return self.execute_query(query, (str(statut),), fetch="all")

    def apurer_soldes_by_ids(self, solde_ids):
        if not solde_ids: return
        self.execute_query(f"UPDATE soldes_annuels SET solde = 0 WHERE id IN ({','.join('?' for _ in solde_ids)})", solde_ids)
    
    def update_solde_by_id(self, solde_id, new_value):
        self.execute_query("UPDATE soldes_annuels SET solde = ? WHERE id = ?", (new_value, solde_id))

    # --- MÉTHODE AJOUTÉE ---
    def create_solde_annuel(self, agent_id, annee, solde_valeur, statut):
        """
        Crée une nouvelle entrée de solde annuel pour un agent.
        """
        query = "INSERT INTO soldes_annuels (agent_id, annee, solde, statut) VALUES (?, ?, ?, ?)"
        # On s'assure que le statut est bien une chaîne de caractères pour la BDD
        params = (agent_id, annee, solde_valeur, str(statut))
        return self.execute_query(query, params)
    # --- FIN DE L'AJOUT ---

    def get_agents(self, statut='Actif', term=None, limit=None, offset=None, exclude_id=None):
        q = "SELECT id, nom, prenom, ppr, cadre, statut_agent FROM agents"
        p = [statut]
        c = ["statut_agent = ?"]
        if term: t = f"%{term.lower()}%"; c.append("(LOWER(nom) LIKE ? OR LOWER(prenom) LIKE ? OR LOWER(ppr) LIKE ?)"); p.extend([t, t, t])
        if exclude_id is not None: c.append("id != ?"); p.append(exclude_id)
        q += " WHERE " + " AND ".join(c) + " ORDER BY nom, prenom"
        if limit is not None: q += " LIMIT ? OFFSET ?"; p.extend([limit, offset])
        
        agents_rows = self.execute_query(q, tuple(p), fetch="all")
        if not agents_rows: return []
        
        agents = [Agent.from_db_row(r) for r in agents_rows]
        agent_ids = [agent.id for agent in agents]
        if not agent_ids: return agents
        
        soldes_query = f"SELECT * FROM soldes_annuels WHERE agent_id IN ({','.join('?' for _ in agent_ids)})"
        all_soldes_rows = self.execute_query(soldes_query, agent_ids, fetch="all")
        
        soldes_map = defaultdict(list)
        for row in all_soldes_rows: soldes_map[row['agent_id']].append(SoldeAnnuel.from_db_row(row))
        for agent in agents: agent.soldes_annuels = soldes_map.get(agent.id, [])
        return agents

    def get_agent_by_id(self, agent_id):
        query = "SELECT * FROM agents WHERE id=?"
        row_dict = self.execute_query(query, (agent_id,), fetch="one")
        if not row_dict: return None
        agent = Agent.from_db_row(row_dict)
        
        soldes_rows = self.execute_query("SELECT * FROM soldes_annuels WHERE agent_id = ?", (agent.id,), fetch="all")
        agent.soldes_annuels = [SoldeAnnuel.from_db_row(r) for r in soldes_rows]
        history_rows = self.execute_query("SELECT * FROM historique_carrieres WHERE agent_id = ? ORDER BY date_evenement DESC", (agent.id,), fetch="all")
        agent.historique = [HistoriqueCarriere.from_db_row(h_row) for h_row in history_rows]
        if agent.cadre and "Résident" in agent.cadre:
            profile_row = self.execute_query("SELECT * FROM profil_medecin_resident WHERE agent_id = ?", (agent.id,), fetch="one")
            if profile_row: agent.profil = ProfilMedecinResident.from_db_row(profile_row)
        return agent

    def get_agents_count(self, statut='Actif', term=None):
        q = "SELECT COUNT(*) as count FROM agents"
        p = [statut]
        c = ["statut_agent = ?"]
        if term: t = f"%{term.lower()}%"; c.append("(LOWER(nom) LIKE ? OR LOWER(prenom) LIKE ? OR LOWER(ppr) LIKE ?)"); p.extend([t, t, t])
        q += " WHERE " + " AND ".join(c)
        return self.execute_query(q, tuple(p), fetch="one")['count']

    def save_agent(self, agent_data, is_modification=False):
        if isinstance(agent_data.get('date_prise_service'), datetime): agent_data['date_prise_service'] = agent_data['date_prise_service'].strftime('%Y-%m-%d')
        if isinstance(agent_data.get('date_cessation_service'), datetime): agent_data['date_cessation_service'] = agent_data['date_cessation_service'].strftime('%Y-%m-%d')
        
        common_fields = ['nom', 'prenom', 'ppr', 'cadre', 'sexe', 'cnie', 'nom_arabe', 'prenom_arabe', 'date_prise_service', 'date_cessation_service', 'statut_hierarchique', 'specialite', 'service_affectation', 'telephone_pro', 'email_pro', 'type_recrutement', 'motif_cessation_service']
        
        if is_modification:
            fields_for_update = ", ".join([f"{field}=?" for field in common_fields])
            query = f"UPDATE agents SET {fields_for_update} WHERE id=?"
            params = tuple(agent_data.get(k) for k in common_fields) + (agent_data.get('id'),)
            self.execute_query(query, params)
            return agent_data.get('id')
        else:
            fields_for_insert = ", ".join(common_fields)
            placeholders = ", ".join(['?'] * len(common_fields))
            query = f"INSERT INTO agents ({fields_for_insert}) VALUES ({placeholders})"
            params = tuple(agent_data.get(k) for k in common_fields)
            return self.execute_query(query, params)

    def supprimer_agent(self, agent_id):
        return self.execute_query("DELETE FROM agents WHERE id=?", (agent_id,))
    
    def supprimer_agents_definitivement(self, agent_ids):
        """Supprime définitivement une liste d'agents de la base de données."""
        if not agent_ids:
            return
        placeholders = ','.join('?' for _ in agent_ids)
        query = f"DELETE FROM agents WHERE id IN ({placeholders})"
        self.execute_query(query, agent_ids)

    def update_agents_status(self, agent_ids, statut):
        if not agent_ids: return
        placeholders = ','.join('?' for _ in agent_ids)
        query = f"UPDATE agents SET statut_agent = ? WHERE id IN ({placeholders})"
        self.execute_query(query, [statut] + agent_ids)

    def ajouter_conge(self, conge_model):
        return self.execute_query("INSERT INTO conges (agent_id, type_conge, justif, interim_id, date_debut, date_fin, jours_pris) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (conge_model.agent_id, conge_model.type_conge, conge_model.justif, conge_model.interim_id, conge_model.date_debut, conge_model.date_fin, conge_model.jours_pris))

    def supprimer_conge(self, conge_id):
        cert = self.execute_query("SELECT chemin_fichier FROM certificats_medicaux WHERE conge_id = ?", (conge_id,), fetch="one")
        if cert and cert['chemin_fichier'] and os.path.exists(cert['chemin_fichier']):
            try: os.remove(cert['chemin_fichier'])
            except OSError as e: logging.error(f"Erreur suppression certificat pour conge_id {conge_id}: {e}")
        self.execute_query("DELETE FROM conges WHERE id=?", (conge_id,))
        return True

    def get_conges(self, agent_id=None):
        q, p = "SELECT * FROM conges", ()
        if agent_id: q += " WHERE agent_id=? ORDER BY date_debut DESC"; p = (agent_id,)
        else: q += " ORDER BY date_debut DESC"
        return [Conge.from_db_row(r) for r in self.execute_query(q, p, fetch="all") if r]

    def get_conge_by_id(self, conge_id):
        r = self.execute_query("SELECT * FROM conges WHERE id=?", (conge_id,), fetch="one")
        return Conge.from_db_row(r) if r else None
        
    def get_overlapping_leaves(self, agent_id, start_date, end_date, conge_id_exclu=None):
        q = "SELECT * FROM conges WHERE agent_id=? AND date_fin >= ? AND date_debut <= ? AND statut = 'Actif'"
        p = [agent_id, start_date, end_date]
        if conge_id_exclu: q += " AND id != ?"; p.append(conge_id_exclu)
        return [Conge.from_db_row(r) for r in self.execute_query(q, tuple(p), fetch="all") if r]

    def get_holidays_for_year(self, year):
        return self.execute_query("SELECT date, nom, type FROM jours_feries_personnalises WHERE strftime('%Y', date) = ? ORDER BY date", (str(year),), fetch="all")
        
    def get_certificat_for_conge(self, conge_id):
        return self.execute_query("SELECT * FROM certificats_medicaux WHERE conge_id = ?", (conge_id,), fetch="one")
    
    def add_certificat(self, conge_id, file_path):
        query = "REPLACE INTO certificats_medicaux (id, conge_id, chemin_fichier) VALUES ((SELECT id FROM certificats_medicaux WHERE conge_id=?), ?, ?)"
        self.execute_query(query, (conge_id, conge_id, file_path))

    def add_or_update_holiday(self, date_sql, name, h_type):
        self.execute_query("REPLACE INTO jours_feries_personnalises (date, nom, type) VALUES (?, ?, ?)", (date_sql, name, h_type))
        return True

    def add_holiday(self, date_sql, name, h_type):
        try:
            self.execute_query("INSERT INTO jours_feries_personnalises (date, nom, type) VALUES (?, ?, ?)", (date_sql, name, h_type))
            return True
        except sqlite3.IntegrityError: return False

    def delete_holiday(self, date_sql):
        self.execute_query("DELETE FROM jours_feries_personnalises WHERE date = ?", (date_sql,)); return True
        
    def get_sick_leaves_by_status(self, status='manquant', search_term=None):
        base = "SELECT a.nom, a.prenom, a.ppr, c.date_debut, c.date_fin, c.jours_pris, c.id FROM conges c JOIN agents a ON c.agent_id = a.id"
        clauses = ["c.type_conge = 'Congé de maladie'", "c.statut = 'Actif'"]
        params = []
        if status == 'manquant': join = "LEFT JOIN certificats_medicaux cm ON c.id = cm.conge_id"; clauses.append("cm.id IS NULL")
        elif status == 'justifie': join = "INNER JOIN certificats_medicaux cm ON c.id = cm.conge_id"
        else: join = "LEFT JOIN certificats_medicaux cm ON c.id = cm.conge_id"
        if search_term:
            term = f"%{search_term.lower()}%"
            clauses.append("(LOWER(a.nom) LIKE ? OR LOWER(a.prenom) LIKE ? OR LOWER(a.ppr) LIKE ?)")
            params.extend([term, term, term])
        return self.execute_query(f"{base} {join} WHERE {' AND '.join(clauses)} ORDER BY c.date_debut DESC", tuple(params), fetch="all")
    
    def get_agents_on_leave_today(self):
        query = """
            SELECT a.nom, a.prenom, a.ppr, c.type_conge, c.date_fin
            FROM conges c JOIN agents a ON c.agent_id = a.id
            WHERE a.statut_agent = 'Actif' AND c.statut = 'Actif' AND date('now', 'localtime') BETWEEN date(c.date_debut) AND date(c.date_fin)
            ORDER BY a.nom, a.prenom"""
        return self.execute_query(query, fetch="all")
        
    def add_history_event(self, event_data):
        if isinstance(event_data.get('date_evenement'), datetime): event_data['date_evenement'] = event_data['date_evenement'].strftime('%Y-%m-%d')
        query = """INSERT INTO historique_carrieres (agent_id, date_evenement, type_evenement, service_affectation, specialite, centre_formation, details) VALUES (?, ?, ?, ?, ?, ?, ?)"""
        params = tuple(event_data.get(k) for k in ['agent_id', 'date_evenement', 'type_evenement', 'service_affectation', 'specialite', 'centre_formation', 'details'])
        return self.execute_query(query, params)

    def save_resident_profile(self, profile_data):
        if isinstance(profile_data.get('date_fin_formation'), datetime): profile_data['date_fin_formation'] = profile_data['date_fin_formation'].strftime('%Y-%m-%d')
        query = """REPLACE INTO profil_medecin_resident (id, agent_id, type_residanat, statut_contrat, date_fin_formation) VALUES ((SELECT id FROM profil_medecin_resident WHERE agent_id=?), ?, ?, ?, ?)"""
        params = (profile_data.get('agent_id'), profile_data.get('agent_id'), profile_data.get('type_residanat'), profile_data.get('statut_contrat'), profile_data.get('date_fin_formation'))
        return self.execute_query(query, params)
        
    def get_db_path(self):
        return self.db_file
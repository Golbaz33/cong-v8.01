# Fichier : core/conges/manager.py
# VERSION FINALE COMPLÈTE - Intègre la logique avancée de gestion des chevauchements et la correction des transactions.

import sqlite3
import logging
import os
import shutil
from datetime import datetime, timedelta
from tkinter import messagebox

from utils.date_utils import get_holidays_set_for_period, jours_ouvres, validate_date, format_date_for_display
from utils.config_loader import CONFIG
from db.models import Conge, SoldeAnnuel
from core.constants import SoldeStatus, SplitConfirmationRequired, ReplaceConfirmationRequired, TrimConfirmationRequired

class CongeManager:
    def __init__(self, db_manager, certificats_dir):
        self.db = db_manager
        self.certificats_dir = certificats_dir
        os.makedirs(self.certificats_dir, exist_ok=True)

    # --- Gestion des Agents ---
    def archive_agents(self, agent_ids):
        if not isinstance(agent_ids, list): agent_ids = [agent_ids]
        return self.db.update_agents_status(agent_ids, 'Archivé')

    def restore_agents(self, agent_ids):
        if not isinstance(agent_ids, list): agent_ids = [agent_ids]
        return self.db.update_agents_status(agent_ids, 'Actif')
        
    def delete_agents_permanently(self, agent_ids):
        if not isinstance(agent_ids, list): agent_ids = [agent_ids]
        return self.db.supprimer_agents_definitivement(agent_ids)

    # --- Tâches Administratives ---
    def get_annee_exercice(self):
        return self.db.get_annee_exercice()

    def effectuer_glissement_annuel(self):
        self.db.conn.execute('BEGIN TRANSACTION')
        try:
            annee_actuelle = self.get_annee_exercice()
            nouvelle_annee = annee_actuelle + 1
            annee_a_expirer = annee_actuelle - 2
            solde_initial = float(CONFIG['conges'].get('solde_annuel_par_defaut', 22.0))
            all_agents = self.get_all_agents(statut='Actif')
            for agent in all_agents:
                self.db.create_solde_annuel(agent.id, nouvelle_annee, solde_initial, SoldeStatus.ACTIF)
                self.db.execute_query("UPDATE soldes_annuels SET statut = ? WHERE agent_id = ? AND annee = ?",
                                      (SoldeStatus.EXPIRE, agent.id, annee_a_expirer))
            self.db.set_annee_exercice(nouvelle_annee)
            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            self.db.conn.rollback(); logging.error(f"Échec glissement: {e}", exc_info=True); raise e

    def get_soldes_expires(self):
        return self.db.get_soldes_by_status(SoldeStatus.EXPIRE)

    def apurer_soldes(self, solde_ids):
        return self.db.apurer_soldes_by_ids(solde_ids)
    
    def save_manual_soldes(self, agent_id, updates, creations):
        self.db.conn.execute('BEGIN TRANSACTION')
        try:
            for solde_id, new_value in updates.items(): self.db.update_solde_by_id(solde_id, new_value)
            if creations:
                annee_exercice = self.get_annee_exercice()
                for year, value in creations.items():
                    statut = SoldeStatus.EXPIRE if year < annee_exercice - 2 else SoldeStatus.ACTIF
                    self.db.create_solde_annuel(agent_id, year, value, statut)
            self.db.conn.commit()
            return True
        except sqlite3.Error as e:
            self.db.conn.rollback(); logging.error(f"Échec MàJ manuelle soldes: {e}", exc_info=True); raise e

    # --- Getters ---
    def get_all_agents(self, statut='Actif', **kwargs):
        return self.db.get_agents(statut=statut, **kwargs)

    def get_agents_count(self, statut='Actif', term=None):
        return self.db.get_agents_count(statut=statut, term=term)

    def get_agent_by_id(self, agent_id):
        return self.db.get_agent_by_id(agent_id)

    def get_all_conges(self):
        return self.db.get_conges()

    def get_conges_for_agent(self, agent_id):
        return self.db.get_conges(agent_id=agent_id)

    def get_conge_by_id(self, conge_id):
        return self.db.get_conge_by_id(conge_id)

    def get_certificat_for_conge(self, conge_id):
        return self.db.get_certificat_for_conge(conge_id)

    def get_holidays_for_year(self, year):
        return self.db.get_holidays_for_year(year)

    def get_sick_leaves_by_status(self, status, search_term=None):
        return self.db.get_sick_leaves_by_status(status, search_term)

    def get_holidays_set_for_period(self, start_year, end_year):
        return get_holidays_set_for_period(self.db, start_year, end_year)

    def get_agents_on_leave_today(self):
        return self.db.get_agents_on_leave_today()

    def add_holiday(self, date_sql, name, h_type):
        return self.db.add_holiday(date_sql, name, h_type)

    def delete_holiday(self, date_sql):
        return self.db.delete_holiday(date_sql)

    def add_or_update_holiday(self, date_sql, name, h_type):
        return self.db.add_or_update_holiday(date_sql, name, h_type)

    # --- Logique des Soldes ---
    def _debiter_solde(self, agent_id, jours_a_prendre):
        if jours_a_prendre <= 0: return
        agent = self.get_agent_by_id(agent_id)
        if agent.get_solde_total_actif() < jours_a_prendre:
            raise ValueError(f"Solde total insuffisant ({agent.get_solde_total_actif()}j) pour décompter {jours_a_prendre}j.")
        
        soldes_actifs = sorted([s for s in agent.soldes_annuels if s.statut == SoldeStatus.ACTIF], key=lambda s: s.annee)
        jours_restants_a_debiter = float(jours_a_prendre)
        for solde_annuel in soldes_actifs:
            if jours_restants_a_debiter < 0.001: break
            jours_pris = min(float(solde_annuel.solde), jours_restants_a_debiter)
            if jours_pris > 0:
                self.db.update_solde_by_id(solde_annuel.id, solde_annuel.solde - jours_pris)
                jours_restants_a_debiter -= jours_pris
        if jours_restants_a_debiter > 0.001:
            raise sqlite3.Error("Incohérence de solde détectée lors du débit.")

    def _crediter_solde(self, agent_id, jours_a_rendre):
        if jours_a_rendre <= 0: return
        agent = self.get_agent_by_id(agent_id)
        soldes_actifs = sorted([s for s in agent.soldes_annuels if s.statut == SoldeStatus.ACTIF], key=lambda s: s.annee, reverse=True)
        
        jours_restants_a_rendre = float(jours_a_rendre)
        solde_max = float(CONFIG['conges'].get('solde_annuel_par_defaut', 22.0))

        for solde_annuel in soldes_actifs:
            if jours_restants_a_rendre < 0.001: break
            jours_a_ajouter = min(jours_restants_a_rendre, solde_max - solde_annuel.solde)
            if jours_a_ajouter > 0:
                self.db.update_solde_by_id(solde_annuel.id, solde_annuel.solde + jours_a_ajouter)
                jours_restants_a_rendre -= jours_a_ajouter

        if jours_restants_a_rendre > 0.001 and soldes_actifs:
            solde_plus_recent = soldes_actifs[0]
            self.db.update_solde_by_id(solde_plus_recent.id, solde_plus_recent.solde + jours_restants_a_rendre)

    def get_deduction_details(self, agent_id, jours_a_prendre):
        if jours_a_prendre <= 0: return {}
        agent = self.get_agent_by_id(agent_id)
        if not agent: return {}
        
        jours_restants = float(jours_a_prendre)
        details = {}
        soldes_tries = sorted([s for s in agent.soldes_annuels if s.statut == SoldeStatus.ACTIF], key=lambda s: s.annee)

        for solde in soldes_tries:
            if jours_restants < 0.001: break
            jours_pris = min(solde.solde, jours_restants)
            if jours_pris > 0:
                details[solde.annee] = jours_pris
                jours_restants -= jours_pris
        return details

    # --- Gestion Complète des Agents et Congés ---

    def save_full_agent(self, agent_data, is_modification=False):
        try:
            agent_id = self.db.save_agent(agent_data, is_modification)
            if not agent_id:
                raise Exception("La sauvegarde des infos de base de l'agent a échoué.")
            if not is_modification and 'soldes' in agent_data:
                for annee, solde_val in agent_data['soldes'].items():
                    if solde_val > 0:
                        self.db.create_solde_annuel(agent_id, annee, solde_val, SoldeStatus.ACTIF)
            cadre = agent_data.get('cadre', '').lower()
            if "résident" in cadre:
                profile_data = { 'agent_id': agent_id, 'type_residanat': agent_data.get('type_residanat'), 'statut_contrat': agent_data.get('statut_contrat_resident'), 'date_fin_formation': agent_data.get('date_fin_formation') }
                self.db.save_resident_profile(profile_data)
            return True
        except Exception as e:
            logging.error(f"Échec sauvegarde complète agent : {e}", exc_info=True); raise e

    def handle_conge_submission(self, form_data, is_modification):
        start_date = validate_date(form_data['date_debut'])
        end_date = validate_date(form_data['date_fin'])
        nouveau_type = form_data['type_conge']

        if not all([nouveau_type, start_date, end_date]) or end_date < start_date:
            raise ValueError("Dates ou type de congé invalides.")

        conge_id_exclu = form_data.get('conge_id') if is_modification else None
        overlaps = self.db.get_overlapping_leaves(form_data['agent_id'], start_date, end_date, conge_id_exclu)
        
        if not overlaps:
            self.db.conn.execute('BEGIN TRANSACTION')
            try:
                self._execute_simple_save(form_data, is_modification)
                self.db.conn.commit()
                return True
            except (ValueError, sqlite3.Error) as e:
                self.db.conn.rollback(); raise e
        
        if len(overlaps) == 1:
            conflit = overlaps[0]
            if conflit.type_conge == "Congé annuel" and nouveau_type == "Congé annuel":
                raise ValueError("Un congé annuel ne peut pas chevaucher un autre congé annuel.")
            
            types_prioritaires = ["Congé de maladie", "Congé de maternité"]
            types_prioritaires_split = types_prioritaires + ["Congé de paternité"]

            if conflit.type_conge == "Congé annuel":
                if nouveau_type in types_prioritaires_split and start_date > conflit.date_debut and end_date < conflit.date_fin:
                    msg = f"Ce {nouveau_type.lower()} chevauche un congé annuel. Voulez-vous diviser le congé annuel en deux ?"
                    raise SplitConfirmationRequired(msg, form_data, conflit)
                if nouveau_type == "Congé de maladie" and start_date == conflit.date_debut and end_date == conflit.date_fin:
                    msg = "Un congé annuel existe déjà sur ces dates. Voulez-vous le remplacer par ce congé maladie ?"
                    raise ReplaceConfirmationRequired(msg, form_data, conflit)
                if nouveau_type in types_prioritaires and start_date <= conflit.date_debut and end_date >= conflit.date_fin:
                    msg = "Ce nouveau congé englobe un congé annuel existant. Voulez-vous remplacer l'ancien congé par celui-ci ?"
                    raise ReplaceConfirmationRequired(msg, form_data, conflit)
                if nouveau_type in types_prioritaires and start_date > conflit.date_debut and start_date <= conflit.date_fin:
                    msg = "Ce nouveau congé chevauche la fin d'un congé annuel. Voulez-vous ajuster le congé annuel existant ?"
                    raise TrimConfirmationRequired(msg, form_data, conflit, 'end')
                if nouveau_type in types_prioritaires and end_date >= conflit.date_debut and end_date < conflit.date_fin:
                    msg = "Ce nouveau congé chevauche le début d'un congé annuel. Voulez-vous ajuster le congé annuel existant ?"
                    raise TrimConfirmationRequired(msg, form_data, conflit, 'start')

        conflit_bloquant = overlaps[0]
        msg_erreur = (
            "Chevauchement de congés détecté.\n\n"
            f"- Type existant : {conflit_bloquant.type_conge}\n"
            f"- Période : du {format_date_for_display(conflit_bloquant.date_debut)} au {format_date_for_display(conflit_bloquant.date_fin)}"
        )
        raise ValueError(msg_erreur)

    def _execute_simple_save(self, form_data, is_modification):
        agent_id, jours_pris, type_conge = form_data['agent_id'], form_data['jours_pris'], form_data['type_conge']
        
        if is_modification:
            old_conge = self.get_conge_by_id(form_data['conge_id'])
            if old_conge and old_conge.type_conge in CONFIG['conges']['types_decompte_solde']:
                self._crediter_solde(old_conge.agent_id, old_conge.jours_pris)
            self.db.supprimer_conge(form_data['conge_id'])

        if type_conge in CONFIG['conges']['types_decompte_solde']:
            self._debiter_solde(agent_id, jours_pris)

        conge_model = Conge(id=None, agent_id=agent_id, type_conge=type_conge, justif=form_data.get('justif'), interim_id=form_data.get('interim_id'), date_debut=validate_date(form_data['date_debut']), date_fin=validate_date(form_data['date_fin']), jours_pris=jours_pris)
        new_conge_id = self.db.ajouter_conge(conge_model)
        
        if new_conge_id and type_conge == "Congé de maladie": 
            self._handle_certificat_save(form_data, new_conge_id)
        return True

    def _create_and_save_leave(self, form_data, leave_type, start_date, end_date, days_to_debit=None):
        holidays_set = self.get_holidays_set_for_period(start_date.year, end_date.year)
        
        if days_to_debit is None:
            if leave_type == "Congé annuel":
                days_to_debit = jours_ouvres(start_date, end_date, holidays_set)
            else:
                days_to_debit = (end_date - start_date).days + 1
        
        if days_to_debit > 0:
            model = Conge(id=None, agent_id=form_data['agent_id'], type_conge=leave_type, justif=form_data.get('justif'), interim_id=form_data.get('interim_id'), date_debut=start_date, date_fin=end_date, jours_pris=days_to_debit)
            new_id = self.db.ajouter_conge(model)
            if leave_type in CONFIG['conges']['types_decompte_solde']:
                self._debiter_solde(form_data['agent_id'], days_to_debit)
            return new_id
        return None

    def execute_split_leave(self, form_data, old_leave):
        self.db.conn.execute('BEGIN TRANSACTION')
        try:
            self.db.supprimer_conge(old_leave.id)
            self._crediter_solde(old_leave.agent_id, old_leave.jours_pris)
            new_start = validate_date(form_data['date_debut'])
            new_end = validate_date(form_data['date_fin'])
            new_leave_id = self._create_and_save_leave(form_data, form_data['type_conge'], new_start, new_end, form_data['jours_pris'])
            if new_leave_id and form_data['type_conge'] == "Congé de maladie":
                self._handle_certificat_save(form_data, new_leave_id)
            part1_end = new_start - timedelta(days=1)
            self._create_and_save_leave(form_data, "Congé annuel", old_leave.date_debut, part1_end)
            part2_start = new_end + timedelta(days=1)
            self._create_and_save_leave(form_data, "Congé annuel", part2_start, old_leave.date_fin)
            self.db.conn.commit()
            return True
        except Exception as e:
            self.db.conn.rollback(); raise e

    def execute_replace_leave(self, form_data, old_leave):
        self.db.conn.execute('BEGIN TRANSACTION')
        try:
            self.db.supprimer_conge(old_leave.id)
            self._crediter_solde(old_leave.agent_id, old_leave.jours_pris)
            self._execute_simple_save(form_data, is_modification=False)
            self.db.conn.commit()
            return True
        except Exception as e:
            self.db.conn.rollback(); raise e

    def execute_trim_leave(self, form_data, old_leave, trim_side):
        self.db.conn.execute('BEGIN TRANSACTION')
        try:
            self.db.supprimer_conge(old_leave.id)
            self._crediter_solde(old_leave.agent_id, old_leave.jours_pris)
            self._execute_simple_save(form_data, is_modification=False)
            
            new_start = validate_date(form_data['date_debut'])
            new_end = validate_date(form_data['date_fin'])
            if trim_side == 'end':
                new_annual_end = new_start - timedelta(days=1)
                self._create_and_save_leave(form_data, "Congé annuel", old_leave.date_debut, new_annual_end)
            elif trim_side == 'start':
                new_annual_start = new_end + timedelta(days=1)
                self._create_and_save_leave(form_data, "Congé annuel", new_annual_start, old_leave.date_fin)

            self.db.conn.commit()
            return True
        except Exception as e:
            self.db.conn.rollback(); raise e

    def delete_conge(self, conge_id):
        conge = self.get_conge_by_id(conge_id)
        if not conge: raise ValueError("Congé introuvable.")
        self.db.conn.execute('BEGIN TRANSACTION')
        try:
            if conge.type_conge in CONFIG['conges']['types_decompte_solde']:
                self._crediter_solde(conge.agent_id, conge.jours_pris)
            self.db.supprimer_conge(conge_id)
            self.db.conn.commit()
            return True
        except (ValueError, sqlite3.Error) as e:
            self.db.conn.rollback(); raise e

    def _handle_certificat_save(self, form_data, conge_id):
        source_path = form_data.get('cert_path')
        if not source_path or not os.path.exists(source_path): return
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            agent_ppr = form_data.get('agent_ppr', 'unknown')
            _, extension = os.path.splitext(source_path)
            safe_filename = f"{timestamp}_{agent_ppr}_{conge_id}{extension}"
            destination_path = os.path.join(self.certificats_dir, safe_filename)
            shutil.copy2(source_path, destination_path)
            self.db.add_certificat(conge_id, destination_path)
        except Exception as e:
            logging.error(f"Échec sauvegarde certif: {e}", exc_info=True)
            messagebox.showwarning("Erreur Justificatif", f"Congé créé, mais sauvegarde justificatif échouée.\nErreur: {e}")

    def find_inconsistent_annual_leaves(self, year):
        inconsistencies = []
        holidays_set = self.get_holidays_set_for_period(year, year + 1)
        all_conges = self.get_all_conges()
        leaves_in_year = [c for c in all_conges if c.type_conge == "Congé annuel" and c.date_debut.year == year and c.statut == 'Actif']
        for conge in leaves_in_year:
            recalculated_days = jours_ouvres(conge.date_debut, conge.date_fin, holidays_set)
            if conge.jours_pris != recalculated_days:
                inconsistencies.append((conge, recalculated_days))
        return inconsistencies
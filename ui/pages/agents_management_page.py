# Fichier : ui/pages/agents_management_page.py
# VERSION FINALE - Mise à jour de la configuration des catégories d'agents.

import tkinter as tk
from tkinter import ttk, messagebox

from utils.config_loader import CONFIG
from ui.ui_utils import treeview_sort_column
from ui.forms.agent_detail_form import AgentDetailForm
from ui.agent_synthesis_window import AgentSynthesisWindow
from utils.date_utils import format_date_for_display

class AgentsManagementPage(ttk.Frame):
    def __init__(self, parent, main_app, manager):
        super().__init__(parent)
        self.main_app = main_app
        self.manager = manager
        
        self.current_category = "Tout le personnel"
        
        # --- NOUVELLE CONFIGURATION DES CATÉGORIES ---
        self.categories_config = {
            "Tout le personnel": {
                "keywords": [], # Pas de mot-clé, affichera tout le monde
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("PPR", lambda a: a.ppr),
                    ("Cadre/Grade", lambda a: a.cadre),
                    ("Service d'affectation", lambda a: a.service_affectation),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            },
            "Professeurs": {
                "keywords": ["Professeur"],
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("PPR", lambda a: a.ppr),
                    ("Cadre/Grade", lambda a: a.cadre), ("Spécialité", lambda a: a.specialite),
                    ("Service d'affectation", lambda a: a.service_affectation),
                    ("Date prise de service", lambda a: format_date_for_display(a.date_prise_service)),
                    ("Statut hiérarchique", lambda a: a.statut_hierarchique),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            },
            "Médecins et pharmaciens": {
                "keywords": ["Médecin", "Pharmacien"],
                "exclude_keywords": ["Résident", "Interne"], # Pour ne pas inclure résidents et internes
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("PPR", lambda a: a.ppr),
                    ("Cadre/Grade", lambda a: a.cadre), ("Spécialité", lambda a: a.specialite),
                    ("Service d'affectation", lambda a: a.service_affectation),
                    ("Date prise de service", lambda a: format_date_for_display(a.date_prise_service)),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            },
            "Médecins Résidents": {
                "keywords": ["Résident"],
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("PPR", lambda a: a.ppr),
                    ("Cadre/Grade", lambda a: a.cadre),
                    ("Statut contrat", lambda a: a.profil.statut_contrat if a.profil else ''),
                    ("Spécialité", lambda a: a.specialite),
                    ("Date prise de service", lambda a: format_date_for_display(a.date_prise_service)),
                    ("Date de fin de formation", lambda a: format_date_for_display(a.profil.date_fin_formation) if a.profil else ''),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            },
            "Médecins Internes": {
                "keywords": ["Interne"],
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("Cadre/Grade", lambda a: a.cadre),
                    ("Date prise de service", lambda a: format_date_for_display(a.date_prise_service)),
                    ("Site de stage 1", lambda a: a.profil.site_stage_1 if a.profil else ''),
                    ("Site de stage 2", lambda a: a.profil.site_stage_2 if a.profil else ''),
                    ("Prolongation", lambda a: a.profil.prolongation if a.profil else ''),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            },
            "Infirmiers et Techniciens de santé": {
                "keywords": ["Infirmier", "Technicien de santé", "Rééducateur", "Sage-femme", "Assistant médico-social"],
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("PPR", lambda a: a.ppr),
                    ("Cadre/Grade", lambda a: a.cadre), ("Spécialité", lambda a: a.specialite),
                    ("Date prise de service", lambda a: format_date_for_display(a.date_prise_service)),
                    ("Statut hiérarchique", lambda a: a.statut_hierarchique),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            },
            "Administration": {
                "keywords": ["Ingénieur", "Technicien", "Administrateur", "Adjoint"],
                "exclude_keywords": ["Technicien de santé"], # Pour ne pas inclure les techniciens de santé
                "columns": [
                    ("Nom", lambda a: a.nom), ("Prénom", lambda a: a.prenom), ("PPR", lambda a: a.ppr),
                    ("Cadre/Grade", lambda a: a.cadre),
                    ("Service d'affectation", lambda a: a.service_affectation),
                    ("Date prise de service", lambda a: format_date_for_display(a.date_prise_service)),
                    ("Solde Total", lambda a: f"{a.get_solde_total_actif():.1f} j")
                ]
            }
        }

        self._create_widgets()
        self.category_panel.select_first_category()

    def _create_widgets(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        self.category_panel = CategoryPanel(main_pane, list(self.categories_config.keys()), self._on_category_select)
        main_pane.add(self.category_panel, weight=1)

        agents_container = ttk.Frame(main_pane)
        main_pane.add(agents_container, weight=4)
        
        search_frame = ttk.Frame(agents_container)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_all())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.list_agents = ttk.Treeview(agents_container, show="headings", selectmode="extended")
        self.list_agents.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.list_agents.bind("<Double-1>", self._on_double_click)
        
        actions_frame = ttk.Frame(agents_container)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(actions_frame, text="Fiche / Modifier", command=self._open_agent_profile).pack(side=tk.LEFT)
        ttk.Button(actions_frame, text="Ajouter un nouvel agent", command=self._add_agent).pack(side=tk.LEFT, padx=5)

    def _on_category_select(self, category_name):
        self.current_category = category_name
        self.refresh_all()
        
    def _setup_agent_list_columns(self):
        if not self.current_category: return
        
        column_defs = self.categories_config[self.current_category]["columns"]
        column_names = [name for name, _ in column_defs]
        
        self.list_agents.config(columns=column_names)
        for item in self.list_agents.get_children():
            self.list_agents.delete(item)
            
        for col_name in column_names:
            self.list_agents.heading(col_name, text=col_name, command=lambda c=col_name: treeview_sort_column(self.list_agents, c, False))
            self.list_agents.column(col_name, width=120, anchor='w')

    def refresh_all(self, agent_to_select_id=None):
        self._setup_agent_list_columns()
        if not self.current_category: return
        
        category_conf = self.categories_config[self.current_category]
        keywords = category_conf.get("keywords", [])
        exclude_keywords = category_conf.get("exclude_keywords", [])
        
        all_agents = self.manager.get_all_agents(statut='Actif', term=self.search_var.get() or None)
        
        agents_in_category = []
        if not keywords: # Cas "Tout le personnel"
            agents_in_category = all_agents
        else:
            for agent in all_agents:
                cadre_lower = agent.cadre.lower()
                # Doit contenir un mot-clé positif
                if any(k.lower() in cadre_lower for k in keywords):
                    # Ne doit contenir aucun mot-clé d'exclusion
                    if not any(ek.lower() in cadre_lower for ek in exclude_keywords):
                        agents_in_category.append(agent)
        
        for agent in agents_in_category:
            values = self._get_agent_values(agent)
            self.list_agents.insert("", "end", values=values, iid=agent.id)
            
        if agent_to_select_id:
            try:
                self.list_agents.selection_set(str(agent_to_select_id))
                self.list_agents.focus(str(agent_to_select_id))
                self.list_agents.see(str(agent_to_select_id))
            except tk.TclError:
                pass

    def _get_agent_values(self, agent):
        if not self.current_category: return []
        
        column_defs = self.categories_config[self.current_category]["columns"]
        return [accessor(agent) or '' for _, accessor in column_defs]

    def _on_double_click(self, event):
        self._open_agent_profile()
        
    def _open_agent_profile(self):
        selected_items = self.list_agents.selection()
        if len(selected_items) == 1:
            agent_id = int(selected_items[0])
            AgentDetailForm(self.main_app, self.manager, agent_id_to_modify=agent_id, on_close_callback=self.refresh_all)

    def _add_agent(self):
        AgentDetailForm(self.main_app, self.manager, on_close_callback=self.refresh_all)


class CategoryPanel(ttk.Frame):
    def __init__(self, parent, categories, on_select_callback):
        super().__init__(parent, padding=5)
        self.on_select_callback = on_select_callback
        
        ttk.Label(self, text="Catégories", font=('Helvetica', 11, 'bold')).pack(anchor="w")
        
        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, pady=5)
        
        for category in categories:
            self.tree.insert("", "end", text=category, iid=category)
            
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, event):
        if self.tree.selection():
            selected_item = self.tree.selection()[0]
            self.on_select_callback(selected_item)
        
    def select_first_category(self):
        if self.tree.get_children():
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
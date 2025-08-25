# Fichier : ui/pages/agents_management_page.py
# VERSION FINALE - Connexion au nouveau formulaire AgentDetailForm.

import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict

from utils.config_loader import CONFIG
from ui.ui_utils import treeview_sort_column
from ui.forms.agent_detail_form import AgentDetailForm # <-- NOUVEL IMPORT
from utils.date_utils import format_date_for_display

class AgentsManagementPage(ttk.Frame):
    def __init__(self, parent, main_app, manager):
        super().__init__(parent)
        self.main_app = main_app
        self.manager = manager
        
        self.current_category = "Professeurs"
        
        self.categories_config = {
            "Professeurs": {"keywords": ["Professeur"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Spécialité", "Service d'affectation", "Date prise de service", "Statut hiérarchique", "Solde Total"]},
            "Médecins Résidents": {"keywords": ["Résident"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Statut contrat", "Spécialité", "Date prise de service", "Date de fin de formation", "Solde Total"]},
            "Médecins Internes": {"keywords": ["Interne"], "columns": ["Nom", "Prénom", "Cadre/Grade", "Date prise de service", "Site de stage 1", "Site de stage 2", "Prolongation", "Solde Total"]},
            "Infirmiers et Techniciens": {"keywords": ["Infirmier", "Technicien", "Sage-femme", "Rééducateur"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Spécialité", "Date prise de service", "Statut hiérarchique", "Solde Total"]},
            "Administration": {"keywords": ["Administrateur", "Adjoint"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Service d'affectation", "Date prise de service", "Solde Total"]}
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
        
        self._create_agents_list_widgets(agents_container)

    def _create_agents_list_widgets(self, parent):
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_all())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.list_agents = ttk.Treeview(parent, show="headings", selectmode="extended")
        self.list_agents.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.list_agents.bind("<Double-1>", self._on_double_click)
        
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(actions_frame, text="Fiche / Modifier", command=self._open_agent_profile).pack(side=tk.LEFT)
        ttk.Button(actions_frame, text="Ajouter un nouvel agent", command=self._add_agent).pack(side=tk.LEFT, padx=5)

    def _on_category_select(self, category_name):
        self.current_category = category_name
        self.refresh_all()
        
    def _setup_agent_list_columns(self):
        current_cols = self.list_agents['columns']
        if not self.current_category: return
        
        new_cols = self.categories_config[self.current_category]["columns"]
        
        if tuple(current_cols) == tuple(new_cols):
            for item in self.list_agents.get_children(): self.list_agents.delete(item)
            return

        self.list_agents.config(columns=new_cols)
        
        for col in new_cols:
            self.list_agents.heading(col, text=col, command=lambda c=col: treeview_sort_column(self.list_agents, c, False))
            self.list_agents.column(col, width=120, anchor='w')

    def refresh_all(self, agent_to_select_id=None):
        self._setup_agent_list_columns()
        if not self.current_category: return
        
        keywords = self.categories_config[self.current_category]["keywords"]
        all_agents = self.manager.get_all_agents(statut='Actif', term=self.search_var.get() or None)
        
        agents_in_category = [agent for agent in all_agents if any(keyword.lower() in agent.cadre.lower() for keyword in keywords)]
        
        columns_map = self.categories_config[self.current_category]["columns"]

        for agent in agents_in_category:
            values = []
            for col_name in columns_map:
                col_attr = col_name.lower().replace(' ', '_').replace('/', '_')
                value = None
                
                if hasattr(agent, col_attr):
                    value = getattr(agent, col_attr)
                elif agent.profil and hasattr(agent.profil, col_attr):
                    value = getattr(agent.profil, col_attr)
                elif col_name == "Solde Total":
                    value = f"{agent.get_solde_total_actif():.1f} j"

                if "date" in col_attr:
                    value = format_date_for_display(value)
                
                values.append(value or '')

            self.list_agents.insert("", "end", values=values, iid=agent.id)
            
        if agent_to_select_id:
            try:
                self.list_agents.selection_set(str(agent_to_select_id))
                self.list_agents.focus(str(agent_to_select_id))
                self.list_agents.see(str(agent_to_select_id))
            except tk.TclError:
                pass

    def _on_double_click(self, event):
        self._open_agent_profile()
        
    def _open_agent_profile(self):
        selected_items = self.list_agents.selection()
        if len(selected_items) == 1:
            agent_id = selected_items[0]
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
# Fichier : ui/panels/agents_panel.py
# VERSION FINALE - Gère deux modes d'affichage : "agents" (catégories) et "conges" (soldes).

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from utils.config_loader import CONFIG
from ui.ui_utils import treeview_sort_column
from ui.forms.agent_detail_form import AgentDetailForm
from ui.agent_synthesis_window import AgentSynthesisWindow
from utils.date_utils import format_date_for_display

class AgentsPanel(ttk.Frame):
    def __init__(self, parent_widget, main_app, manager, base_dir, on_agent_select_callback=None, view_mode="agents"):
        super().__init__(parent_widget)
        self.main_app = main_app
        self.manager = manager
        self.base_dir = base_dir
        self.on_agent_select_callback = on_agent_select_callback
        self.view_mode = view_mode

        self.annee_exercice = self.manager.get_annee_exercice()
        
        # Variables pour la vue 'conges'
        self.current_page = 1
        self.items_per_page = 50
        self.total_pages = 1
        self.status_filter_var = tk.StringVar(value="Actif")

        # Variables pour la vue 'agents'
        self.current_category = None
        self.categories_config = {
            "Professeurs": {"keywords": ["Professeur"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Spécialité", "Service d'affectation"]},
            "Médecins Résidents": {"keywords": ["Résident"], "columns": ["Nom", "Prénom", "PPR", "Statut contrat", "Spécialité", "Date fin de formation"]},
            "Médecins Internes": {"keywords": ["Interne"], "columns": ["Nom", "Prénom", "Date prise de service", "Site de stage 1", "Site de stage 2"]},
            "Infirmiers et Techniciens": {"keywords": ["Infirmier", "Technicien", "Sage-femme", "Rééducateur"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Spécialité", "Statut hiérarchique"]},
            "Administration": {"keywords": ["Administrateur", "Adjoint"], "columns": ["Nom", "Prénom", "PPR", "Cadre/Grade", "Service d'affectation"]}
        }
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_all())

        self._create_widgets()

        if self.view_mode == "agents":
            self.category_panel.select_first_category()
        else:
            self.refresh_all()
    
    def _create_widgets(self):
        if self.view_mode == "agents":
            self._create_agents_view_widgets()
        else: # view_mode == "conges"
            self._create_conges_view_widgets()

    def _create_agents_view_widgets(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)
        
        self.category_panel = CategoryPanel(main_pane, list(self.categories_config.keys()), self._on_category_select)
        main_pane.add(self.category_panel, weight=1)

        agents_container = ttk.Frame(main_pane)
        main_pane.add(agents_container, weight=4)
        
        search_frame = ttk.Frame(agents_container)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.list_agents = ttk.Treeview(agents_container, show="headings", selectmode="extended")
        self.list_agents.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.list_agents.bind("<Double-1>", lambda e: self._open_agent_profile())
        
        actions_frame = ttk.Frame(agents_container)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(actions_frame, text="Fiche / Modifier", command=self._open_agent_profile).pack(side=tk.LEFT)
        ttk.Button(actions_frame, text="Ajouter un nouvel agent", command=self._add_agent).pack(side=tk.LEFT, padx=5)

    def _create_conges_view_widgets(self):
        agents_frame = ttk.LabelFrame(self, text="Agents")
        agents_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        top_bar_frame = ttk.Frame(agents_frame)
        top_bar_frame.pack(fill=tk.X, padx=5, pady=5)

        filter_frame = ttk.Frame(top_bar_frame)
        filter_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(filter_frame, text="Agents Actifs", variable=self.status_filter_var, value="Actif", command=self.refresh_all).pack(anchor='w')
        ttk.Radiobutton(filter_frame, text="Agents Archivés", variable=self.status_filter_var, value="Archivé", command=self.refresh_all).pack(anchor='w')

        search_frame = ttk.Frame(top_bar_frame)
        search_frame.pack(fill=tk.X, expand=True, side=tk.LEFT)
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(search_frame, textvariable=self.search_var).pack(fill=tk.X, expand=True, side=tk.LEFT)
        
        an_n, an_n1, an_n2 = self.annee_exercice, self.annee_exercice - 1, self.annee_exercice - 2
        cols = ["ID", "Nom", "Prénom", "Cadre/Grade", f"Solde {an_n2}", f"Solde {an_n1}", f"Solde {an_n}", "Solde Total"]
        
        self.list_agents = ttk.Treeview(agents_frame, columns=cols, show="headings", selectmode="extended")
        
        for col in cols:
            self.list_agents.heading(col, text=col, command=lambda c=col: treeview_sort_column(self.list_agents, c, False))
        
        self.list_agents.column("ID", width=0, stretch=False)
        self.list_agents.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.list_agents.bind("<<TreeviewSelect>>", self._on_agent_select)
        self.list_agents.bind("<Double-1>", self._on_double_click_synthesis)

        pagination_frame = ttk.Frame(agents_frame)
        pagination_frame.pack(fill=tk.X, padx=5, pady=5)
        self.prev_button = ttk.Button(pagination_frame, text="<< Précédent", command=self.prev_page); self.prev_button.pack(side=tk.LEFT)
        self.page_label = ttk.Label(pagination_frame, text="Page 1 / 1"); self.page_label.pack(side=tk.LEFT, expand=True)
        self.next_button = ttk.Button(pagination_frame, text="Suivant >>", command=self.next_page); self.next_button.pack(side=tk.RIGHT)

    def refresh_all(self, agent_to_select_id=None):
        if self.view_mode == "agents":
            self._refresh_agents_view(agent_to_select_id)
        else:
            self._refresh_conges_view(agent_to_select_id)

    def _refresh_agents_view(self, agent_to_select_id=None):
        self._setup_columns_for_category()
        if not self.current_category: return

        keywords = self.categories_config[self.current_category]["keywords"]
        all_agents = self.manager.get_all_agents(statut='Actif', term=self.search_var.get() or None)
        agents_in_category = [agent for agent in all_agents if any(k.lower() in agent.cadre.lower() for k in keywords)]
        
        columns_map = self.categories_config[self.current_category]["columns"]
        for agent in agents_in_category:
            values = self._get_agent_values_for_columns(agent, columns_map)
            self.list_agents.insert("", "end", values=values, iid=agent.id)
            
        if agent_to_select_id: self._select_agent_in_list(agent_to_select_id)

    def _refresh_conges_view(self, agent_to_select_id=None):
        for row in self.list_agents.get_children(): self.list_agents.delete(row)
        
        statut = self.status_filter_var.get()
        term = self.search_var.get().strip().lower() or None
        total_items = self.manager.get_agents_count(statut, term)
        self.total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        self.current_page = min(self.current_page, self.total_pages)
        offset = (self.current_page - 1) * self.items_per_page
        
        agents = self.manager.get_all_agents(statut=statut, term=term, limit=self.items_per_page, offset=offset)
        
        an_n, an_n1, an_n2 = self.annee_exercice, self.annee_exercice - 1, self.annee_exercice - 2
        for agent in agents:
            soldes = {s.annee: s.solde for s in agent.soldes_annuels}
            values = (
                agent.id, agent.nom, agent.prenom, agent.cadre,
                f"{soldes.get(an_n2, 0.0):.1f} j", f"{soldes.get(an_n1, 0.0):.1f} j",
                f"{soldes.get(an_n, 0.0):.1f} j", f"{agent.get_solde_total_actif():.1f} j"
            )
            self.list_agents.insert("", "end", values=values, iid=agent.id)

        if agent_to_select_id: self._select_agent_in_list(agent_to_select_id)
        
        self.page_label.config(text=f"Page {self.current_page} / {self.total_pages}")
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")

    def _get_agent_values_for_columns(self, agent, columns):
        values = []
        for col_name in columns:
            col_attr = col_name.lower().replace(' ', '_').replace('/', '_')
            value = None
            if hasattr(agent, col_attr): value = getattr(agent, col_attr)
            elif agent.profil and hasattr(agent.profil, col_attr): value = getattr(agent.profil, col_attr)
            elif col_name == "Solde Total": value = f"{agent.get_solde_total_actif():.1f} j"
            if "date" in col_attr: value = format_date_for_display(value)
            values.append(value or '')
        return values

    def _setup_columns_for_category(self):
        if not self.current_category: return
        new_cols = self.categories_config[self.current_category]["columns"]
        self.list_agents.config(columns=new_cols)
        for item in self.list_agents.get_children(): self.list_agents.delete(item)
        for col in new_cols:
            self.list_agents.heading(col, text=col, command=lambda c=col: treeview_sort_column(self.list_agents, c, False))
            self.list_agents.column(col, width=120, anchor='w')
            
    def _on_category_select(self, category_name):
        self.current_category = category_name
        self.refresh_all()
        
    def get_selected_agent_ids(self):
        return [int(iid) for iid in self.list_agents.selection()]

    def _select_agent_in_list(self, agent_id):
        try:
            self.list_agents.selection_set(str(agent_id))
            self.list_agents.focus(str(agent_id))
            self.list_agents.see(str(agent_id))
        except tk.TclError: pass # L'agent n'est pas dans la liste affichée

    def _on_agent_select(self, event=None):
        if self.on_agent_select_callback:
            selected_ids = self.get_selected_agent_ids()
            agent_id = selected_ids[0] if len(selected_ids) == 1 else None
            self.on_agent_select_callback(agent_id)

    def _open_agent_profile(self):
        selected_ids = self.get_selected_agent_ids()
        if len(selected_ids) == 1:
            AgentDetailForm(self.main_app, self.manager, agent_id_to_modify=selected_ids[0], on_close_callback=self.refresh_all)

    def _add_agent(self):
        AgentDetailForm(self.main_app, self.manager, on_close_callback=self.refresh_all)

    def _on_double_click_synthesis(self, event=None):
        selected_ids = self.get_selected_agent_ids()
        if len(selected_ids) == 1:
            AgentSynthesisWindow(self.main_app, self.manager, selected_ids[0])
            
    def search_agents(self):
        if self.view_mode == "conges":
            self.current_page = 1
        self.refresh_all()

    def prev_page(self):
        if self.current_page > 1: self.current_page -= 1; self.refresh_all()

    def next_page(self):
        if self.current_page < self.total_pages: self.current_page += 1; self.refresh_all()

class CategoryPanel(ttk.Frame):
    def __init__(self, parent, categories, on_select_callback):
        super().__init__(parent, padding=5)
        self.on_select_callback = on_select_callback
        ttk.Label(self, text="Catégories", font=('Helvetica', 11, 'bold')).pack(anchor="w")
        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, pady=5)
        for category in categories: self.tree.insert("", "end", text=category, iid=category)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, event):
        if self.tree.selection(): self.on_select_callback(self.tree.selection()[0])
        
    def select_first_category(self):
        if self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first); self.tree.focus(first)
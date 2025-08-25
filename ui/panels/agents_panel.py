# Fichier : ui/panels/agents_panel.py
# MISE À JOUR - Le double-clic ouvre la fenêtre de synthèse.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from core.constants import SoldeStatus
from ui.ui_utils import treeview_sort_column
from utils.file_utils import export_agents_to_excel, import_agents_from_excel
from ui.agent_synthesis_window import AgentSynthesisWindow
from utils.date_utils import format_date_for_display

class AgentsPanel(ttk.Frame):
    def __init__(self, parent_widget, main_app, manager, base_dir, on_agent_select_callback):
        super().__init__(parent_widget, padding=5)
        self.main_app = main_app
        self.manager = manager
        self.base_dir = base_dir
        self.on_agent_select_callback = on_agent_select_callback

        self.annee_exercice = self.manager.get_annee_exercice()
        
        self.current_page = 1
        self.items_per_page = 50
        self.total_pages = 1
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.search_agents())
        self.status_filter_var = tk.StringVar(value="Actif")

        self._create_widgets()
        self.refresh_agents_list()

    def _create_widgets(self):
        agents_frame = ttk.LabelFrame(self, text="Agents")
        agents_frame.pack(fill=tk.BOTH, expand=True)

        top_bar_frame = ttk.Frame(agents_frame)
        top_bar_frame.pack(fill=tk.X, padx=5, pady=5)

        filter_frame = ttk.Frame(top_bar_frame)
        filter_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(filter_frame, text="Agents Actifs", variable=self.status_filter_var, value="Actif", command=self.refresh_agents_list).pack(anchor='w')
        ttk.Radiobutton(filter_frame, text="Agents Archivés", variable=self.status_filter_var, value="Archivé", command=self.refresh_agents_list).pack(anchor='w')

        search_frame = ttk.Frame(top_bar_frame)
        search_frame.pack(fill=tk.X, expand=True, side=tk.LEFT)
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, expand=True, side=tk.LEFT)
        
        # --- Colonnes simplifiées pour la vue Congés ---
        self.cols_agents = ["ID", "Nom", "Prénom", "Cadre", "Solde Total Actif"]
        self.list_agents = ttk.Treeview(agents_frame, columns=self.cols_agents, show="headings", selectmode="extended")
        
        for col in self.cols_agents:
            self.list_agents.heading(col, text=col, command=lambda c=col: treeview_sort_column(self.list_agents, c, False))
        
        self.list_agents.column("ID", width=0, stretch=False)
        self.list_agents.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.list_agents.bind("<<TreeviewSelect>>", self._on_agent_select)
        self.list_agents.bind("<Double-1>", self.open_agent_synthesis)

        pagination_frame = ttk.Frame(agents_frame); pagination_frame.pack(fill=tk.X, padx=5, pady=5)
        self.prev_button = ttk.Button(pagination_frame, text="<< Précédent", command=self.prev_page); self.prev_button.pack(side=tk.LEFT)
        self.page_label = ttk.Label(pagination_frame, text="Page 1 / 1"); self.page_label.pack(side=tk.LEFT, expand=True)
        self.next_button = ttk.Button(pagination_frame, text="Suivant >>", command=self.next_page); self.next_button.pack(side=tk.RIGHT)
        
        # Le panel Agent de la vue Congés n'a pas de barre d'action
        # On garde le frame au cas où on voudrait en rajouter plus tard
        self.actions_frame = ttk.Frame(agents_frame)
        self.actions_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

    def get_selected_agent_ids(self):
        return [int(self.list_agents.item(item_id)["values"][0]) for item_id in self.list_agents.selection()]

    def open_agent_synthesis(self, event=None):
        selected_ids = self.get_selected_agent_ids()
        if len(selected_ids) == 1:
            AgentSynthesisWindow(self.main_app, self.manager, selected_ids[0])

    def refresh_agents_list(self, agent_to_select_id=None):
        for row in self.list_agents.get_children(): self.list_agents.delete(row)
        
        statut = self.status_filter_var.get()
        term = self.search_var.get().strip().lower() or None
        total_items = self.manager.get_agents_count(statut, term)
        self.total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        self.current_page = min(self.current_page, self.total_pages)
        offset = (self.current_page - 1) * self.items_per_page
        
        agents = self.manager.get_all_agents(statut=statut, term=term, limit=self.items_per_page, offset=offset)
        
        item_to_select = None
        for agent in agents:
            solde_total_display = f"{agent.get_solde_total_actif():.1f} j"
            values = (agent.id, agent.nom, agent.prenom, agent.cadre, solde_total_display)
            
            item_id = self.list_agents.insert("", "end", values=values, iid=agent.id)
            if agent_to_select_id is not None and agent.id == agent_to_select_id:
                item_to_select = item_id

        if item_to_select:
            self.list_agents.selection_set(item_to_select)
            self.list_agents.see(item_to_select)
        
        self.page_label.config(text=f"Page {self.current_page} / {self.total_pages}")
        self.prev_button.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_button.config(state="normal" if self.current_page < self.total_pages else "disabled")
        self.main_app.set_status(f"{len(agents)} agents affichés sur {total_items} au total.")

    def search_agents(self):
        self.current_page = 1
        self.refresh_agents_list()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_agents_list()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_agents_list()

    def _on_agent_select(self, event=None):
        selected_ids = self.get_selected_agent_ids()
        agent_id_for_conges = selected_ids[0] if len(selected_ids) == 1 else None
        self.on_agent_select_callback(agent_id_for_conges)
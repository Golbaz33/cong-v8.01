# Fichier : ui/pages/dashboard_page.py
# VERSION FINALE - Ajout des filtres de statistiques.

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import logging

from utils.date_utils import format_date_for_display, calculate_reprise_date, validate_date

class DashboardPage(ttk.Frame):
    def __init__(self, parent, main_app, manager):
        super().__init__(parent)
        self.main_app = main_app
        self.manager = manager
        
        self.annee_exercice = self.manager.get_annee_exercice()
        
        # --- Variables pour les filtres ---
        self.filter_cadre = tk.StringVar(value="Tous")
        self.filter_service = tk.StringVar(value="Tous")
        self.filter_specialite = tk.StringVar(value="Tous")
        
        self._create_widgets()
        self.refresh_stats()

    def _create_widgets(self):
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=(15, 15))

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        actions_frame = ttk.Frame(scrollable_frame)
        actions_frame.pack(fill="x", pady=(0, 20), anchor="w")
        
        ttk.Button(actions_frame, text="🔄 Actualiser les données", command=self.refresh_stats).pack(side="left")

        # --- NOUVEAU CADRE POUR LES FILTRES ---
        filters_frame = ttk.LabelFrame(scrollable_frame, text="Filtres", padding=10)
        filters_frame.pack(fill="x", pady=10)
        
        # Filtre Cadre
        ttk.Label(filters_frame, text="Cadre/Grade:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.cadre_combo = ttk.Combobox(filters_frame, textvariable=self.filter_cadre, state="readonly", width=30)
        self.cadre_combo.grid(row=0, column=1, padx=(0, 20), pady=5, sticky="ew")
        self.cadre_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_stats())
        
        # Filtre Service
        ttk.Label(filters_frame, text="Service:").grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")
        self.service_combo = ttk.Combobox(filters_frame, textvariable=self.filter_service, state="readonly", width=30)
        self.service_combo.grid(row=0, column=3, padx=(0, 20), pady=5, sticky="ew")
        self.service_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_stats())
        
        # Filtre Spécialité
        ttk.Label(filters_frame, text="Spécialité:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.specialite_combo = ttk.Combobox(filters_frame, textvariable=self.filter_specialite, state="readonly", width=30)
        self.specialite_combo.grid(row=1, column=1, pady=5, sticky="ew")
        self.specialite_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_stats())

        filters_frame.columnconfigure(1, weight=1)
        filters_frame.columnconfigure(3, weight=1)
        
        stats_frame = ttk.LabelFrame(scrollable_frame, text="Statistiques Générales", padding=10)
        stats_frame.pack(fill="x", pady=10)
        self.stats_agents_actifs = ttk.Label(stats_frame, text="Agents actifs : -", font=('Helvetica', 11))
        self.stats_agents_actifs.pack(anchor="w")
        self.stats_total_conges = ttk.Label(stats_frame, text="Congés enregistrés (actifs) : -", font=('Helvetica', 11))
        self.stats_total_conges.pack(anchor="w", pady=(5,0))

        on_leave_frame = ttk.LabelFrame(scrollable_frame, text="Agents Actuellement en Congé", padding=10)
        on_leave_frame.pack(fill="both", expand=True, pady=10)
        
        cols_on_leave = ("Agent", "PPR", "Type Congé", "Date de Reprise")
        self.list_on_leave = ttk.Treeview(on_leave_frame, columns=cols_on_leave, show="headings", height=8)
        for col in cols_on_leave: self.list_on_leave.heading(col, text=col)
        self.list_on_leave.pack(fill="both", expand=True, padx=5, pady=5)
        
        upcoming_frame = ttk.LabelFrame(scrollable_frame, text="Congés Débutant dans les 7 Prochains Jours", padding=10)
        upcoming_frame.pack(fill="both", expand=True, pady=10)
        
        cols_upcoming = ("Agent", "PPR", "Type Congé", "Date de Début")
        self.list_upcoming = ttk.Treeview(upcoming_frame, columns=cols_upcoming, show="headings", height=8)
        for col in cols_upcoming: self.list_upcoming.heading(col, text=col)
        self.list_upcoming.pack(fill="both", expand=True, padx=5, pady=5)

    def _populate_filters(self, all_agents):
        """Remplit les menus déroulants des filtres avec les données existantes."""
        cadres = sorted(list(set(agent.cadre for agent in all_agents if agent.cadre)))
        services = sorted(list(set(agent.service_affectation for agent in all_agents if agent.service_affectation)))
        specialites = sorted(list(set(agent.specialite for agent in all_agents if agent.specialite)))
        
        self.cadre_combo['values'] = ["Tous"] + cadres
        self.service_combo['values'] = ["Tous"] + services
        self.specialite_combo['values'] = ["Tous"] + specialites

    def refresh_stats(self):
        """Met à jour toutes les listes et statistiques de la page."""
        self.main_app.set_status("Chargement du tableau de bord...")
        
        all_agents = self.manager.get_all_agents(statut='Actif')
        all_agents_map = {agent.id: agent for agent in all_agents}
        all_active_leaves = [c for c in self.manager.get_all_conges() if c.statut == 'Actif']
        
        self._populate_filters(all_agents)
        
        # Appliquer les filtres
        filtered_agents_ids = set(all_agents_map.keys())
        
        if self.filter_cadre.get() != "Tous":
            filtered_agents_ids &= {id for id, agent in all_agents_map.items() if agent.cadre == self.filter_cadre.get()}
        if self.filter_service.get() != "Tous":
            filtered_agents_ids &= {id for id, agent in all_agents_map.items() if agent.service_affectation == self.filter_service.get()}
        if self.filter_specialite.get() != "Tous":
            filtered_agents_ids &= {id for id, agent in all_agents_map.items() if agent.specialite == self.filter_specialite.get()}

        # Mise à jour des statistiques
        self.stats_agents_actifs.config(text=f"Agents actifs : {len(all_agents)}")
        self.stats_total_conges.config(text=f"Congés enregistrés (actifs) : {len(all_active_leaves)}")

        # Mise à jour de la liste des agents en congé
        for row in self.list_on_leave.get_children(): self.list_on_leave.delete(row)
        holidays_set = self.manager.get_holidays_set_for_period(self.annee_exercice, self.annee_exercice + 1)
        today = datetime.now().date()

        for conge in all_active_leaves:
            if conge.agent_id in filtered_agents_ids:
                start_date = conge.date_debut.date() if isinstance(conge.date_debut, datetime) else conge.date_debut
                end_date = conge.date_fin.date() if isinstance(conge.date_fin, datetime) else conge.date_fin
                if start_date and end_date and start_date <= today <= end_date:
                    agent = all_agents_map[conge.agent_id]
                    reprise_date = calculate_reprise_date(conge.date_fin, holidays_set)
                    reprise_display = format_date_for_display(reprise_date) if reprise_date else "N/A"
                    self.list_on_leave.insert("", "end", values=(f"{agent.nom} {agent.prenom}", agent.ppr, conge.type_conge, reprise_display))

        # Mise à jour de la liste des congés à venir
        for row in self.list_upcoming.get_children(): self.list_upcoming.delete(row)
        one_week_from_now = today + timedelta(days=7)

        for conge in sorted(all_active_leaves, key=lambda c: c.date_debut):
            if conge.agent_id in filtered_agents_ids:
                start_date = conge.date_debut.date() if isinstance(conge.date_debut, datetime) else conge.date_debut
                if start_date and today < start_date <= one_week_from_now:
                    agent = all_agents_map[conge.agent_id]
                    self.list_upcoming.insert("", "end", values=(f"{agent.nom} {agent.prenom}", agent.ppr, conge.type_conge, format_date_for_display(conge.date_debut)))

        self.main_app.set_status("Prêt.")

    def refresh_all(self, agent_to_select_id=None):
        self.refresh_stats()
# Fichier : ui/agent_synthesis_window.py
# NOUVEAU FICHIER - Fenêtre de consultation rapide pour un agent.

import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict
from datetime import datetime

from utils.date_utils import format_date_for_display_short, calculate_reprise_date

class AgentSynthesisWindow(tk.Toplevel):
    def __init__(self, parent, manager, agent_id):
        super().__init__(parent)
        self.manager = manager
        
        self.agent = self.manager.get_agent_by_id(agent_id)
        if not self.agent:
            messagebox.showerror("Erreur", "Impossible de charger les données de l'agent.", parent=parent)
            self.destroy(); return

        self.title(f"Synthèse : {self.agent.nom} {self.agent.prenom}")
        self.grab_set()
        self.geometry("700x500")
        self.resizable(False, False)

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # --- Informations clés ---
        info_frame = ttk.LabelFrame(main_frame, text="Informations Clés", padding=10)
        info_frame.pack(fill="x", pady=5)
        
        ttk.Label(info_frame, text=f"Nom Complet:").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, text=f"{self.agent.nom} {self.agent.prenom}", font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky="w")
        
        ttk.Label(info_frame, text=f"Cadre / Grade:").grid(row=1, column=0, sticky="w")
        ttk.Label(info_frame, text=f"{self.agent.cadre}", font=('Helvetica', 10, 'bold')).grid(row=1, column=1, sticky="w")
        info_frame.columnconfigure(1, weight=1)

        # --- Panneau à onglets pour Soldes et Congés ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=10)

        soldes_tab = ttk.Frame(notebook, padding=10)
        conges_tab = ttk.Frame(notebook, padding=10)
        
        notebook.add(soldes_tab, text="Soldes de Congés Annuels")
        notebook.add(conges_tab, text="Historique des Congés")
        
        self._populate_soldes_tab(soldes_tab)
        self._populate_conges_tab(conges_tab)

        ttk.Button(main_frame, text="Fermer", command=self.destroy).pack(side="bottom", pady=5)

    def _populate_soldes_tab(self, parent):
        cols = ("Année", "Solde (j)", "Statut")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=5)
        for col in cols:
            tree.heading(col, text=col)
        
        tree.column("Année", anchor='center', width=100)
        tree.column("Solde (j)", anchor='center', width=120)
        tree.column("Statut", anchor='center', width=100)

        if self.agent.soldes_annuels:
            for solde in sorted(self.agent.soldes_annuels, key=lambda s: s.annee, reverse=True):
                tree.insert("", "end", values=(solde.annee, f"{solde.solde:.1f}", solde.statut))
        
        tree.pack(fill="both", expand=True)
    
    def _populate_conges_tab(self, parent):
        conges = self.manager.get_conges_for_agent(self.agent.id)
        
        cols = ("Type", "Début", "Fin", "Jours Pris", "Statut")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
        
        tree.column("Type", width=150)
        tree.column("Début", width=100, anchor='center')
        tree.column("Fin", width=100, anchor='center')
        tree.column("Jours Pris", width=80, anchor='center')
        tree.column("Statut", width=80, anchor='center')
        
        if conges:
            conges_par_annee = defaultdict(list)
            for c in conges:
                if c.date_debut: conges_par_annee[c.date_debut.year].append(c)

            for annee in sorted(conges_par_annee.keys(), reverse=True):
                tree.insert("", "end", values=(f"--- ANNÉE {annee} ---", "", "", "", ""))
                for conge in sorted(conges_par_annee[annee], key=lambda c: c.date_debut):
                    tree.insert("", "end", values=(
                        conge.type_conge,
                        format_date_for_display_short(conge.date_debut),
                        format_date_for_display_short(conge.date_fin),
                        conge.jours_pris,
                        conge.statut
                    ))
        
        tree.pack(fill="both", expand=True)
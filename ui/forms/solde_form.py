# Fichier : ui/forms/solde_form.py
# NOUVEAU FICHIER - Fenêtre dédiée à la modification des soldes d'un agent.

import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict

class SoldeForm(tk.Toplevel):
    def __init__(self, parent, manager, agent_id):
        super().__init__(parent)
        self.parent = parent
        self.manager = manager
        self.agent_id = agent_id
        
        agent = self.manager.get_agent_by_id(self.agent_id)
        if not agent:
            messagebox.showerror("Erreur", "Agent introuvable.", parent=parent)
            self.destroy()
            return

        self.title(f"Modifier les Soldes de {agent.nom} {agent.prenom}")
        self.grab_set()
        self.resizable(False, False)

        self.solde_entries = {}
        self.annee_exercice = self.manager.get_annee_exercice()
        
        self._create_widgets(agent)

    def _create_widgets(self, agent):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        soldes_map = {s.annee: s for s in agent.soldes_annuels}
        years_to_display = sorted(list(set(list(soldes_map.keys()) + [self.annee_exercice, self.annee_exercice - 1, self.annee_exercice - 2])), reverse=True)

        for i, year in enumerate(years_to_display[:5]): # On affiche les 5 dernières années max
            solde_obj = soldes_map.get(year)
            
            if solde_obj:
                status_text = f"({solde_obj.statut})"
                current_value = f"{solde_obj.solde:.1f}"
                entry_key = solde_obj.id
            else:
                status_text = "(Nouveau)"
                current_value = "0.0"
                entry_key = year

            label_text = f"Année {year} {status_text} :"
            ttk.Label(main_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5, pady=5)
            entry = ttk.Entry(main_frame, width=10)
            entry.grid(row=i, column=1, padx=5)
            entry.insert(0, current_value)
            self.solde_entries[entry_key] = entry

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=len(self.solde_entries), columnspan=2, pady=(20, 0))
        ttk.Button(btn_frame, text="Valider", command=self._on_validate).pack(side="right")
        ttk.Button(btn_frame, text="Annuler", command=self.destroy).pack(side="right", padx=10)

    def _on_validate(self):
        updates = {}; creations = {}
        try:
            for key, entry in self.solde_entries.items():
                new_value = float(entry.get().replace(",", "."))
                if new_value < 0: raise ValueError("Les soldes ne peuvent pas être négatifs.")
                
                if isinstance(key, int): # C'est un ID, donc une mise à jour
                    updates[key] = new_value
                else: # C'est une année, donc une création
                    if new_value > 0: creations[key] = new_value
        except ValueError as e:
            messagebox.showerror("Erreur de Saisie", f"Veuillez entrer des nombres valides.\n{e}", parent=self)
            return
        
        try:
            if self.manager.save_manual_soldes(self.agent_id, updates, creations):
                messagebox.showinfo("Succès", "Les soldes ont été mis à jour.", parent=self)
                self.parent.refresh_all(self.agent_id)
                self.destroy()
        except Exception as e:
             messagebox.showerror("Erreur de Sauvegarde", f"La mise à jour a échoué : {e}", parent=self)
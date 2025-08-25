# Fichier : ui/forms/agent_form.py
# VERSION FINALE - Correction de la logique pour le motif "Abandon de poste".

import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict
import logging

from utils.config_loader import CONFIG
from ui.widgets.arabic_keyboard import ArabicKeyboard
from ui.widgets.date_picker import DatePickerWindow

class AgentForm(tk.Toplevel):
    def __init__(self, parent, manager, agent_id_to_modify=None):
        super().__init__(parent)
        self.parent = parent
        self.manager = manager
        self.agent_id = agent_id_to_modify
        self.is_modification = agent_id_to_modify is not None

        title = "Modifier un Agent" if self.is_modification else "Ajouter un Agent"
        self.title(title)
        self.grab_set()
        self.geometry("750x700")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)

        self.vars = defaultdict(tk.StringVar)
        self.cadre_var = tk.StringVar()
        self.annee_exercice = self.manager.get_annee_exercice()
        self.has_changed = False

        self.soignant_cadres = ["infirmier", "sage-femme", "technicien de santé", "rééducateur", "assistant médico-social", "technicien en maintenance biomédicale"]
        self.formation_cadres = ["médecin résident", "médecin interne"]

        self._create_widgets()

        if self.is_modification:
            self._populate_data()
        
        for var in list(self.vars.values()) + [self.cadre_var]:
            var.trace_add("write", self._set_changed_flag)
        
        self._on_cadre_change()
        self.has_changed = False

    def _set_changed_flag(self, *args):
        self.has_changed = True

    def _populate_data(self):
        self.has_changed = False
        agent = self.manager.get_agent_by_id(self.agent_id)
        if not agent:
            messagebox.showerror("Erreur", "Agent introuvable.", parent=self); self.destroy(); return

        common_fields = ['nom', 'nom_arabe', 'prenom', 'prenom_arabe', 'ppr', 'cnie', 'sexe',
                         'type_recrutement', 'statut_hierarchique', 'specialite', 
                         'service_affectation', 'telephone_pro', 'email_pro', 'motif_cessation_service']
        for field in common_fields: self.vars[field].set(getattr(agent, field, '') or '')
        
        self.cadre_var.set(agent.cadre)
        
        if agent.date_prise_service: self.vars['date_prise_service'].set(agent.date_prise_service.strftime('%d/%m/%Y'))
        if agent.date_cessation_service: self.vars['date_cessation_service'].set(agent.date_cessation_service.strftime('%d/%m/%Y'))

        if hasattr(agent, 'profil') and agent.profil and "résident" in agent.cadre.lower():
            self.vars['type_residanat'].set(agent.profil.type_residanat or '')
            self.vars['statut_contrat_resident'].set(agent.profil.statut_contrat or '')
            if agent.profil.date_fin_formation:
                self.vars['date_fin_formation'].set(agent.profil.date_fin_formation.strftime('%d/%m/%Y'))
        
        self.has_changed = False

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(main_frame, padding=(10, 10))
        btn_frame.pack(fill="x", side="bottom")
        ttk.Button(btn_frame, text="Valider", command=self._on_validate).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Annuler", command=self._on_close_button).pack(side=tk.RIGHT, padx=5)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, padding=(15, 15))

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._create_personnel_section(self.scrollable_frame)
        self._create_poste_section(self.scrollable_frame)
        self._create_profil_specific_frames(self.scrollable_frame)
        if not self.is_modification:
            self._create_solde_section(self.scrollable_frame)

    def _create_personnel_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Informations Personnelles", padding=10)
        frame.pack(fill="x", pady=5)
        
        ttk.Label(frame, text="Nom:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['nom'], width=30).grid(row=0, column=1, sticky="ew")
        
        ttk.Label(frame, text="Nom (arabe):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self._create_entry_with_keyboard(frame, self.vars['nom_arabe']).grid(row=1, column=1, sticky="ew")

        ttk.Label(frame, text="Prénom:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['prenom'], width=30).grid(row=2, column=1, sticky="ew")

        ttk.Label(frame, text="Prénom (arabe):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self._create_entry_with_keyboard(frame, self.vars['prenom_arabe']).grid(row=3, column=1, sticky="ew")
        
        ttk.Label(frame, text="Sexe:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.vars['sexe'], values=["", "Homme", "Femme"], state="readonly").grid(row=4, column=1, sticky="ew")
        
        ttk.Label(frame, text="PPR:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['ppr']).grid(row=5, column=1, sticky="ew")
        
        ttk.Label(frame, text="CNIE:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['cnie']).grid(row=6, column=1, sticky="ew")

        ttk.Label(frame, text="Téléphone:").grid(row=7, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['telephone_pro']).grid(row=7, column=1, sticky="ew")

        ttk.Label(frame, text="Email:").grid(row=8, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['email_pro']).grid(row=8, column=1, sticky="ew")
        
        frame.columnconfigure(1, weight=1)

    def _create_poste_section(self, parent):
        self.poste_frame = ttk.LabelFrame(parent, text="Poste & Carrière", padding=10)
        self.poste_frame.pack(fill="x", pady=5)
        frame = self.poste_frame
        
        cadres = CONFIG['ui'].get('grades', [])
        ttk.Label(frame, text="Cadre / Grade:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.combo_cadre = ttk.Combobox(frame, textvariable=self.cadre_var, values=[""] + cadres, state="readonly")
        self.combo_cadre.grid(row=0, column=1, sticky="ew", columnspan=2)
        self.combo_cadre.bind("<<ComboboxSelected>>", self._on_cadre_change)
        
        ttk.Label(frame, text="Spécialité:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['specialite']).grid(row=1, column=1, sticky="ew", columnspan=2)

        ttk.Label(frame, text="Service d'affectation:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['service_affectation']).grid(row=2, column=1, sticky="ew", columnspan=2)

        self.statut_label = ttk.Label(frame, text="Statut Hiérarchique:")
        self.statut_label.grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.statut_combo = ttk.Combobox(frame, textvariable=self.vars['statut_hierarchique'], state="readonly")
        self.statut_combo.grid(row=3, column=1, sticky="ew", columnspan=2)

        self.recrutement_label = ttk.Label(frame, text="Type Recrutement:")
        self.recrutement_label.grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.recrutement_combo = ttk.Combobox(frame, textvariable=self.vars['type_recrutement'], values=["", "Recrutement", "Détachement", "Mutation"], state="readonly")
        self.recrutement_combo.grid(row=4, column=1, sticky="ew", columnspan=2)
        
        ttk.Label(frame, text="Date prise de service:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self._create_date_entry(frame, self.vars['date_prise_service'], 5, 1)

        ttk.Label(frame, text="Date cessation de service:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
        self._create_date_entry(frame, self.vars['date_cessation_service'], 6, 1)
        
        self.motif_label = ttk.Label(frame, text="Motif cessation:")
        self.motif_label.grid(row=7, column=0, sticky="w", padx=5, pady=5)
        self.motif_combo = ttk.Combobox(frame, textvariable=self.vars['motif_cessation_service'])
        self.motif_combo.grid(row=7, column=1, sticky="ew", columnspan=2)

        frame.columnconfigure(1, weight=1)

    def _create_profil_specific_frames(self, parent):
        self.resident_frame = ttk.LabelFrame(parent, text="Détails du Résidanat", padding=10)
        
        ttk.Label(self.resident_frame, text="Type Résidanat:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ttk.Combobox(self.resident_frame, textvariable=self.vars['type_residanat'], values=["", "Sur titre", "Sur concours"], state="readonly").grid(row=0, column=1, sticky="ew")

        ttk.Label(self.resident_frame, text="Statut Contrat:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        ttk.Combobox(self.resident_frame, textvariable=self.vars['statut_contrat_resident'], values=["", "Bénévole", "Contractuel"], state="readonly").grid(row=1, column=1, sticky="ew")

        ttk.Label(self.resident_frame, text="Date fin de formation:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self._create_date_entry(self.resident_frame, self.vars['date_fin_formation'], 2, 1)
        
        self.resident_frame.columnconfigure(1, weight=1)

    def _create_solde_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Solde Initial", padding=10)
        frame.pack(fill="x", pady=5)
        
        self.solde_entries = {}
        an_n, an_n1, an_n2 = self.annee_exercice, self.annee_exercice - 1, self.annee_exercice - 2
        
        ttk.Label(frame, text=f"Solde ({an_n2}):").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        e = ttk.Entry(frame); e.grid(row=0, column=1, sticky="ew"); e.insert(0, "0.0"); self.solde_entries[an_n2] = e
        
        ttk.Label(frame, text=f"Solde ({an_n1}):").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        e = ttk.Entry(frame); e.grid(row=1, column=1, sticky="ew"); e.insert(0, "0.0"); self.solde_entries[an_n1] = e
        
        ttk.Label(frame, text=f"Solde ({an_n}):").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        e = ttk.Entry(frame); e.grid(row=2, column=1, sticky="ew"); e.insert(0, str(CONFIG['conges'].get('solde_annuel_par_defaut', 22.0))); self.solde_entries[an_n] = e

        frame.columnconfigure(1, weight=1)

    def _on_cadre_change(self, event=None):
        cadre_lower = self.cadre_var.get().lower()
        
        if self.resident_frame.winfo_ismapped(): self.resident_frame.pack_forget()

        # --- NOUVELLE LOGIQUE DYNAMIQUE ---
        motifs_base = ["", "Démission", "Abandon de poste", "Mutation"]
        is_formation = any(c in cadre_lower for c in self.formation_cadres)

        if is_formation:
            self.statut_label.grid_remove(); self.statut_combo.grid_remove()
            motifs_specifiques = ["Fin de formation", "Changement de centre de formation"]
            self.motif_combo['values'] = motifs_base + motifs_specifiques
            if "résident" in cadre_lower: self.resident_frame.pack(fill="x", pady=5)
        else:
            self.statut_label.grid(); self.statut_combo.grid()
            motifs_specifiques = ["Retraite", "Fin de détachement"]
            self.motif_combo['values'] = motifs_base + motifs_specifiques
            
            is_soignant = any(c in cadre_lower for c in self.soignant_cadres)
            if is_soignant:
                self.statut_combo['values'] = ["", "Normal", "Infirmier chef", "Surveillant Général"]
            else:
                self.statut_combo['values'] = ["", "Normal", "Chef de service", "Chef de division"]

    def _on_validate(self):
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir enregistrer les modifications ?", parent=self):
            try:
                agent_data = {field: var.get() for field, var in self.vars.items()}
                agent_data['cadre'] = self.cadre_var.get()
                
                if not agent_data['nom'] or not agent_data['cadre']: raise ValueError("Le nom et le cadre sont obligatoires.")

                if self.is_modification: agent_data['id'] = self.agent_id
                else:
                    agent_data['soldes'] = {annee: float(entry.get().replace(",", ".")) for annee, entry in self.solde_entries.items()}

                self.manager.save_full_agent(agent_data, self.is_modification)
                
                self.has_changed = False # Marquer comme non modifié après sauvegarde
                message = "Agent modifié." if self.is_modification else "Agent ajouté."
                self.parent.set_status(message)
                self.parent.refresh_all(self.agent_id)
                self.destroy()
                
            except Exception as e:
                logging.error(f"Erreur de validation du formulaire agent: {e}", exc_info=True)
                messagebox.showerror("Erreur de validation", str(e), parent=self)

    def _on_close_button(self):
        if self.has_changed:
            if messagebox.askyesno("Modifications non enregistrées", "Vous avez des modifications non enregistrées. Voulez-vous vraiment quitter sans sauvegarder ?", icon='warning', parent=self):
                self.destroy()
        else:
            self.destroy()

    def _create_entry_with_keyboard(self, parent, text_variable):
        frame = ttk.Frame(parent)
        entry = ttk.Entry(frame, textvariable=text_variable, width=25)
        entry.pack(side="left", expand=True, fill="x")
        btn = tk.Button(frame, text="🇸🇦", font=('Arial', 10), command=lambda: ArabicKeyboard(self, entry), bd=1)
        btn.pack(side="left", padx=(5,0))
        frame.columnconfigure(0, weight=1)
        return frame
        
    def _create_date_entry(self, parent, text_variable, row, col):
        entry = ttk.Entry(parent, textvariable=text_variable, width=20)
        entry.grid(row=row, column=col, sticky="w", padx=5)
        btn = ttk.Button(parent, text="📅", width=3, command=lambda: DatePickerWindow(self, entry, self.manager))
        btn.grid(row=row, column=col+1, sticky="w")
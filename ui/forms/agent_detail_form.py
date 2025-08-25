# Fichier : ui/forms/agent_detail_form.py
# NOUVEAU FORMULAIRE - Version avancée avec champs conditionnels et nouveaux champs.

import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict
import logging

from utils.config_loader import CONFIG
from ui.widgets.arabic_keyboard import ArabicKeyboard
from ui.widgets.date_picker import DatePickerWindow
from utils.date_utils import format_date_for_display

class AgentDetailForm(tk.Toplevel):
    def __init__(self, parent, manager, agent_id_to_modify=None, on_close_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.manager = manager
        self.agent_id = agent_id_to_modify
        self.is_modification = agent_id_to_modify is not None
        self.on_close_callback = on_close_callback

        title = "Modifier les Détails de l'Agent" if self.is_modification else "Ajouter un Nouvel Agent"
        self.title(title)
        self.grab_set()
        self.geometry("750x700")
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)

        self.vars = defaultdict(tk.StringVar)
        self.cadre_var = tk.StringVar()
        self.has_changed = False

        self._create_widgets()

        if self.is_modification:
            self._populate_data()
        
        for var in list(self.vars.values()) + [self.cadre_var]:
            var.trace_add("write", self._set_changed_flag)
        
        # On écoute aussi les changements sur le statut du contrat pour les résidents
        self.vars['statut_contrat_resident'].trace_add("write", self._on_cadre_change)
        
        self._on_cadre_change()
        self.after(100, lambda: self.__setattr__('has_changed', False))

    def _set_changed_flag(self, *args):
        self.has_changed = True

    def _populate_data(self):
        self.has_changed = False
        agent = self.manager.get_agent_by_id(self.agent_id)
        if not agent:
            messagebox.showerror("Erreur", "Agent introuvable.", parent=self); self.destroy(); return

        fields = ['nom', 'nom_arabe', 'prenom', 'prenom_arabe', 'ppr', 'cnie', 'sexe',
                  'situation_familiale', 'type_recrutement', 'statut_hierarchique', 'specialite', 
                  'service_affectation', 'telephone_pro', 'email_pro', 'motif_cessation_service']
        for field in fields:
            self.vars[field].set(getattr(agent, field, '') or '')
        
        self.cadre_var.set(agent.cadre)
        
        self.vars['date_prise_service'].set(format_date_for_display(agent.date_prise_service))
        self.vars['date_cessation_service'].set(format_date_for_display(agent.date_cessation_service))
        
        if agent.profil:
            if "résident" in agent.cadre.lower():
                self.vars['type_residanat'].set(agent.profil.type_residanat or '')
                self.vars['statut_contrat_resident'].set(agent.profil.statut_contrat or '')
                self.vars['date_fin_formation'].set(format_date_for_display(agent.profil.date_fin_formation))
            elif "interne" in agent.cadre.lower():
                self.vars['site_stage_1'].set(agent.profil.site_stage_1 or '')
                self.vars['site_stage_2'].set(agent.profil.site_stage_2 or '')
                self.vars['site_stage_3'].set(agent.profil.site_stage_3 or '')
                self.vars['site_stage_4'].set(agent.profil.site_stage_4 or '')
                self.vars['prolongation'].set(agent.profil.prolongation or '')

        self.after(100, lambda: self.__setattr__('has_changed', False))

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(main_frame, padding=(10, 10))
        btn_frame.pack(fill="x", side="bottom")
        ttk.Button(btn_frame, text="Valider", command=self._on_validate).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Annuler", command=self._on_close_button).pack(side=tk.RIGHT, padx=5)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=(15, 15))

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._create_personnel_section(scrollable_frame)
        self._create_poste_section(scrollable_frame)
        self._create_profil_specific_frames(scrollable_frame)

    def _create_personnel_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Informations Personnelles", padding=10)
        frame.pack(fill="x", pady=5)
        
        ttk.Label(frame, text="Nom:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['nom'], width=30).grid(row=0, column=1, sticky="ew")
        
        ttk.Label(frame, text="الاسم العائلي:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self._create_entry_with_keyboard(frame, self.vars['nom_arabe']).grid(row=1, column=1, sticky="ew")

        ttk.Label(frame, text="Prénom:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['prenom'], width=30).grid(row=2, column=1, sticky="ew")

        ttk.Label(frame, text="الاسم الشخصي:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self._create_entry_with_keyboard(frame, self.vars['prenom_arabe']).grid(row=3, column=1, sticky="ew")
        
        ttk.Label(frame, text="Sexe:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.vars['sexe'], values=["", "Homme", "Femme"], state="readonly").grid(row=4, column=1, sticky="ew")
        
        ttk.Label(frame, text="CNIE:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['cnie']).grid(row=5, column=1, sticky="ew")

        ttk.Label(frame, text="Situation Familiale:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.vars['situation_familiale'], values=["", "Célibataire", "Marié(e)", "Divorcé(e)", "Veuf(ve)"], state="readonly").grid(row=6, column=1, sticky="ew")

        ttk.Label(frame, text="Téléphone:").grid(row=7, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['telephone_pro']).grid(row=7, column=1, sticky="ew")

        ttk.Label(frame, text="Email:").grid(row=8, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['email_pro']).grid(row=8, column=1, sticky="ew")
        
        frame.columnconfigure(1, weight=1)

    def _create_poste_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Poste & Carrière", padding=10)
        frame.pack(fill="x", pady=5)
        
        cadres = CONFIG['ui'].get('grades', [])
        ttk.Label(frame, text="Cadre / Grade:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.combo_cadre = ttk.Combobox(frame, textvariable=self.cadre_var, values=[""] + cadres, state="readonly")
        self.combo_cadre.grid(row=0, column=1, sticky="ew", columnspan=2)
        self.combo_cadre.bind("<<ComboboxSelected>>", self._on_cadre_change)

        self.ppr_label = ttk.Label(frame, text="PPR:")
        self.ppr_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ppr_entry = ttk.Entry(frame, textvariable=self.vars['ppr'])
        self.ppr_entry.grid(row=1, column=1, sticky="ew", columnspan=2)
        
        ttk.Label(frame, text="Spécialité:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['specialite']).grid(row=2, column=1, sticky="ew", columnspan=2)

        ttk.Label(frame, text="Service d'affectation:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.vars['service_affectation']).grid(row=3, column=1, sticky="ew", columnspan=2)

        ttk.Label(frame, text="Statut Hiérarchique:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.vars['statut_hierarchique'], state="readonly", values=["", "Normal", "Chef de service", "Chef de division"]).grid(row=4, column=1, sticky="ew", columnspan=2)

        ttk.Label(frame, text="Type Recrutement:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.vars['type_recrutement'], values=["", "Recrutement", "Détachement", "Mutation"], state="readonly").grid(row=5, column=1, sticky="ew", columnspan=2)
        
        ttk.Label(frame, text="Date prise de service:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
        self._create_date_entry(frame, self.vars['date_prise_service'], 6, 1)

        ttk.Label(frame, text="Date cessation de service:").grid(row=7, column=0, sticky="w", padx=5, pady=5)
        self._create_date_entry(frame, self.vars['date_cessation_service'], 7, 1)
        
        ttk.Label(frame, text="Motif cessation:").grid(row=8, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(frame, textvariable=self.vars['motif_cessation_service'], values=["", "Démission", "Retraite", "Mutation", "Fin de contrat"]).grid(row=8, column=1, sticky="ew", columnspan=2)

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

        self.interne_frame = ttk.LabelFrame(parent, text="Détails de l'Internat", padding=10)
        ttk.Label(self.interne_frame, text="Site de stage 1:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(self.interne_frame, textvariable=self.vars['site_stage_1']).grid(row=0, column=1, sticky="ew")
        ttk.Label(self.interne_frame, text="Site de stage 2:").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(self.interne_frame, textvariable=self.vars['site_stage_2']).grid(row=1, column=1, sticky="ew")
        ttk.Label(self.interne_frame, text="Site de stage 3:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(self.interne_frame, textvariable=self.vars['site_stage_3']).grid(row=2, column=1, sticky="ew")
        ttk.Label(self.interne_frame, text="Site de stage 4:").grid(row=3, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(self.interne_frame, textvariable=self.vars['site_stage_4']).grid(row=3, column=1, sticky="ew")
        ttk.Label(self.interne_frame, text="Prolongation:").grid(row=4, column=0, sticky="w", padx=5, pady=3)
        ttk.Entry(self.interne_frame, textvariable=self.vars['prolongation']).grid(row=4, column=1, sticky="ew")
        self.interne_frame.columnconfigure(1, weight=1)

    def _on_cadre_change(self, *args):
        cadre_lower = self.cadre_var.get().lower()
        
        if "résident" in cadre_lower: self.resident_frame.pack(fill="x", pady=5)
        else: self.resident_frame.pack_forget()
            
        if "interne" in cadre_lower: self.interne_frame.pack(fill="x", pady=5)
        else: self.interne_frame.pack_forget()

        statut_contrat_resident = self.vars['statut_contrat_resident'].get()
        is_benevole = ("interne" in cadre_lower) or ("résident" in cadre_lower and statut_contrat_resident == "Bénévole")
        
        if is_benevole:
            self.ppr_label.grid_forget()
            self.ppr_entry.grid_forget()
        else:
            self.ppr_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
            self.ppr_entry.grid(row=1, column=1, sticky="ew", columnspan=2)

    def _on_validate(self):
        try:
            agent_data = {field: var.get() for field, var in self.vars.items()}
            agent_data['cadre'] = self.cadre_var.get()
            
            if not agent_data['nom'] or not agent_data['cadre']: raise ValueError("Le nom et le cadre sont obligatoires.")

            if self.is_modification:
                agent_data['id'] = self.agent_id
            
            self.manager.save_full_agent(agent_data, self.is_modification)
            
            new_agent_id = self.agent_id if self.is_modification else self.manager.db.execute_query("SELECT id FROM agents WHERE ppr=?", (agent_data['ppr'],), fetch="one")['id']

            messagebox.showinfo("Succès", "Agent enregistré avec succès.", parent=self)
            
            if self.on_close_callback:
                self.on_close_callback(new_agent_id)
            self.destroy()
            
        except Exception as e:
            logging.error(f"Erreur validation agent_detail_form: {e}", exc_info=True)
            messagebox.showerror("Erreur de validation", str(e), parent=self)

    def _on_close_button(self):
        if self.has_changed:
            if messagebox.askyesno("Modifications non enregistrées", "Quitter sans sauvegarder ?", icon='warning', parent=self):
                self.destroy()
        else:
            self.destroy()

    def _create_entry_with_keyboard(self, parent, text_variable):
        frame = ttk.Frame(parent)
        entry = ttk.Entry(frame, textvariable=text_variable, width=25)
        entry.pack(side="left", expand=True, fill="x")
        btn = tk.Button(frame, text="🇸🇦", font=('Arial', 10), command=lambda: ArabicKeyboard(self, entry), bd=1)
        btn.pack(side="left", padx=(5,0))
        return frame
        
    def _create_date_entry(self, parent, text_variable, row, col):
        entry = ttk.Entry(parent, textvariable=text_variable, width=20)
        entry.grid(row=row, column=col, sticky="w", padx=5)
        btn = ttk.Button(parent, text="📅", width=3, command=lambda: DatePickerWindow(self, entry, self.manager))
        btn.grid(row=row, column=col+1, sticky="w")
# Fichier : ui/agent_profile_window.py
# VERSION FINALE - Refonte de la mise en page sans onglets, avec défilement et féminisation.

import tkinter as tk
from tkinter import ttk, messagebox

from utils.date_utils import format_date_for_display

def feminize(titre, sexe):
    """Simple fonction pour féminiser les titres."""
    if sexe != "Femme" or not titre:
        return titre
    
    titres = {
        "Administrateur": "Administratrice", "Ingénieur": "Ingénieure",
        "Technicien": "Technicienne", "Infirmier": "Infirmière",
        "Surveillant Général": "Surveillante Générale", "Chef de service": "Cheffe de service",
        "Chef de division": "Cheffe de division", "Professeur": "Professeure",
        "Assistant": "Assistante", "Agrégé": "Agrégée", "Médecin": "Médecin"
    }
    
    for masculin, feminin in titres.items():
        if masculin in titre:
            return titre.replace(masculin, feminin)
            
    return titre

class AgentProfileWindow(tk.Toplevel):
    def __init__(self, parent, manager, agent_id):
        super().__init__(parent)
        self.manager = manager
        
        self.agent = self.manager.get_agent_by_id(agent_id)
        if not self.agent:
            messagebox.showerror("Erreur", "Impossible de charger les données de l'agent.", parent=parent)
            self.destroy(); return

        self.title(f"Fiche de l'Agent : {self.agent.nom} {self.agent.prenom}")
        self.grab_set()
        self.geometry("750x600")
        self.resizable(True, True)

        self._create_widgets()
        self.transient(parent)
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Button(main_frame, text="Fermer", command=self.destroy).pack(side="bottom", pady=10)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=(15, 15))

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Création des sections dans le cadre défilant ---
        self._create_general_info_section(scrollable_frame)
        self._create_career_section(scrollable_frame)
        if self.agent.profil:
            self._create_resident_profile_section(scrollable_frame)
        self._create_history_section(scrollable_frame)
        self._create_solde_section(scrollable_frame)

    def _create_info_row(self, parent, label, value, row):
        ttk.Label(parent, text=f"{label}:", font=('Helvetica', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(parent, text=value or '-', wraplength=500).grid(row=row, column=1, sticky="w", padx=5, pady=3)

    def _create_general_info_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Informations Générales", padding=10)
        frame.pack(fill="x", pady=5)
        self._create_info_row(frame, "Nom complet", f"{self.agent.nom} {self.agent.prenom}", 0)
        self._create_info_row(frame, "اسم الكامل", f"{self.agent.nom_arabe} {self.agent.prenom_arabe}", 1)
        self._create_info_row(frame, "Sexe", self.agent.sexe, 2)
        self._create_info_row(frame, "PPR", self.agent.ppr, 3)
        self._create_info_row(frame, "CNIE", self.agent.cnie, 4)
        self._create_info_row(frame, "Téléphone", self.agent.telephone_pro, 5)
        self._create_info_row(frame, "Email", self.agent.email_pro, 6)
        
    def _create_career_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Poste & Carrière", padding=10)
        frame.pack(fill="x", pady=5)
        sexe = self.agent.sexe
        self._create_info_row(frame, "Cadre / Grade", feminize(self.agent.cadre, sexe), 0)
        self._create_info_row(frame, "Spécialité", self.agent.specialite, 1)
        self._create_info_row(frame, "Service d'affectation", self.agent.service_affectation, 2)
        self._create_info_row(frame, "Statut hiérarchique", feminize(self.agent.statut_hierarchique, sexe), 3)
        self._create_info_row(frame, "Type de recrutement", self.agent.type_recrutement, 4)
        self._create_info_row(frame, "Date de prise de service", format_date_for_display(self.agent.date_prise_service), 5)
        self._create_info_row(frame, "Date de cessation de service", format_date_for_display(self.agent.date_cessation_service), 6)
        self._create_info_row(frame, "Motif de cessation", self.agent.motif_cessation_service, 7)

    def _create_resident_profile_section(self, parent):
        if not (self.agent.profil and "résident" in self.agent.cadre.lower()): return
        frame = ttk.LabelFrame(parent, text="Détails du Résidanat", padding=10)
        frame.pack(fill="x", pady=5)
        self._create_info_row(frame, "Type de Résidanat", self.agent.profil.type_residanat, 0)
        self._create_info_row(frame, "Statut du contrat", self.agent.profil.statut_contrat, 1)
        self._create_info_row(frame, "Date de fin de formation", format_date_for_display(self.agent.profil.date_fin_formation), 2)
        
    def _create_history_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Historique de Carrière", padding=10)
        frame.pack(fill="both", expand=True, pady=5)
        cols = ("Date", "Type", "Service", "Spécialité", "Centre", "Détails")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=5)
        for col in cols: tree.heading(col, text=col); tree.column(col, width=110, anchor='center')
        tree.column("Détails", width=150)
        
        for event in self.agent.historique:
            tree.insert("", "end", values=(
                format_date_for_display(event.date_evenement), event.type_evenement,
                event.service_affectation or '-', event.specialite or '-',
                event.centre_formation or '-', event.details or ''
            ))
        tree.pack(fill="both", expand=True)

    def _create_solde_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Soldes de Congés", padding=10)
        frame.pack(fill="both", expand=True, pady=5)
        cols = ("Année", "Solde (j)", "Statut")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=3)
        for col in cols: tree.heading(col, text=col)
        
        tree.column("Année", anchor='center', width=100)
        tree.column("Solde (j)", anchor='center', width=120)
        tree.column("Statut", anchor='center', width=100)

        if self.agent.soldes_annuels:
            for solde in sorted(self.agent.soldes_annuels, key=lambda s: s.annee, reverse=True):
                tree.insert("", "end", values=(solde.annee, f"{solde.solde:.1f}", solde.statut))
        tree.pack(fill="both", expand=True)
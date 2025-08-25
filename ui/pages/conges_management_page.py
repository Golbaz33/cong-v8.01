# Fichier : ui/pages/conges_management_page.py
# VERSION FINALE - Connexion aux fenêtres "Modifier Soldes" et "Synthèse Agent".

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime, date
from collections import defaultdict

from ui.panels.agents_panel import AgentsPanel
from utils.date_utils import format_date_for_display_short, calculate_reprise_date, format_date_for_display
from utils.config_loader import CONFIG
from ui.forms.conge_form import CongeForm
from ui.forms.solde_form import SoldeForm
from ui.agent_synthesis_window import AgentSynthesisWindow
from ui.ui_utils import treeview_sort_column
from utils.file_utils import generate_decision_from_template

class CongesManagementPage(ttk.Frame):
    def __init__(self, parent, main_app, manager):
        super().__init__(parent)
        self.main_app = main_app
        self.manager = manager
        
        self._create_widgets()

    def _create_widgets(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        self.agents_panel = AgentsPanel(parent_widget=main_pane, main_app=self.main_app, manager=self.manager, 
                                        base_dir=self.main_app.base_dir, on_agent_select_callback=self._on_agent_select)
        main_pane.add(self.agents_panel, weight=2)

        self.conges_details_panel = CongesDetailsPanel(parent=main_pane, main_app=self.main_app, manager=self.manager)
        main_pane.add(self.conges_details_panel, weight=3)
    
    def _on_agent_select(self, agent_id):
        self.conges_details_panel.display_conges_for_agent(agent_id)

    def refresh_all(self, agent_to_select_id=None):
        self.agents_panel.refresh_agents_list(agent_to_select_id)
        if agent_to_select_id is None:
            selected_ids = self.agents_panel.get_selected_agent_ids()
            agent_to_select_id = selected_ids[0] if selected_ids else None
        self.conges_details_panel.display_conges_for_agent(agent_to_select_id)

class CongesDetailsPanel(ttk.Frame):
    def __init__(self, parent, main_app, manager):
        super().__init__(parent)
        self.main_app = main_app
        self.manager = manager
        self.current_agent_id = None
        self._create_widgets()

    def _create_widgets(self):
        parent_tab = ttk.Frame(self, padding=5)
        parent_tab.pack(fill="both", expand=True, padx=(5,0))

        self.conge_filter_var = tk.StringVar(value="Tous")
        
        filter_frame = ttk.Frame(parent_tab)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(filter_frame, text="Filtrer:").pack(side=tk.LEFT, padx=(0, 5))
        self.conge_filter_combo = ttk.Combobox(filter_frame, textvariable=self.conge_filter_var, 
                                          values=["Tous"] + CONFIG['ui']['types_conge'], state="readonly")
        self.conge_filter_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.conge_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.display_conges_for_agent(self.current_agent_id))

        cols_conges = ("CongeID", "Certificat", "Type", "Début", "Fin", "Reprise", "Jours")
        self.list_conges = ttk.Treeview(parent_tab, columns=cols_conges, show="headings", selectmode="browse")
        
        for col in cols_conges:
            self.list_conges.heading(col, text=col, command=lambda c=col: treeview_sort_column(self.list_conges, c, False))
        
        self.list_conges.column("CongeID", width=0, stretch=False)
        self.list_conges.column("Certificat", width=80, anchor="center")
        self.list_conges.column("Type", width=120)
        self.list_conges.column("Jours", width=50, anchor="center")
        self.list_conges.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.list_conges.tag_configure("summary", background="#e6f2ff", font=("Helvetica", 10, "bold"))
        self.list_conges.tag_configure("annule", foreground="grey", font=('Helvetica', 10, 'overstrike'))
        
        self.list_conges.bind("<Double-1>", self.on_conge_double_click)
        self.list_conges.bind("<<TreeviewSelect>>", self._update_conge_action_buttons_state)

        btn_frame_conges = ttk.Frame(parent_tab)
        btn_frame_conges.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.add_conge_btn = ttk.Button(btn_frame_conges, text="Ajouter Congé", command=self.add_conge_ui)
        self.add_conge_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.modify_conge_btn = ttk.Button(btn_frame_conges, text="Modifier Congé", command=self.modify_selected_conge)
        self.modify_conge_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.delete_conge_btn = ttk.Button(btn_frame_conges, text="Supprimer Congé", command=self.delete_selected_conge)
        self.delete_conge_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.solde_btn = ttk.Button(btn_frame_conges, text="Modifier Soldes", command=self._open_solde_editor)
        self.solde_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.decision_conge_btn = ttk.Button(btn_frame_conges, text="Générer Décision", command=self.on_generate_decision_click)
        self.decision_conge_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self._update_conge_action_buttons_state()
    
    def display_conges_for_agent(self, agent_id):
        self.current_agent_id = agent_id
        self.list_conges.delete(*self.list_conges.get_children())
        if not agent_id:
            self._update_conge_action_buttons_state()
            return

        filtre = self.conge_filter_var.get()
        conges_data = self.manager.get_conges_for_agent(agent_id)
        
        conges_par_annee = defaultdict(list)
        for c in conges_data:
            if filtre != "Tous" and c.type_conge != filtre: continue
            if c.date_debut:
                conges_par_annee[c.date_debut.year].append(c)

        for annee in sorted(conges_par_annee.keys(), reverse=True):
            total_jours = sum(c.jours_pris for c in conges_par_annee[annee] if c.type_conge == 'Congé annuel' and c.statut == 'Actif')
            summary_id = self.list_conges.insert("", "end", values=("", "", f"📅 ANNÉE {annee}", "", "", f"Total: {total_jours} j", ""), tags=("summary",), open=True)
            
            holidays_set = self.manager.get_holidays_set_for_period(annee, annee + 1)
            for conge in sorted(conges_par_annee[annee], key=lambda c: c.date_debut):
                cert_status = "✅" if self.manager.get_certificat_for_conge(conge.id) else "❌" if conge.type_conge == 'Congé de maladie' else ""
                reprise = calculate_reprise_date(conge.date_fin, holidays_set)
                tags = ('annule',) if conge.statut == 'Annulé' else ()
                
                self.list_conges.insert(summary_id, "end", values=(
                    conge.id, cert_status, conge.type_conge, 
                    format_date_for_display_short(conge.date_debut), 
                    format_date_for_display_short(conge.date_fin), 
                    format_date_for_display_short(reprise) if reprise else "",
                    conge.jours_pris
                ), tags=tags)
        
        self._update_conge_action_buttons_state()

    def get_selected_conge_id(self):
        selection = self.list_conges.selection()
        if not selection: return None
        item = self.list_conges.item(selection[0])
        if "summary" in item["tags"] or not item["values"] or not item["values"][0]:
            return None
        return int(item["values"][0])

    def _update_conge_action_buttons_state(self, event=None):
        agent_selected = self.current_agent_id is not None
        conge_selected = self.get_selected_conge_id() is not None
        
        self.add_conge_btn.config(state="normal" if agent_selected else "disabled")
        self.solde_btn.config(state="normal" if agent_selected else "disabled")
        self.modify_conge_btn.config(state="normal" if conge_selected else "disabled")
        self.delete_conge_btn.config(state="normal" if conge_selected else "disabled")
        self.decision_conge_btn.config(state="normal" if conge_selected else "disabled")

    def _open_solde_editor(self):
        if self.current_agent_id:
            SoldeForm(self.main_app, self.manager, self.current_agent_id)

    def add_conge_ui(self):
        if self.current_agent_id:
            CongeForm(self.main_app, self.manager, self.current_agent_id)

    def modify_selected_conge(self):
        conge_id = self.get_selected_conge_id()
        if conge_id and self.current_agent_id:
            CongeForm(self.main_app, self.manager, self.current_agent_id, conge_id=conge_id)

    def delete_selected_conge(self):
        conge_id = self.get_selected_conge_id()
        if not conge_id: return
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir supprimer ce congé ?"):
            try:
                if self.manager.delete_conge(conge_id):
                    self.main_app.set_status("Congé supprimé.")
                    self.main_app.pages["CongesManagementPage"].refresh_all(self.current_agent_id)
            except Exception as e:
                messagebox.showerror("Erreur de suppression", str(e))

    def on_conge_double_click(self, event=None):
        conge_id = self.get_selected_conge_id()
        if not conge_id: return
        cert = self.manager.get_certificat_for_conge(conge_id)
        if cert and cert['chemin_fichier'] and os.path.exists(cert['chemin_fichier']):
            self.main_app._open_file(cert['chemin_fichier'])
        else:
            self.modify_selected_conge()
    
    def on_generate_decision_click(self):
        conge_id = self.get_selected_conge_id()
        if not self.current_agent_id or not conge_id: return

        agent = self.manager.get_agent_by_id(self.current_agent_id)
        conge = self.manager.get_conge_by_id(conge_id)
        if not conge or not agent: return
        
        holidays_set = self.manager.get_holidays_set_for_period(conge.date_fin.year, conge.date_fin.year + 1)
        date_reprise = calculate_reprise_date(conge.date_fin, holidays_set)
        
        details_solde_str = ""
        if conge.type_conge == "Congé annuel":
            details = self.manager.get_deduction_details(agent.id, conge.jours_pris)
            parts = [f"{int(round(days))} {'jour' if int(round(days)) == 1 else 'jours'} au titre de l'année {year}" for year, days in sorted(details.items())]
            details_solde_str = " et ".join(parts)

        context = {
            "{{nom_complet}}": f"{agent.nom} {agent.prenom}", "{{grade}}": agent.cadre, "{{ppr}}": agent.ppr,
            "{{date_debut}}": format_date_for_display(conge.date_debut), "{{date_fin}}": format_date_for_display(conge.date_fin),
            "{{date_reprise}}": format_date_for_display(date_reprise) if date_reprise else "N/A",
            "{{jours_pris}}": str(conge.jours_pris), "{{details_solde}}": details_solde_str,
            "{{date_aujourdhui}}": date.today().strftime("%d/%m/%Y")
        }
        
        templates_dir_name = CONFIG.get('paths', {}).get('templates_dir', 'templates')
        grade_str = agent.cadre.lower().replace(" ", "_")
        template_name = f"{grade_str}.docx"
        template_path = os.path.join(self.main_app.base_dir, templates_dir_name, template_name)
        
        if not os.path.exists(template_path):
            messagebox.showerror("Modèle manquant", f"Le modèle '{template_name}' est introuvable.", parent=self.main_app)
            return

        initial_filename = f"Decision_Conge_{agent.nom}_{conge.date_debut.strftime('%Y-%m-%d')}.docx"
        save_path = filedialog.asksaveasfilename(
            title="Enregistrer la décision", initialfile=initial_filename, defaultextension=".docx",
            filetypes=[("Documents Word", "*.docx")]
        )
        if not save_path: return

        try:
            generate_decision_from_template(template_path, save_path, context)
            if messagebox.askyesno("Succès", "La décision a été générée.\nVoulez-vous ouvrir le fichier ?", parent=self.main_app):
                self.main_app._open_file(save_path)
        except Exception as e:
            messagebox.showerror("Erreur de Génération", f"Une erreur est survenue:\n{e}", parent=self.main_app)
# Fichier : ui/pages/administration_page.py
# NOUVEAU FICHIER - Page dédiée aux tâches administratives globales.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import shutil
import sys

try:
    import holidays
except ImportError:
    pass

from ui.widgets.date_picker import DatePickerWindow
from utils.date_utils import validate_date, format_date_for_display
from utils.config_loader import CONFIG
from ui.widgets.secondary_windows import BackupWindow, EditHolidayWindow

class AdministrationPage(ttk.Frame):
    def __init__(self, parent, main_app, manager):
        super().__init__(parent)
        self.main_app = main_app
        self.manager = manager
        
        self.annee_exercice = self.manager.get_annee_exercice()
        
        self._create_widgets()
        
    def _create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_gestion = ttk.Frame(notebook)
        tab_feries = ttk.Frame(notebook)
        
        notebook.add(tab_gestion, text=" Gestion Annuelle et Sauvegardes ")
        notebook.add(tab_feries, text=" Jours Fériés Personnalisés ")
        
        self._populate_gestion_tab(tab_gestion)
        self._populate_feries_tab(tab_feries)
        
    def _populate_gestion_tab(self, parent_frame):
        main_pane = ttk.PanedWindow(parent_frame, orient=tk.VERTICAL)
        main_pane.pack(fill="both", expand=True, pady=5, padx=5)
        
        glissement_frame = ttk.LabelFrame(main_pane, text="Clôture de l'Exercice Annuel", padding=10)
        main_pane.add(glissement_frame, weight=1)
        
        self.glissement_label = ttk.Label(glissement_frame, text=f"L'exercice actuel est {self.annee_exercice}. La clôture mettra à jour l'application pour l'exercice {self.annee_exercice + 1}.\nLe solde de l'année {self.annee_exercice - 2} passera au statut 'Expiré'.", wraplength=700)
        self.glissement_label.pack(pady=5, fill="x")
        
        self.glissement_btn = ttk.Button(glissement_frame, text=f"Clôturer l'exercice {self.annee_exercice}", command=self._run_glissement_annuel)
        self.glissement_btn.pack(pady=10)
        
        backup_btn = ttk.Button(glissement_frame, text="Gérer les Sauvegardes / Restaurer", command=self._open_backup_window)
        backup_btn.pack(pady=5)
        
        apurement_frame = ttk.LabelFrame(main_pane, text="Apurement des Soldes Expirés", padding=10)
        main_pane.add(apurement_frame, weight=3)
        
        cols = ("id", "Agent", "Année du Solde", "Jours Expirés")
        self.tree_expires = ttk.Treeview(apurement_frame, columns=cols, show="headings", selectmode="extended")
        self.tree_expires.heading("Agent", text="Agent")
        self.tree_expires.heading("Année du Solde", text="Année du Solde")
        self.tree_expires.heading("Jours Expirés", text="Jours Expirés")
        self.tree_expires.column("id", width=0, stretch=False)
        self.tree_expires.pack(fill="both", expand=True, pady=5)
        
        apurement_btn = ttk.Button(apurement_frame, text="Apurer les soldes sélectionnés (mettre à 0)", command=self._run_apurement)
        apurement_btn.pack(pady=5)
        
    def _populate_feries_tab(self, parent_frame):
        main_frame = ttk.Frame(parent_frame, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        top_frame = ttk.LabelFrame(main_frame, text="Jours Fériés Enregistrés")
        top_frame.pack(fill="x", pady=5, padx=5)
        
        year_frame = ttk.Frame(top_frame, padding=5)
        year_frame.pack(fill="x")
        
        ttk.Label(year_frame, text="Année:").pack(side="left")
        current_year = datetime.now().year
        self.year_var = tk.StringVar(value=str(current_year))
        self.year_spinbox = ttk.Spinbox(year_frame, from_=current_year - 5, to=current_year + 5, textvariable=self.year_var, width=8, command=self.refresh_holidays_list)
        self.year_spinbox.pack(side="left", padx=5)
        
        cols = ("Date", "Description", "Type")
        self.holidays_tree = ttk.Treeview(top_frame, columns=cols, show="headings", height=10)
        for col in cols: self.holidays_tree.heading(col, text=col)
        self.holidays_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(pady=5, fill="x", padx=5)
        ttk.Button(action_frame, text="Supprimer le jour sélectionné", command=self._delete_holiday).pack(side="right")
        ttk.Button(action_frame, text="Modifier le jour sélectionné", command=self._edit_holiday).pack(side="right", padx=(0, 10))
        
        bottom_frame = ttk.LabelFrame(main_frame, text="Ajouter un Jour Férié Personnalisé")
        bottom_frame.pack(fill="x", pady=5, padx=5)
        
        add_frame = ttk.Frame(bottom_frame, padding=5)
        add_frame.pack()
        
        ttk.Label(add_frame, text="Date:").grid(row=0, column=0, sticky="w", pady=2)
        self.date_entry = ttk.Entry(add_frame, width=15)
        self.date_entry.grid(row=0, column=1, padx=5)
        ttk.Button(add_frame, text="📅", width=2, command=lambda: DatePickerWindow(self.main_app, self.date_entry, self.manager)).grid(row=0, column=2)
        
        ttk.Label(add_frame, text="Description:").grid(row=1, column=0, sticky="w", pady=2)
        self.desc_entry = ttk.Entry(add_frame, width=30)
        self.desc_entry.grid(row=1, column=1, columnspan=2, padx=5)
        
        ttk.Button(bottom_frame, text="Ajouter ce jour férié", command=self.add_holiday).pack(pady=5)

    def refresh_all(self, agent_to_select_id=None):
        self.annee_exercice = self.manager.get_annee_exercice()
        self.glissement_label.config(text=f"L'exercice actuel est {self.annee_exercice}. La clôture mettra à jour l'application pour l'exercice {self.annee_exercice + 1}.\nLe solde de l'année {self.annee_exercice - 2} passera au statut 'Expiré'.")
        self.glissement_btn.config(text=f"Clôturer l'exercice {self.annee_exercice}")
        self.refresh_soldes_expires_list()
        self.refresh_holidays_list()
        
    def refresh_soldes_expires_list(self):
        for row in self.tree_expires.get_children(): self.tree_expires.delete(row)
        try:
            soldes_expires = self.manager.get_soldes_expires()
            for solde_id, nom, prenom, annee, solde in soldes_expires:
                agent_name = f"{nom} {prenom}"
                self.tree_expires.insert("", "end", values=(solde_id, agent_name, annee, f"{solde:.1f} j"))
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les soldes expirés : {e}", parent=self)
            
    def _open_backup_window(self):
        BackupWindow(self.main_app, self.manager, self.main_app)
        
    def _run_glissement_annuel(self):
        if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir clôturer l'exercice {self.annee_exercice} ?\nCette action est IRRÉVERSIBLE.", icon='warning', parent=self):
            try:
                db_path = self.manager.db.get_db_path()
                backup_filename = f"backup_{datetime.now():%Y-%m-%d_%H-%M-%S}_AVANT_CLOTURE_{self.annee_exercice}.db"
                backup_path = os.path.join(os.path.dirname(db_path), "backups", backup_filename)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(db_path, backup_path)
            except Exception as e:
                messagebox.showerror("Échec de la Sauvegarde", f"La sauvegarde automatique a échoué. Opération annulée.\n\nErreur : {e}", parent=self)
                return
            
            try:
                self.manager.effectuer_glissement_annuel()
                messagebox.showinfo("Succès", "Le glissement annuel a été effectué.\nUne sauvegarde a été créée.\n\nL'application va maintenant redémarrer.", parent=self)
                self.main_app.trigger_restart()
            except Exception as e:
                messagebox.showerror("Erreur de Clôture", f"Le glissement a échoué : {e}", parent=self)

    def _run_apurement(self):
        selection = self.tree_expires.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner les soldes à apurer.", parent=self)
            return
        
        solde_ids = [self.tree_expires.item(item, "values")[0] for item in selection]
        if messagebox.askyesno("Confirmation", f"Mettre à zéro les {len(solde_ids)} soldes expirés sélectionnés ?\nCette action est irréversible.", parent=self):
            try:
                self.manager.apurer_soldes(solde_ids)
                self.refresh_soldes_expires_list()
            except Exception as e:
                messagebox.showerror("Erreur", f"L'apurement a échoué : {e}", parent=self)

    def refresh_holidays_list(self):
        for row in self.holidays_tree.get_children(): self.holidays_tree.delete(row)
        try:
            year = int(self.year_var.get())
            country_code = CONFIG['conges']['holidays_country']
            all_holidays = {}
            if 'holidays' in sys.modules:
                 for h_date, h_name in holidays.country_holidays(country_code, years=year).items():
                    all_holidays[h_date] = (h_name, "Officiel")
            
            for date_str, name, h_type in self.manager.get_holidays_for_year(str(year)):
                validated_date = validate_date(date_str)
                if validated_date: all_holidays[validated_date.date()] = (name, h_type)

            for h_date, (h_name, h_type) in sorted(all_holidays.items()):
                self.holidays_tree.insert("", "end", values=(format_date_for_display(h_date), h_name, h_type))
        except (tk.TclError, ValueError): pass
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les jours fériés: {e}", parent=self)

    def _get_selected_holiday_info(self):
        selection = self.holidays_tree.selection()
        if not selection: messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un jour.", parent=self); return None, None
        return self.holidays_tree.item(selection[0], "values")

    def _delete_holiday(self):
        date_str, _, h_type = self._get_selected_holiday_info()
        if not date_str or h_type == "Officiel": return
        
        date_obj = validate_date(date_str)
        if not date_obj: return
        
        if messagebox.askyesno("Confirmation", f"Supprimer le jour férié personnalisé '{date_str}' ?", parent=self):
            if self.manager.delete_holiday(date_obj.strftime('%Y-%m-%d')):
                self.refresh_holidays_list()
            else:
                messagebox.showerror("Échec", "La suppression a échoué.", parent=self)

    def _edit_holiday(self):
        date_str, name, h_type = self._get_selected_holiday_info()
        if not date_str or h_type == "Officiel": return
        EditHolidayWindow(self.main_app, date_str, name, self._process_holiday_update)

    def _process_holiday_update(self, original_date_str, new_date_obj, new_name):
        original_date_sql = validate_date(original_date_str).strftime('%Y-%m-%d')
        new_date_sql = new_date_obj.strftime('%Y-%m-%d')
        if original_date_sql != new_date_sql:
            self.manager.delete_holiday(original_date_sql)
        if self.manager.add_or_update_holiday(new_date_sql, new_name, "Personnalisé"):
            self.refresh_holidays_list()
        else:
            messagebox.showerror("Échec", "La mise à jour a échoué.", parent=self)

    def add_holiday(self):
        date_str = self.date_entry.get(); desc = self.desc_entry.get().strip()
        validated_date = validate_date(date_str)
        if not validated_date or not desc:
            messagebox.showerror("Erreur", "Veuillez entrer une date et une description valides.", parent=self)
            return
        
        if self.manager.add_holiday(validated_date.strftime("%Y-%m-%d"), desc, "Personnalisé"):
            self.desc_entry.delete(0, tk.END); self.date_entry.delete(0, tk.END)
            self.refresh_holidays_list()
        else:
            messagebox.showerror("Erreur", "Cette date est déjà enregistrée.", parent=self)
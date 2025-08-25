# Fichier : ui/widgets/secondary_windows.py
# MISE À JOUR - Suppression de l'ancienne classe AdminWindow.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import shutil
import sqlite3
import sys

try:
    import holidays
except ImportError:
    pass

from ui.widgets.date_picker import DatePickerWindow
from utils.date_utils import validate_date, format_date_for_display
from utils.config_loader import CONFIG

class EditHolidayWindow(tk.Toplevel):
    def __init__(self, parent, original_date, original_name, callback):
        super().__init__(parent)
        self.original_date_str = original_date
        self.callback = callback
        
        self.title("Modifier le Jour Férié")
        self.grab_set()
        self.resizable(False, False)
        
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Date:").grid(row=0, column=0, sticky="w", pady=5)
        self.date_entry = ttk.Entry(frame, width=25)
        self.date_entry.insert(0, original_date)
        self.date_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(frame, text="Nom/Description:").grid(row=1, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(frame, width=25)
        self.name_entry.insert(0, original_name)
        self.name_entry.grid(row=1, column=1, padx=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, columnspan=2, pady=(15, 0))
        
        ttk.Button(btn_frame, text="Valider", command=self._on_validate).pack(side="right")
        ttk.Button(btn_frame, text="Annuler", command=self.destroy).pack(side="right", padx=10)
        
        self.transient(parent)
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")
        self.focus_set()
        self.wait_window()

    def _on_validate(self):
        new_date_str = self.date_entry.get().strip()
        new_name = self.name_entry.get().strip()
        new_date_obj = validate_date(new_date_str)
        
        if not new_date_obj or not new_name:
            messagebox.showerror("Erreur de saisie", "Veuillez entrer une date valide et un nom.", parent=self)
            return
            
        self.callback(self.original_date_str, new_date_obj, new_name)
        self.destroy()

class BackupWindow(tk.Toplevel):
    def __init__(self, parent, manager, main_app_instance):
        super().__init__(parent)
        self.manager = manager
        self.main_app = main_app_instance
        self.db_path = self.manager.db.get_db_path()
        self.base_dir = os.path.dirname(self.db_path)
        self.backups_dir = os.path.join(self.base_dir, "backups")
        
        self.title("Gérer les Sauvegardes et Restaurer")
        self.geometry("700x400")
        self.grab_set()
        self.transient(parent)
        
        self._create_widgets()
        self._populate_backups()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        list_frame = ttk.LabelFrame(main_frame, text="Sauvegardes Disponibles", padding=10)
        list_frame.pack(fill="both", expand=True)
        
        cols = ("Fichier", "Date de création", "Taille")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.tree.heading("Fichier", text="Nom du Fichier")
        self.tree.heading("Date de création", text="Date de création")
        self.tree.heading("Taille", text="Taille")
        self.tree.pack(fill="both", expand=True)
        
        btn_frame = ttk.Frame(main_frame, padding=(0, 10))
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Fermer", command=self.destroy).pack(side="right")
        ttk.Button(btn_frame, text="Restaurer la version sélectionnée", command=self._run_restore).pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Supprimer la sauvegarde", command=self._delete_backup).pack(side="left")

    def _populate_backups(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not os.path.exists(self.backups_dir): return
            
        backups = sorted([f for f in os.listdir(self.backups_dir) if f.endswith((".db", ".sqlite3"))], 
                         key=lambda f: os.path.getmtime(os.path.join(self.backups_dir, f)), reverse=True)
        
        for filename in backups:
            full_path = os.path.join(self.backups_dir, filename)
            try:
                mtime = os.path.getmtime(full_path)
                size = os.path.getsize(full_path)
                date_str = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')
                size_str = f"{size / 1024:.1f} KB"
                self.tree.insert("", "end", values=(filename, date_str, size_str))
            except OSError:
                continue

    def _get_selected_backup_path(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une sauvegarde.", parent=self)
            return None
        filename = self.tree.item(selection[0], "values")[0]
        return os.path.join(self.backups_dir, filename)

    def _delete_backup(self):
        backup_path = self._get_selected_backup_path()
        if not backup_path: return
        if messagebox.askyesno("Confirmation", f"Supprimer définitivement le fichier de sauvegarde ?\n\n{os.path.basename(backup_path)}", parent=self):
            try:
                os.remove(backup_path)
                self._populate_backups()
            except OSError as e:
                messagebox.showerror("Erreur", f"Impossible de supprimer le fichier : {e}", parent=self)
    
    def _run_restore(self):
        backup_path = self._get_selected_backup_path()
        if not backup_path: return
            
        msg = ("Êtes-vous certain de vouloir restaurer cette version ?\n\n"
               "ATTENTION : Toutes les données actuelles seront PERDUES.\n"
               "Cette action est IRRÉVERSIBLE.")
        if messagebox.askyesno("Confirmation de Restauration", msg, icon='warning', parent=self):
            try:
                self.manager.db.close()
                shutil.copy2(backup_path, self.db_path)
                messagebox.showinfo("Restauration Réussie", "Restauration effectuée.\n\nL'application va redémarrer.", parent=self)
                self.main_app.trigger_restart()
            except Exception as e:
                messagebox.showerror("Erreur Critique", f"La restauration a échoué : {e}", parent=self)

class JustificatifsWindow(tk.Toplevel):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self.manager = manager
        self.title("Suivi des Justificatifs Médicaux")
        self.grab_set()
        self.geometry("800x600")
        self.filter_var = tk.StringVar(value="manquant")
        self.search_var = tk.StringVar()
        self._create_widgets()
        self.refresh_list()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        filter_frame = ttk.LabelFrame(main_frame, text="Filtres et Recherche", padding=10)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        status_frame = ttk.Frame(filter_frame)
        status_frame.pack(side="left", fill="x", expand=True)
        ttk.Radiobutton(status_frame, text="Manquants", variable=self.filter_var, value="manquant", command=self.refresh_list).pack(anchor="w")
        ttk.Radiobutton(status_frame, text="Fournis", variable=self.filter_var, value="justifie", command=self.refresh_list).pack(anchor="w")
        ttk.Radiobutton(status_frame, text="Tous", variable=self.filter_var, value="tous", command=self.refresh_list).pack(anchor="w")
        
        search_frame = ttk.Frame(filter_frame)
        search_frame.pack(side="left", fill="x", expand=True, padx=(20, 0))
        ttk.Label(search_frame, text="Rechercher un agent (Nom, Prénom, PPR):").pack(anchor="w")
        
        search_entry_frame = ttk.Frame(search_frame)
        search_entry_frame.pack(fill="x", pady=5)
        search_entry = ttk.Entry(search_entry_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<Return>", lambda event: self.refresh_list())
        clear_btn = ttk.Button(search_entry_frame, text="X", width=3, command=self._clear_search)
        clear_btn.pack(side="left", padx=(5, 0))
        
        ttk.Button(search_frame, text="Rechercher", command=self.refresh_list).pack(anchor="w", pady=5)
        
        cols = ("Agent", "PPR", "Date Début", "Date Fin", "Jours Pris")
        self.tree = ttk.Treeview(main_frame, columns=cols, show="headings", height=10)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
    def _clear_search(self):
        self.search_var.set("")
        self.refresh_list()
        
    def refresh_list(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        try:
            filtre_choisi = self.filter_var.get()
            terme_recherche = self.search_var.get().strip()
            conges_list = self.manager.get_sick_leaves_by_status(status=filtre_choisi, search_term=terme_recherche)
            for row_data in conges_list:
                agent_fullname = f"{row_data['nom']} {row_data['prenom']}"
                ppr = row_data['ppr']
                date_debut = format_date_for_display(row_data['date_debut'])
                date_fin = format_date_for_display(row_data['date_fin'])
                jours_pris = row_data['jours_pris']
                self.tree.insert("", "end", values=(agent_fullname, ppr, date_debut, date_fin, jours_pris))
        except sqlite3.Error as e:
            messagebox.showerror("Erreur BD", f"Impossible de charger la liste : {e}", parent=self)
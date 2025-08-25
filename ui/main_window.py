# Fichier : ui/main_window.py
# VERSION FINALE - Intègre les quatre pages : Gestion Agents, Gestion Congés, Tableau de Bord, Administration.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
import sqlite3
import threading
from datetime import datetime, date
import subprocess
import sys

from core.conges.manager import CongeManager
from utils.file_utils import generate_decision_from_template
from utils.date_utils import format_date_for_display, calculate_reprise_date
from utils.config_loader import CONFIG

from ui.pages.dashboard_page import DashboardPage
from ui.pages.conges_management_page import CongesManagementPage
from ui.pages.agents_management_page import AgentsManagementPage
from ui.pages.administration_page import AdministrationPage


class MainWindow(tk.Tk):
    def __init__(self, manager: CongeManager, base_dir: str):
        super().__init__()
        self.manager = manager
        self.base_dir = base_dir
        self.title(f"{CONFIG['app']['title']} - v{CONFIG['app']['version']} - Refonte UI")
        self.minsize(1400, 700)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.restart_on_close = False
        self.status_var = tk.StringVar(value="Prêt.")

        self.pages = {}

        self.create_widgets()
        
        self.show_page("AgentsManagementPage")

    def on_close(self):
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter ?"):
            self.destroy()

    def trigger_restart(self):
        self.restart_on_close = True
        self.destroy()

    def set_status(self, message):
        self.status_var.set(message)
        self.update_idletasks()

    def show_page(self, page_name):
        """Affiche la page demandée et cache les autres."""
        if page_name not in self.pages:
            self.set_status(f"La page '{page_name}' n'est pas encore disponible.")
            return

        for page in self.pages.values():
            page.pack_forget()
        
        page_to_show = self.pages[page_name]
        page_to_show.pack(fill="both", expand=True, padx=10, pady=(0,10))
        
        if hasattr(page_to_show, 'refresh_all'):
            page_to_show.refresh_all()
        elif hasattr(page_to_show, 'refresh_stats'):
            page_to_show.refresh_stats()

    def create_widgets(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25, font=('Helvetica', 10))
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'), relief="raised")
        style.configure("TLabelframe.Label", font=('Helvetica', 12, 'bold'))
        style.configure("TButton", padding=6)
        
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(side="top", fill="x")

        # --- BARRE D'OUTILS FINALE ---
        ttk.Button(toolbar, text="Gestion des Agents", command=lambda: self.show_page("AgentsManagementPage")).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Gestion des Congés", command=lambda: self.show_page("CongesManagementPage")).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Tableau de Bord", command=lambda: self.show_page("DashboardPage")).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Administration", command=lambda: self.show_page("AdministrationPage")).pack(side="left", padx=5)

        # --- CRÉATION DE TOUTES LES PAGES ---
        for PageClass in (AgentsManagementPage, CongesManagementPage, DashboardPage, AdministrationPage):
            page_name = PageClass.__name__
            page = PageClass(parent=self, main_app=self, manager=self.manager)
            self.pages[page_name] = page
            
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side="bottom", fill="x")
        
    def refresh_all(self, agent_to_select_id=None):
        """Rafraîchit toutes les pages."""
        for page_name, page in self.pages.items():
            if hasattr(page, 'refresh_all'):
                page.refresh_all(agent_to_select_id)
            elif hasattr(page, 'refresh_stats'):
                page.refresh_stats()

    def _open_file(self, filepath):
        filepath = os.path.realpath(filepath)
        try:
            if sys.platform == "win32": os.startfile(filepath)
            elif sys.platform == "darwin": subprocess.run(["open", filepath], check=True)
            else: subprocess.run(["xdg-open", filepath], check=True)
        except Exception as e:
            messagebox.showerror("Erreur d'Ouverture", f"Impossible d'ouvrir le fichier:\n{e}", parent=self)
            
    def _run_long_task(self, task_lambda, on_complete, status_message):
        self.set_status(status_message)
        self.config(cursor="watch")
        
        result_container = []
        def task_wrapper():
            try: result_container.append(task_lambda())
            except Exception as e: result_container.append(e)
                
        worker_thread = threading.Thread(target=task_wrapper)
        worker_thread.start()
        self._check_thread_completion(worker_thread, result_container, on_complete)
    
    def _check_thread_completion(self, thread, result_container, on_complete):
        if thread.is_alive():
            self.after(100, lambda: self._check_thread_completion(thread, result_container, on_complete))
        else:
            result = result_container[0] if result_container else None
            on_complete(result)
            self.config(cursor="")
            self.set_status("Prêt.")
    
    def _on_task_complete(self, result):
        if isinstance(result, Exception):
            messagebox.showerror("Erreur", f"L'opération a échoué:\n{result}")
        elif result:
            messagebox.showinfo("Succès", result)
    
    def _on_import_complete(self, result):
        self._on_task_complete(result)
        if not isinstance(result, Exception): self.refresh_all()
# Fichier: core/constants.py

from enum import Enum

class SoldeStatus(str, Enum):
    ACTIF = 'Actif'
    EXPIRE = 'Expiré'
    def __str__(self):
        return self.value

# --- EXCEPTIONS PERSONNALISÉES POUR LA LOGIQUE DE CHEVAUCHEMENT ---
class SplitConfirmationRequired(Exception):
    def __init__(self, message, form_data, overlap_conge):
        self.message = message; self.form_data = form_data; self.overlap_conge = overlap_conge
        super().__init__(self.message)

class ReplaceConfirmationRequired(Exception):
    def __init__(self, message, form_data, overlap_conge):
        self.message = message; self.form_data = form_data; self.overlap_conge = overlap_conge
        super().__init__(self.message)

class TrimConfirmationRequired(Exception):
    def __init__(self, message, form_data, overlap_conge, trim_side):
        self.message = message; self.form_data = form_data; self.overlap_conge = overlap_conge
        self.trim_side = trim_side
        super().__init__(self.message)
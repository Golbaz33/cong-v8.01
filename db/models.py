# Fichier : db/models.py
# MISE À JOUR - Ajout de la situation familiale et des champs pour les internes.

from utils.date_utils import validate_date
from core.constants import SoldeStatus

class SoldeAnnuel:
    def __init__(self, id, agent_id, annee, solde, statut):
        self.id = id; self.agent_id = agent_id; self.annee = annee
        self.solde = float(solde); self.statut = SoldeStatus(statut.strip() if statut else SoldeStatus.ACTIF)
    @classmethod
    def from_db_row(cls, row):
        if not row: return None
        return cls(id=row['id'], agent_id=row['agent_id'], annee=row['annee'], solde=row['solde'], statut=row['statut'])

class HistoriqueCarriere:
    def __init__(self, id, agent_id, date_evenement, type_evenement, service, specialite, centre, details):
        self.id = id; self.agent_id = agent_id; self.date_evenement = validate_date(date_evenement)
        self.type_evenement = type_evenement; self.service_affectation = service; self.specialite = specialite
        self.centre_formation = centre; self.details = details
    @classmethod
    def from_db_row(cls, row):
        if not row: return None
        return cls(id=row['id'], agent_id=row['agent_id'], date_evenement=row['date_evenement'],
                   type_evenement=row['type_evenement'], service=row['service_affectation'],
                   specialite=row['specialite'], centre=row['centre_formation'], details=row['details'])

class ProfilMedecinResident:
    def __init__(self, id, agent_id, type_residanat, statut_contrat, date_fin_formation):
        self.id = id; self.agent_id = agent_id; self.type_residanat = type_residanat
        self.statut_contrat = statut_contrat; self.date_fin_formation = validate_date(date_fin_formation)
    @classmethod
    def from_db_row(cls, row):
        if not row: return None
        return cls(id=row['id'], agent_id=row['agent_id'], type_residanat=row['type_residanat'], 
                   statut_contrat=row['statut_contrat'], date_fin_formation=row['date_fin_formation'])

# --- NOUVELLE CLASSE POUR LE PROFIL MÉDECIN INTERNE ---
class ProfilMedecinInterne:
    def __init__(self, id, agent_id, site_stage_1, site_stage_2, site_stage_3, site_stage_4, prolongation):
        self.id = id
        self.agent_id = agent_id
        self.site_stage_1 = site_stage_1
        self.site_stage_2 = site_stage_2
        self.site_stage_3 = site_stage_3
        self.site_stage_4 = site_stage_4
        self.prolongation = prolongation
    @classmethod
    def from_db_row(cls, row):
        if not row: return None
        return cls(id=row['id'], agent_id=row['agent_id'], site_stage_1=row.get('site_stage_1'),
                   site_stage_2=row.get('site_stage_2'), site_stage_3=row.get('site_stage_3'),
                   site_stage_4=row.get('site_stage_4'), prolongation=row.get('prolongation'))

class Agent:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.nom = (kwargs.get('nom') or "").strip()
        self.prenom = (kwargs.get('prenom') or "").strip()
        self.ppr = (kwargs.get('ppr') or "").strip()
        self.cadre = (kwargs.get('cadre') or "").strip()
        
        self.sexe = kwargs.get('sexe')
        self.cnie = kwargs.get('cnie')
        self.nom_arabe = kwargs.get('nom_arabe')
        self.prenom_arabe = kwargs.get('prenom_arabe')
        
        # --- NOUVEAU CHAMP ---
        self.situation_familiale = kwargs.get('situation_familiale')

        self.date_prise_service = validate_date(kwargs.get('date_prise_service'))
        self.date_cessation_service = validate_date(kwargs.get('date_cessation_service'))
        self.statut_hierarchique = kwargs.get('statut_hierarchique')
        self.specialite = kwargs.get('specialite')
        self.service_affectation = kwargs.get('service_affectation')
        self.telephone_pro = kwargs.get('telephone_pro')
        self.email_pro = kwargs.get('email_pro')
        self.type_recrutement = kwargs.get('type_recrutement')
        self.motif_cessation_service = kwargs.get('motif_cessation_service')
        self.statut_agent = kwargs.get('statut_agent', 'Actif')
        
        self.soldes_annuels = []
        self.historique = []
        self.profil = None # Sera soit un ProfilMedecinResident, soit un ProfilMedecinInterne

    def __str__(self):
        return f"{self.nom} {self.prenom} (PPR: {self.ppr})"

    @classmethod
    def from_db_row(cls, row_dict):
        """Crée une instance d'Agent à partir d'un dictionnaire (row factory)."""
        if not row_dict: return None
        return cls(**row_dict)

    def get_solde_total_actif(self):
        return sum(s.solde for s in self.soldes_annuels if s.statut == SoldeStatus.ACTIF)

class Conge:
    def __init__(self, id, agent_id, type_conge, justif, interim_id, date_debut, date_fin, jours_pris, statut='Actif'):
        self.id = id; self.agent_id = agent_id; self.type_conge = (type_conge or "").strip()
        self.justif = (justif or "").strip(); self.interim_id = interim_id
        self.date_debut = validate_date(date_debut); self.date_fin = validate_date(date_fin)
        self.jours_pris = jours_pris; self.statut = (statut or "Actif").strip()

    @classmethod
    def from_db_row(cls, row):
        if not row: return None
        return cls(id=row['id'], agent_id=row['agent_id'], type_conge=row['type_conge'], justif=row['justif'], 
                   interim_id=row['interim_id'], date_debut=row['date_debut'], date_fin=row['date_fin'], 
                   jours_pris=row['jours_pris'], statut=row['statut'])
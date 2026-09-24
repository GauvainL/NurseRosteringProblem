from dataclasses import dataclass

@dataclass
class Poste:
    d_min  : int       # durée en minutes
    I      : list[int] # les IDs de poste ne pouvant pas être affectés juste après ce poste
    u_j    : list[int] # le nombre d'employés requis pour chaque journée
    v_min_j: list[int] # la pénalité pour pas assez d'employés pour chaque journée
    v_max_j: list[int] # la pénalité pour trop d'employés pour chaque journée

@dataclass
class Requete:
    poste: int # le poste concerné par la requête
    poids: int # le poids d'échec de la requête

@dataclass
class Employe:
    R      : list[int]          # les jours où l'employé ne travaille pas
    t_min  : int                # le temps total minimum de travail à faire
    t_max  : int                # le temps total maximum de travail à faire
    c_min  : int                # le nombre de jours consécutifs minimum à travailler
    c_max  : int                # le nombre de jours consécutifs maximum à travailler
    r_min  : int                # le nombre de jours de repos consécutifs à affecter
    w_max  : int                # le nombre maximum de week-ends pouvant être travaillés
    m_max_p: list[int]          # le nombre maximum de jours à travailler par ID de poste
    s      : dict[int, Requete] # le souhait de travailler un poste tel jour
    no_s   : dict[int, Requete] # le non-souhait de travailler un poste tel jour

@dataclass
class Modele:
    h: int           # le nombre de jours de plannification
    J: list[int]     # la liste des jours de plannification
    W: list[int]     # les weekends de plannification
    E: list[Employe] # la liste des employés
    P: list[Poste]   # la liste des postes



class Solution:
    x_ejp : list[list[list[bool]]] # x[p][j][e]: 1 si au poste p le jour j l'employé e est affecté, 0 sinon
    t_ew  : list[list[bool]]       # t[w][e]   : 1 si le weekend w l'employé e travaille, 0 sinon (w = sam OU dim)
    y_jp_m: list[list[int]]        # y_m[p][j] : manque de personnel au poste p le jour j
    y_jp_e: list[list[int]]        # y_e[p][j] : excédent de personnel au poste p le jour j
import re

from objets import Modele, Solution, Employe, Poste

def contrainte_1(sol: Solution) -> bool:
    """
    Contrainte sur l'affectation des employés aux postes :
    Chaque employé ne peut être affecté qu’à un seul type de poste par jour, au plus.
    
    Returns:
        True si la contrainte est respectée, False sinon.
        
    Args:
        sol (Solution)
    """
    
    for e in range(len(sol.x_ejp[0][0])):
        for j in range(len(sol.x_ejp[0])):
            somme_postes = sum(sol.x_ejp[p][j][e] for p in range(len(sol.x_ejp)))
            if somme_postes > 1:
                return False
    return True

def contrainte_2(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur l'incapacité d'enchaîner certains types de postes :
    Certain types de poste ne peuvent pas être enchaînés.

    Returns:
        True si la contrainte est respectée, False sinon.
        
    Args:
        sol (Solution)
        modele (Modele)
    """
    for i in range(len(sol.x_ejp)):
        for j in range(len(sol.x_ejp[i])):
            for e in range(len(sol.x_ejp[i][j])):
                if sol.x_ejp[i][j][e] == 1:
                    for poste_interdit in modele.P[i].I:
                        if j + 1 < len(sol.x_ejp[i]) and sol.x_ejp[poste_interdit][j + 1][e] == 1:
                            return False
    return True

def contrainte_3(sol: Solution, modele: Modele) -> bool:
    """ 
    Contrainte sur le nombre maximum d'affectations d'un employé à un poste :
    Chaque employé ne peut pas être affecté à un poste plus de m_max_p fois.

    Returns:
        True si la contrainte est respectée, False sinon.
        
    Args:
        sol (Solution):
        modele (Modele):
    """
    for e in range(len(sol.x_ejp[0][0])):
        for p in range(len(sol.x_ejp)):
            count = sum(sol.x_ejp[p][j][e] for j in range(len(sol.x_ejp[p])))
            if count > modele.E[e].m_max_p[p]:
                return False
    return True

def contrainte_4(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur le temps minimal et maximal de travail d'un employé :
    Chaque employé travaille un total total borné

    Returns:
        True si la contrainte est respectée, False sinon.
        
    Args:
        sol (Solution):
        modele (Modele):
    """
    for e in range(len(sol.x_ejp[0][0])):
        total_work = 0
        for p in range(len(sol.x_ejp)):
            duree = modele.P[p].d_min
            total_work += sum(sol.x_ejp[p][j][e] for j in range(modele.h)) * duree

        if total_work < modele.E[e].t_min or total_work > modele.E[e].t_max:
            return False
    return True

def contrainte_5_6(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur le nombre de jours consécutifs travaillés :
    Chaque employé doit travailler un nombre de jours consécutifs borné

    Returns:
        True si la contrainte est respectée, False sinon.

    Args:
        sol (Solution):
        modele (Modele):
    """
    nb_postes = len(sol.x_ejp)
    nb_jours = len(sol.x_ejp[0])
    nb_employes = len(sol.x_ejp[0][0])

    for e in range(nb_employes):
        c_min = modele.E[e].c_min
        c_max = modele.E[e].c_max
        travaille = [any(sol.x_ejp[p][j][e] == 1 for p in range(nb_postes)) for j in range(nb_jours)]
        j = 0
        while j < nb_jours:
            if travaille[j]:
                debut = j
                while j < nb_jours and travaille[j]:
                    j += 1
                consecutive_days = j - debut
                if consecutive_days < c_min or consecutive_days > c_max:
                    return False
            else:
                j += 1
    return True

def contrainte_7(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur le nombre de jours consécutifs de repos :
    Chaque employé a un nombre minimum consécutifs de jour de repos :

    Returns:
        True si la contrainte est respectée, False sinon.
        
    Args:
        sol (Solution):
        modele (Modele):
    """
    
    nb_postes = len(sol.x_ejp)
    nb_jours = len(sol.x_ejp[0])
    nb_employes = len(sol.x_ejp[0][0])

    for e in range(nb_employes):
        r_min = modele.E[e].r_min
        repos = [not any(sol.x_ejp[p][j][e] == 1 for p in range(nb_postes)) for j in range(nb_jours)]
        j = 0
        while j < nb_jours:
            if repos[j]:
                debut = j
                while j < nb_jours and repos[j]:
                    j += 1
                consecutive_days = j - debut
                if consecutive_days < r_min:
                    return False
            else:
                j += 1
    return True

def contrainte_8(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur le nombre maximum de week-ends travaillés :
    Chaque employé ne peut pas travailler plus de w_max week-ends.

    Returns:
        True si la contrainte est respectée, False sinon.

    Args:
        sol (Solution):
        modele (Modele):
    """
    
    for e in range(len(sol.x_ejp[0][0])):
        weekend_count = 0
        for w in range(len(modele.W)):
            if sol.t_ew[w][e] == 1:
                weekend_count += 1
        if weekend_count > modele.E[e].w_max:
            return False
    return True

def contrainte_9(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur les jours de repos imposés :
    Chaque employé a des jours de repos imposés.
    
    Returns:
        True si la contrainte est respectée, False sinon.
        
    Args:
        sol (Solution):
        modele (Modele):
    """
    for e in range(len(sol.x_ejp[0][0])):
        for j in range(len(sol.x_ejp[0])):
            for p in range(len(sol.x_ejp)):
                if sol.x_ejp[p][j][e] == 1 and j in modele.E[e].R:
                    return False
    return True

def contrainte_10(sol: Solution, modele: Modele) -> bool:
    """
    Contrainte sur la couvertures des postes :
    Chaque poste doit être couvert par un nombre d'employés approprié.
    
    Returns:
        True si la contrainte est respectée, False sinon.

    Args:
        sol (Solution):
        modele (Modele):
    """
    for p in range(len(sol.x_ejp)):
        for j in range(len(sol.x_ejp[p])):
            total_employees = sum(sol.x_ejp[p][j][e] - sol.y_jp_m[p][j] + sol.y_jp_e[p][j] for e in range(len(sol.x_ejp[p][j])))
            if total_employees == modele.P[p].u_j[j]:
                return True
            else:
                return False
    return True

def calculer_q_ejp(sol: Solution, e:Employe, p:Poste, j:int) -> int:
    """
    Calcule la pénalité si l’employé e n’est pas affecté au type de poste p le jour j alors qu’il le souhaitait.

    Returns:
        q_ejp (int): la pénalité si l’employé e n’est pas affecté au type de poste p le jour j alors qu’il le souhaitait

    Args:
        sol (Solution):
        e (Employe):
        p (Poste):
        j (int):
    """
    for souhait in e.s.values():
        if souhait[0] == j and souhait[1].poste == p:
            if sol.x_ejp[e.s[j].poste][j][e] == 0:
                return souhait[1].poids
    return 0

def calculer_p_ejp(sol: Solution, e:Employe, p:Poste, j:int) -> int:
    """
    Calcule la pénalité si l’employé e n’est pas affecté au type de poste p le jour j alors qu’il le souhaitait.

    Returns:
        p_ejp (int): la pénalité si l’employé e est affecté au type de poste p le jour j alors qu’il ne le souhaitait pas

    Args:
        sol (Solution):
        e (Employe):
        p (Poste):
        j (int):
    """
    for non_souhait in e.no_s.values():
        if non_souhait[0] == j and non_souhait[1].poste == p:
            if sol.x_ejp[e.no_s[j].poste][j][e] == 1:
                return non_souhait[1].poids
    return 0

def fonction_objective(sol: Solution, modele: Modele):
    """
    Fonction objectif :
    Minimiser le nombre de pénalités pour manque ou excédent de personnel.

    Args:
        sol (Solution):
        modele (Modele):
    """
    
    resultat_1 = 0
    resultat_2 = 0
    
    for p in range(len(sol.x_ejp)):
        for j in range(len(sol.x_ejp[p])):
            for e in range(len(sol.x_ejp[p][j])):
                resultat_1 += (calculer_q_ejp(sol, modele.E[e], modele.P[p], j) * (1- sol.x_ejp[p][j][e])) + (calculer_p_ejp(sol, modele.E[e], modele.P[p], j) * sol.x_ejp[p][j][e])
                
    for p in range(len(sol.x_ejp)):
        for j in range(len(sol.x_ejp[p])):
            resultat_2 += (modele.P[p].v_min_j * sol.y_jp_m[p][j]) + (modele.P[p].v_max_j * sol.y_jp_e[p][j]) 

    return resultat_1 + resultat_2
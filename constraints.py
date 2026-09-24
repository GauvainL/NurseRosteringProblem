from objets import Modele, Solution

def constraint_1(sol: Solution):
    """
    Contrainte sur l'affectation des employés aux postes :
    Chaque employé ne peut être affecté qu’à un seul type de poste par jour, au plus.

    Args:
        sol (Solution)
    """
    
    for i in range(len(sol.x_ejp)):
        for j in range(len(sol.x_ejp[i])):
            if sum(sol.x_ejp[i][j]) > 1:
                return False
    return True

def constraint_2(sol: Solution, modele: Modele):
    """
    Contrainte sur l'incapacité d'enchaîner certains types de postes :
    Certain types de poste ne peuvent pas être enchaînés.

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

def constraint_3(sol: Solution, modele: Modele):
    """ 
    Contrainte sur le nombre maximum d'affectations d'un employé à un poste :
    Chaque employé ne peut pas être affecté à un poste plus de m_max_p fois.

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

def constraint_4(sol: Solution, modele: Modele):
    """
    Contrainte sur le temps minimal et maximal de travail d'un employé :
    Chaque employé travaille un total total borné

    Args:
        sol (Solution):
        modele (Modele):
    """
    for p in range(len(sol.x_ejp)):
        for e in range(len(sol.x_ejp[p][0])):
            total_work = sum(sol.x_ejp[p][j][e] * modele.P[p].d_min for j in range(len(sol.x_ejp[p])))
            if total_work < modele.E[e].t_min or total_work > modele.E[e].t_max:
                return False
    return True

def constraint_5_6(sol: Solution, modele: Modele):
    """
    Contrainte sur le nombre de jours consécutifs travaillés :
    Chaque employé doit travailler un nombre de jours consécutifs borné

    Args:
        sol (Solution):
        modele (Modele):
    """
    for e in range(len(sol.x_ejp[0][0])):
        consecutive_days = 0
        max_consecutive_days = 0
        for j in range(len(sol.x_ejp[0])):
            if any(sol.x_ejp[p][j][e] == 1 for p in range(len(sol.x_ejp))):
                consecutive_days += 1
                max_consecutive_days = max(max_consecutive_days, consecutive_days)
            else:
                consecutive_days = 0
        if max_consecutive_days < modele.E[e].c_min or max_consecutive_days > modele.E[e].c_max:
            return False
    return True

def constraint_7(sol: Solution, modele: Modele):
    """
    Contrainte sur le nombre de jours consécutifs de repos :
    Chaque employé a un nombre minimum consécutifs de jour de repos :

    Args:
        sol (Solution):
        modele (Modele):
    """
    
    for e in range(len(sol.x_ejp[0][0])):
        consecutive_rest_days = 0
        max_consecutive_rest_days = 0
        for j in range(len(sol.x_ejp[0])):
            if not any(sol.x_ejp[p][j][e] == 1 for p in range(len(sol.x_ejp))):
                consecutive_rest_days += 1
                max_consecutive_rest_days = max(max_consecutive_rest_days, consecutive_rest_days)
            else:
                consecutive_rest_days = 0
        if max_consecutive_rest_days < modele.E[e].r_min:
            return False
    return True

def constraint_8(sol: Solution, modele: Modele):
    """
    Contrainte sur le nombre maximum de week-ends travaillés :
    Chaque employé ne peut pas travailler plus de w_max week-ends.

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

def constraint_9(sol: Solution, modele: Modele):
    """
    Contrainte sur les jours de repos imposés :
    Chaque employé a des jours de repos imposés.
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

def constraint_10(sol: Solution, modele: Modele):
    """
    Contrainte sur la couvertures des postes :
    Chaque poste doit être couvert par un nombre d'employés approprié.
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
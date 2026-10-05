from objets import *
import pychoco


def creer_template_choco(probleme: Modele) -> tuple[pychoco.Model, list[list[list]], list[list]]:
    """
    Construit le modèle PyChoco correspondant uniquement aux contraintes
    dures (1) à (9) du problème de nurse rostering.

    Aucune contrainte de couverture et aucun objectif ne sont ajoutés :
    toute solution trouvée par Choco est donc simplement une solution faisable.
    """
    modele = pychoco.Model()

    h   = probleme.h
    n_e = len(probleme.E)
    n_p = len(probleme.P)
    n_w = len(probleme.W)

    if len(probleme.J) != h:
        raise ValueError("Modele.J doit contenir exactement h jours")
    if h % 7 != 0:
        raise ValueError("L'horizon de planification doit être un multiple de 7")
    if n_w != h // 7:
        raise ValueError("Modele.W est incohérent avec l'horizon de planification")

    # Correspondance entre les identifiants de jours du modèle métier
    # et leurs indices 0..h-1 dans les tableaux PyChoco.
    jour_vers_index = {
        jour: index
        for index, jour in enumerate(probleme.J)
    }

    # x_ejp[p][j][e] = 1 si l'employé e travaille au poste p le jour j.
    x_flat = modele.intvars(n_p * h * n_e, 0, 1)
    x_ejp  = [[[x_flat[(p * h + j) * n_e + e] for e in range(n_e)] for j in range(h) ] for p in range(n_p)]

    def x(p: int, j: int, e: int):
        return x_ejp[p][j][e]

    # t_ew[w][e] = 1 si l'employé e travaille au moins un jour du week-end w.
    t_flat = modele.intvars(n_w * n_e, 0, 1)
    t_ew   = [[t_flat[w * n_e + e] for e in range(n_e)] for w in range(n_w)]

    def t(w: int, e: int):
        return t_ew[w][e]


    # (1) Un employé travaille au plus un poste par jour.
    for e in range(n_e):
        for j in range(h):
            modele.sum([x(p, j, e) for p in range(n_p)], "<=", 1).post()

    # (2) Incompatibilités entre deux postes de jours consécutifs.
    for e in range(n_e):
        for j in range(h - 1):
            for p, poste in enumerate(probleme.P):
                for p_suivant in poste.I:
                    if not 0 <= p_suivant < n_p:
                        raise ValueError(f"ID de poste incompatible invalide : {p_suivant}")
                    modele.sum([x(p, j, e), x(p_suivant, j + 1, e)], "<=", 1).post()

    for e, employe in enumerate(probleme.E):
        # (3) Nombre maximal d'affectations de l'employé e au poste p.
        if len(employe.m_max_p) != n_p:
            raise ValueError(f"m_max_p de l'employé {e} doit contenir une valeur par poste")
        for p in range(n_p):
            modele.sum([x(p, j, e) for j in range(h)], "<=", employe.m_max_p[p]).post()

        # (4) Temps total de travail borné.
        variables    = []
        coefficients = []

        for j in range(h):
            for p, poste in enumerate(probleme.P):
                variables   .append(x(p, j, e))
                coefficients.append(poste.d_min)

        modele.scalar(variables, coefficients, ">=", employe.t_min).post()
        modele.scalar(variables, coefficients, "<=", employe.t_max).post()

        # (5) Au plus c_max jours consécutifs travaillés.
        # Dans toute fenêtre de c_max + 1 jours, il doit donc exister
        # au moins un jour de repos.
        taille_fenetre = employe.c_max + 1

        if taille_fenetre <= h:
            for d in range(h - taille_fenetre + 1):
                modele.sum(
                    [
                        x(p, j, e)
                        for j in range(d, d + taille_fenetre)
                        for p in range(n_p)
                    ],
                    "<=",
                    employe.c_max,
                ).post()

        # (6) Au moins c_min jours consécutifs travaillés.
        #
        # Formulation du sujet : pour chaque s < c_min, on interdit
        # un bloc d'exactement s jours travaillés entouré de repos.
        #
        #   work[d] + s - sum(work[d+1..d+s]) + work[d+s+1] > 0
        #
        # Comme tout est entier : > 0 équivaut à >= 1.
        for s in range(1, employe.c_min):
            for d in range(h - s - 1):
                variables    = []
                coefficients = []

                # work[d]
                for p in range(n_p):
                    variables   .append(x(p, d, e))
                    coefficients.append(1)
                # -sum(work[d+1 .. d+s])
                for j in range(d + 1, d + s + 1):
                    for p in range(n_p):
                        variables   .append(x(p, j, e))
                        coefficients.append(-1)
                # +work[d+s+1]
                for p in range(n_p):
                    variables   .append(x(p, d + s + 1, e))
                    coefficients.append(1)

                # work[d] - middle + work[d+s+1] >= 1 - s
                modele.scalar(variables, coefficients, ">=", 1 - s).post()

        # (7) Au moins r_min jours consécutifs de repos.
        #
        # Formulation du sujet : pour chaque s < r_min, on interdit
        # un bloc d'exactement s jours de repos entouré de travail.
        #
        #   (1-work[d]) + sum(work[d+1..d+s])
        #   + (1-work[d+s+1]) > 0
        #
        # Ce qui se réécrit :
        #   -work[d] + middle - work[d+s+1] >= -1
        for s in range(1, employe.r_min):
            for d in range(h - s - 1):
                variables    = []
                coefficients = []

                # -work[d]
                for p in range(n_p):
                    variables   .append(x(p, d, e))
                    coefficients.append(-1)
                # +sum(work[d+1 .. d+s])
                for j in range(d + 1, d + s + 1):
                    for p in range(n_p):
                        variables   .append(x(p, j, e))
                        coefficients.append(1)
                # -work[d+s+1]
                for p in range(n_p):
                    variables   .append(x(p, d + s + 1, e))
                    coefficients.append(-1)

                modele.scalar(variables, coefficients, ">=", -1).post()

        # (8) Nombre maximal de week-ends travaillés.
        # Le planning commence un lundi : samedi = 7w+5, dimanche = 7w+6.
        for w in range(n_w):
            samedi   = 7 * w + 5
            dimanche = 7 * w + 6

            # t[w,e] <= work[samedi] + work[dimanche]
            modele.scalar(
                  [t(w, e)]
                + [x(p, samedi  , e) for p in range(n_p)]
                + [x(p, dimanche, e) for p in range(n_p)],
                [1] + [-1] * (2 * n_p),
                "<=",
                0,
            ).post()

            # work[samedi] + work[dimanche] <= 2 * t[w,e]
            modele.scalar(
                  [t(w, e)]
                + [x(p, samedi  , e) for p in range(n_p)]
                + [x(p, dimanche, e) for p in range(n_p)],
                [-2] + [1] * (2 * n_p),
                "<=",
                0,
            ).post()

        modele.sum([t(w, e) for w in range(n_w)], "<=", employe.w_max).post()

        # (9) Jours de repos imposés.
        for jour in employe.R:
            if jour not in jour_vers_index:
                raise ValueError(f"Jour {jour} de R pour l'employé {e} absent de Modele.J")

            j = jour_vers_index[jour]
            for p in range(n_p):
                modele.arithm(x(p, j, e), "=", 0).post()

    return modele, x_ejp, t_ew

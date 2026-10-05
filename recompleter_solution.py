from objets import *
import pychoco


def recompleter_solution(
        probleme: Modele,
        x_ejp   : list[list[list]],
        t_ew    : list[list],
        sol     : Solution                   | None = None,
        coord   : list[tuple[int, int, int]] | None = None) -> Solution:

    n_p = len(probleme.P)
    n_j = probleme.h
    n_e = len(probleme.E)
    n_w = len(probleme.W)

    if sol   is None:
        sol = Solution()

    if coord is None:
        sol.x_ejp = [[[bool(x_ejp[p][j][e].get_value()) for e in range(n_e)] for j in range(n_j)] for p in range(n_p)]
    else:
        if not hasattr(sol, "x_ejp"):
            raise ValueError("Une reconstruction partielle nécessite une solution existante")

        for p, j, e in coord:
            sol.x_ejp[p][j][e] = bool(x_ejp[p][j][e].get_value())

    sol.t_ew   = [[bool(t_ew[w][e].get_value()) for e in range(n_e)] for w in range(n_w)]
    sol.y_jp_m = [[0 for _ in range(n_j)] for _ in range(n_p)]
    sol.y_jp_e = [[0 for _ in range(n_j)] for _ in range(n_p)]

    for p, poste in enumerate(probleme.P):
        for j in range(n_j):
            affectes         = sum(sol.x_ejp[p][j][e] for e in range(n_e))
            requis           = poste.u_j[j]
            sol.y_jp_m[p][j] = max(requis - affectes, 0)
            sol.y_jp_e[p][j] = max(affectes - requis, 0)

    return sol

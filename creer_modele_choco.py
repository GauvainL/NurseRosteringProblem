from pychoco import Model
import pychoco
from objets import Modele, Solution
from creer_template_choco import creer_template_choco

def creer_modele_choco(solution: Solution, modele: Modele, coord: list[tuple[int, int, int]]) -> {pychoco.Model, list[list[list[bool]]], list[list[bool]]}:

	template, x_ejp, t_ew = creer_template_choco(modele)
	for p, j, e in coord:
		template.arithm(solution.x_ejp[p][j][e], "=", x_ejp[p][j][e]).post()
	return template, x_ejp, t_ew
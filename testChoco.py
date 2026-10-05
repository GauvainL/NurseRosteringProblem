"""Solveur PyChoco pour le Nurse Rostering Problem.

Le module suit la formulation du sujet :
	x[p][j][e] = 1 si l'employe e travaille au poste p le jour j.

Les contraintes dures sont postees dans :func:`construire_modele_choco`.
L'objectif comprend les demandes de postes et les ecarts de couverture.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from pychoco import Model

from generateXML import sauvegarder_solution_ros
from objets import Modele, Solution
from readData import parseur


@dataclass
class ModeleChoco:
	modele: Model
	x: list[list[list[object]]]
	travaille: list[list[object]]
	week_end: list[list[object]]
	manque: list[list[object]]
	excedent: list[list[object]]
	objectif: object


def _somme_bool(model: Model, variables: list[object], name: str) -> object:
	resultat = model.intvar(0, len(variables), name=name)
	model.sum(variables, "=", resultat).post()
	return resultat


def _fenetre_interdite(
	model: Model,
	variables: list[object],
	start: int,
	length: int,
	valeur: int,
) -> None:
	"""Interdit une serie de ``length`` valeurs, encadree par la valeur opposee."""
	horizon = len(variables)
	avant = [model.arithm(variables[start - 1], "=", 1 - valeur)] if start > 0 else []
	apres_index = start + length
	apres = (
		[model.arithm(variables[apres_index], "=", 1 - valeur)]
		if apres_index < horizon
		else []
	)
	serie = [model.arithm(variables[index], "=", valeur)
			 for index in range(start, apres_index)]
	motif = model.and_(avant + serie + apres)
	# Le motif contient deja la valeur de la premiere case : l'impliquer
	# vers la valeur opposee le rend impossible.

	model.if_then(motif, model.arithm(variables[start], "=", 1 - valeur))


def construire_modele_choco(donnees: Modele) -> ModeleChoco:
	"""Construit le modele PyChoco complet a partir d'une instance lue."""
	model = Model("Nurse Rostering")
	nombre_postes = len(donnees.P)
	nombre_employes = len(donnees.E)
	h = donnees.h

	x = [
		[
			[model.boolvar(name=f"x_{p}_{j}_{e}") for e in range(nombre_employes)]
			for j in range(h)
		]
		for p in range(nombre_postes)
	]

	travaille = [
		[_somme_bool(model, [x[p][j][e] for p in range(nombre_postes)], f"work_{j}_{e}")
		 for e in range(nombre_employes)]
		for j in range(h)
	]

	# (1) Au plus un poste par employe et par jour.
	for j in range(h):
		for e in range(nombre_employes):
			model.arithm(travaille[j][e], "<=", 1).post()

	# (2) Incompatibilites d'enchainement.
	for p, poste in enumerate(donnees.P):
		for poste_suivant in poste.I:
			for j in range(h - 1):
				for e in range(nombre_employes):
					model.arithm(x[p][j][e], "+", x[poste_suivant][j + 1][e], "<=", 1).post()

	for e, employe in enumerate(donnees.E):
		# (3) Nombre maximal de jours sur chaque poste.
		for p in range(nombre_postes):
			model.sum([x[p][j][e] for j in range(h)], "<=", employe.m_max_p[p]).post()

		# (4) Temps total de travail.
		durees = [donnees.P[p].d_min for p in range(nombre_postes) for _ in range(h)]
		variables = [x[p][j][e] for p in range(nombre_postes) for j in range(h)]
		model.scalar(variables, durees, ">=", employe.t_min).post()
		model.scalar(variables, durees, "<=", employe.t_max).post()

		# (5) Une serie de travail ne depasse jamais c_max jours.
		for debut in range(h - employe.c_max):
			model.sum([travaille[j][e] for j in range(debut, debut + employe.c_max + 1)],
					  "<=", employe.c_max).post()

		# (6) Toute serie de travail est au moins de longueur c_min.
		for longueur in range(1, employe.c_min):
			for debut in range(h - longueur + 1):
				_fenetre_interdite(model, [travaille[j][e] for j in range(h)],
								   debut, longueur, 1)

		# (7) Toute serie de repos est au moins de longueur r_min.
		for longueur in range(1, employe.r_min):
			for debut in range(h - longueur + 1):
				_fenetre_interdite(model, [travaille[j][e] for j in range(h)],
								   debut, longueur, 0)

		# (8) Week-ends travailles et limite individuelle.
		indicateurs = []
		for w in donnees.W:
			samedi = 7 * w + 5
			dimanche = samedi + 1
			if dimanche >= h:
				continue
			indicateur = model.boolvar(name=f"weekend_{w}_{e}")
			indicateurs.append(indicateur)
			weekend_work = model.intvar(0, 2, name=f"weekend_work_{w}_{e}")
			model.sum([travaille[samedi][e], travaille[dimanche][e]], "=", weekend_work).post()
			model.arithm(weekend_work, ">=", indicateur).post()
			model.arithm(weekend_work, "<=", 2, "*", indicateur).post()
		if indicateurs:
			model.sum(indicateurs, "<=", employe.w_max).post()

		# (9) Jours de repos imposes.
		for jour in employe.R:
			if 0 <= jour < h:
				model.arithm(travaille[jour][e], "=", 0).post()

	manque = [[model.intvar(0, nombre_employes, name=f"under_{p}_{j}")
			   for j in range(h)] for p in range(nombre_postes)]
	excedent = [[model.intvar(0, nombre_employes, name=f"over_{p}_{j}")
				 for j in range(h)] for p in range(nombre_postes)]

	# (10) Couverture : les ecarts sont autorises et penalises dans l'objectif.
	for p, poste in enumerate(donnees.P):
		for j in range(h):
			variables = [x[p][j][e] for e in range(nombre_employes)]
			variables += [manque[p][j], excedent[p][j]]
			coefficients = [1] * nombre_employes + [-1, 1]
			model.scalar(variables, coefficients, "=", poste.u_j[j]).post()

	# (11) Objectif : constantes des souhaits + termes variables.
	objectif_constante = 0
	objectif_variables = []
	objectif_coefficients = []
	for e, employe in enumerate(donnees.E):
		for jour, requete in employe.s.items():
			objectif_constante += requete.poids
			objectif_variables.append(x[requete.poste][jour][e])
			objectif_coefficients.append(-requete.poids)
		for jour, requete in employe.no_s.items():
			objectif_variables.append(x[requete.poste][jour][e])
			objectif_coefficients.append(requete.poids)
	for p, poste in enumerate(donnees.P):
		for j in range(h):
			objectif_variables.extend([manque[p][j], excedent[p][j]])
			objectif_coefficients.extend([poste.v_min_j[j], poste.v_max_j[j]])

	borne_objectif = objectif_constante + sum(
		max(0, coefficient) * (nombre_employes if abs(coefficient) else 0)
		for coefficient in objectif_coefficients
	) + sum(-coefficient for coefficient in objectif_coefficients if coefficient < 0)
	objectif = model.intvar(0, max(1, borne_objectif), name="objective")
	model.scalar(objectif_variables + [objectif], objectif_coefficients + [-1],
				  "=", -objectif_constante).post()
	model.set_objective(objectif, maximize=False)

	return ModeleChoco(model, x, travaille, [], manque, excedent, objectif)


def extraire_solution(modele_choco: ModeleChoco, solution_choco: object) -> Solution:
	"""Convertit une solution PyChoco dans la representation du depot."""
	x = [[[bool(solution_choco.get_int_val(modele_choco.x[p][j][e]))
		   for e in range(len(modele_choco.x[p][j]))]
		  for j in range(len(modele_choco.x[p]))]
		 for p in range(len(modele_choco.x))]
	manque = [[solution_choco.get_int_val(variable) for variable in ligne]
			  for ligne in modele_choco.manque]
	excedent = [[solution_choco.get_int_val(variable) for variable in ligne]
				for ligne in modele_choco.excedent]
	return Solution(x_ejp=x, t_ew=[], y_jp_m=manque, y_jp_e=excedent)


def solution_est_faisable(solution: Solution, donnees: Modele) -> bool:
	"""Verification independante des contraintes dures (1) a (9)."""
	h = donnees.h
	nombre_employes = len(donnees.E)
	for e, employe in enumerate(donnees.E):
		travail = [sum(solution.x_ejp[p][j][e] for p in range(len(donnees.P)))
				   for j in range(h)]
		if any(value > 1 for value in travail):
			return False
		for p, poste in enumerate(donnees.P):
			if sum(solution.x_ejp[p][j][e] for j in range(h)) > employe.m_max_p[p]:
				return False
			for j in range(h - 1):
				if solution.x_ejp[p][j][e] and any(
					solution.x_ejp[next_p][j + 1][e] for next_p in poste.I
				):
					return False
		total = sum(solution.x_ejp[p][j][e] * donnees.P[p].d_min
					for p in range(len(donnees.P)) for j in range(h))
		if not employe.t_min <= total <= employe.t_max:
			return False
		for j in range(h - employe.c_max):
			if sum(travail[j:j + employe.c_max + 1]) > employe.c_max:
				return False
		runs = []
		courant = 0
		for value in travail + [0]:
			if value:
				courant += 1
			elif courant:
				runs.append(courant)
				courant = 0
		if any(run < employe.c_min for run in runs):
			return False
		repos = []
		courant = 0
		for value in travail + [1]:
			if not value:
				courant += 1
			elif courant:
				repos.append(courant)
				courant = 0
		if any(run < employe.r_min for run in repos):
			return False
		if any(travail[j] for j in employe.R if 0 <= j < h):
			return False
		weekends = sum(any(travail[j] for j in (7 * w + 5, 7 * w + 6) if j < h)
					   for w in donnees.W)
		if weekends > employe.w_max:
			return False
	return nombre_employes == len(donnees.E)


def resoudre(instance_path: str, limite_temps: str | None = None) -> tuple[Solution, int, Modele]:
	"""Lit, resout et verifie une instance. Retourne solution, cout et donnees."""
	donnees, _, _ = parseur(instance_path)
	modele_choco = construire_modele_choco(donnees)
	solveur = modele_choco.modele.get_solver()
	solution_choco = solveur.find_optimal_solution(
		modele_choco.objectif, maximize=False, time_limit=limite_temps
	)
	if solution_choco is None:
		raise RuntimeError("PyChoco n'a trouve aucune solution faisable.")
	solution = extraire_solution(modele_choco, solution_choco)
	if not solution_est_faisable(solution, donnees):
		raise RuntimeError("La solution PyChoco ne respecte pas les contraintes dures.")
	cout = solution_choco.get_int_val(modele_choco.objectif)
	return solution, cout, donnees


def main() -> None:
    """
	parser = argparse.ArgumentParser(description="Solveur PyChoco de Nurse Rostering")
	parser.add_argument("instance", type=Path, help="Fichier .txt d'instance")
	parser.add_argument("--sortie", type=Path, help="Fichier .ros de sortie")
	parser.add_argument("--limite-temps", help="Limite Choco, par exemple 60s")
	args = parser.parse_args()
    """
    
    args = argparse.Namespace(instance=Path("Instances/instance1.txt"), sortie=Path("solution.ros"), limite_temps="20s")
    solution, cout, donnees = resoudre(str(args.instance), args.limite_temps)
    print(f"Cout objectif : {cout}")
    print("Contraintes dures : OK")
    if args.sortie:
        _, staff, shifts = parseur(str(args.instance))
        sauvegarder_solution_ros(solution, str(args.instance), str(args.sortie), staff, shifts, donnees.h)


if __name__ == "__main__":
	main()

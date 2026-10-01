import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

def sauvegarder_solution_ros(
    solution,
    instance_file_path: str,
    output_name: str,
    id_to_staff: list[str],
    id_to_shift: list[str],
    h: int
):
    """
    Exporte une Solution au format XML .ros compatible avec Staff Roster Solutions.

    :param solution: Objet Solution contenant x_ejp[p][j][e] (booléen)
    :param instance_file_path: Nom ou chemin du fichier d'instance (ex: "Instance1.txt")
    :param output_name: Nom du fichier de sortie (ex: "Solution_Instance1.ros")
    :param id_to_staff: Liste des ID employés d'origine (ex: ['A', 'B', 'C', ...])
    :param id_to_shift: Liste des ID postes d'origine (ex: ['E', 'L'] ou ['D'])
    :param h: Horizon de planification (nombre de jours)
    """

    roster = ET.Element("Roster", {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:noNamespaceSchemaLocation": "Roster.xsd"
    })

    # Nom du fichier d'instance de référence
    sched_file = ET.SubElement(roster, "SchedulingPeriodFile")
    # On garde de préférence uniquement le nom de base du fichier pour la portabilité
    sched_file.text = os.path.basename(instance_file_path)

    nb_employes = len(id_to_staff)
    nb_postes = len(id_to_shift)

    # Pour chaque employé
    for e in range(nb_employes):
        emp_id_str = id_to_staff[e]
        employee_node = ET.SubElement(roster, "Employee", {"ID": emp_id_str})

        # Parcours chronologique des jours
        for j in range(h):
            # Recherche du poste affecté à l'employé e le jour j
            shift_affecte = None
            for p in range(nb_postes):
                # Dans Solution : x_ejp[p][j][e] vaut True si e est affecté au poste p le jour j
                if solution.x_ejp[p][j][e]:
                    shift_affecte = id_to_shift[p]
                    break  # Au plus un poste par jour
            
            # Si l'employé travaille ce jour-ci, on ajoute l'affectation
            if shift_affecte is not None:
                assign = ET.SubElement(employee_node, "Assign")
                day_elem = ET.SubElement(assign, "Day")
                day_elem.text = str(j)  # 0-indexed conforme au visualiseur
                shift_elem = ET.SubElement(assign, "Shift")
                shift_elem.text = str(shift_affecte)

    # Formatage XML indenté (Pretty Print)
    xml_str = ET.tostring(roster, encoding="utf-8")
    reparsed = minidom.parseString(xml_str)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    with open(output_name, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"Solution sauvegardée avec succès dans : {output_name}")

# --- Zone de test ---
if __name__ == "__main__":
    import objets

    print("--- Test rapide d'exportation XML ---")

    # 1. Données fictives simples
    dummy_staff = ["A", "B", "C"]       # 3 employés (indices 0, 1, 2)
    dummy_shifts = ["E", "L"]           # 2 postes (indices 0: E, 1: L)
    dummy_h = 7                         # Horizon d'une semaine (jours 0 à 6)

    # 2. Création d'une fausse matrice x_ejp[p][j][e] remplie de False
    # Dimensions : nb_postes x nb_jours x nb_employes
    nb_p = len(dummy_shifts)
    nb_j = dummy_h
    nb_e = len(dummy_staff)

    fake_x = [[[False for _ in range(nb_e)] for _ in range(nb_j)] for _ in range(nb_p)]

    # 3. Ajout de quelques affectations manuelles :
    # Rappel du format : fake_x[poste][jour][employe] = True
    
    # L'employé 'A' (0) fait le poste 'E' (0) le jour 0
    fake_x[0][0][0] = True
    # L'employé 'A' (0) fait le poste 'L' (1) le jour 1
    fake_x[1][1][0] = True

    # L'employé 'B' (1) fait le poste 'L' (1) le jour 0 et le jour 2
    fake_x[1][0][1] = True
    fake_x[1][2][1] = True

    # (L'employé 'C' ne travaille pas dans ce test, il n'aura aucun <Assign>)

    # 4. Instanciation d'un objet Solution fictif
    fake_solution = objets.Solution(
        x_ejp=fake_x,
        t_ew=[],    # Pas nécessaire pour le XML
        y_jp_m=[],
        y_jp_e=[]
    )

    # 5. Appel de la fonction de sauvegarde
    output_test_file = "test_output.ros"
    sauvegarder_solution_ros(
        solution=fake_solution,
        instance_file_path="Instance1.txt",
        output_name=output_test_file,
        id_to_staff=dummy_staff,
        id_to_shift=dummy_shifts,
        h=dummy_h
    )

    # 6. Affichage du contenu généré pour vérification immédiate dans la console
    print("\nContenu du fichier généré :")
    with open(output_test_file, "r", encoding="utf-8") as f:
        print(f.read())
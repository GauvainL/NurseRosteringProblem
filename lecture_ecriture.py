import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import objets

        
def lire_donnees(file_path: str) -> objets.Modele:
    """
    Lit les données d'une instances à partir d'un fichier txt pour retourner un objet Modele.

    Args:
        file_path (str): Chemin vers le fichier d'instance.

    Returns:
        objets.Modele: Objet Modele contenant les informations de l'instance.
    """
    
    # 1. Lecture brute et extraction des lignes nettoyées par section
    sections = {}
    current_section = None
    staff_names = []  # retiendra ['A', 'B', 'C', ...]
    shift_names = []  # retiendra ['E', 'L']

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("SECTION_"):
                current_section = line[8:]
                sections[current_section] = []
            elif current_section:
                sections[current_section].append(line)

    # 2. Section HORIZON
    h = int(sections["HORIZON"][0])
    J = list(range(h))              # Jours 0 à h-1 (ou 1 à h selon ta convention)
    num_weekends = (h + 6) // 7
    W = list(range(num_weekends))

    # 3. Section SHIFTS
    # Création du dictionnaire de mapping str -> int (ex: "E": 0, "L": 1)
    shift_str_to_id = {}
    shift_raw_data = []

    for idx, line in enumerate(sections.get("SHIFTS", [])):
        parts = [p.strip() for p in line.split(",")]
        shift_name = parts[0]
        duration = int(parts[1])
        cannot_follow_str = parts[2].split("|") if len(parts) > 2 and parts[2] else []
        
        shift_str_to_id[shift_name] = idx
        shift_raw_data.append((duration, cannot_follow_str))
        shift_names.append(shift_name)

    # Initialisation de la liste des objets Poste
    nb_postes = len(shift_raw_data)
    postes = []
    for duration, cannot_follow_str in shift_raw_data:
        postes.append(
            objets.Poste(
                d_min=duration,
                I=[],                       # sera complété juste après le mapping
                u_j=[0] * h,
                v_min_j=[0] * h,
                v_max_j=[0] * h
            )
        )

    # Résolution des incompatibilités I (conversion des noms en IDs entiers)
    for idx, (_, cannot_follow_str) in enumerate(shift_raw_data):
        incompatibles = [shift_str_to_id[name] for name in cannot_follow_str if name in shift_str_to_id]
        postes[idx].I = incompatibles

    # 4. Section STAFF
    # Création du dictionnaire de mapping str -> int (ex: "A": 0, "B": 1)
    staff_str_to_id = {}
    employes = []

    for idx, line in enumerate(sections.get("STAFF", [])):
        parts = [p.strip() for p in line.split(",")]
        emp_id_str = parts[0]
        staff_str_to_id[emp_id_str] = idx
        staff_names.append(emp_id_str)

        # Parsing de MaxShifts (ex: "E=14|L=14")
        max_shifts_parts = parts[1].split("|") if parts[1] else []
        m_max_p = [0] * nb_postes
        for m_str in max_shifts_parts:
            if "=" in m_str:
                s_name, s_val = m_str.split("=")
                if s_name in shift_str_to_id:
                    m_max_p[shift_str_to_id[s_name]] = int(s_val)

        max_total_min = int(parts[2])
        min_total_min = int(parts[3])
        max_consec_shifts = int(parts[4])
        min_consec_shifts = int(parts[5])
        min_consec_days_off = int(parts[6])
        max_weekends = int(parts[7])

        employes.append(
            objets.Employe(
                R=[],
                t_min=min_total_min,
                t_max=max_total_min,
                c_min=min_consec_shifts,
                c_max=max_consec_shifts,
                r_min=min_consec_days_off,
                w_max=max_weekends,
                m_max_p=m_max_p,
                s={},
                no_s={}
            )
        )

    # 5. Section DAYS_OFF
    for line in sections.get("DAYS_OFF", []):
        parts = [p.strip() for p in line.split(",")]
        emp_str = parts[0]
        if emp_str in staff_str_to_id:
            e_idx = staff_str_to_id[emp_str]
            days_off = [int(d) for d in parts[1:] if d]
            employes[e_idx].R.extend(days_off)

    # 6. Section SHIFT_ON_REQUESTS (souhaits s)
    for line in sections.get("SHIFT_ON_REQUESTS", []):
        emp_str, day_str, shift_str, weight_str = [p.strip() for p in line.split(",")]
        if emp_str in staff_str_to_id and shift_str in shift_str_to_id:
            e_idx = staff_str_to_id[emp_str]
            day = int(day_str)
            p_idx = shift_str_to_id[shift_str]
            weight = int(weight_str)
            employes[e_idx].s[day] = objets.Requete(poste=p_idx, poids=weight)

    # 7. Section SHIFT_OFF_REQUESTS (non-souhaits no_s)
    for line in sections.get("SHIFT_OFF_REQUESTS", []):
        emp_str, day_str, shift_str, weight_str = [p.strip() for p in line.split(",")]
        if emp_str in staff_str_to_id and shift_str in shift_str_to_id:
            e_idx = staff_str_to_id[emp_str]
            day = int(day_str)
            p_idx = shift_str_to_id[shift_str]
            weight = int(weight_str)
            employes[e_idx].no_s[day] = objets.Requete(poste=p_idx, poids=weight)

    # 8. Section COVER
    for line in sections.get("COVER", []):
        day_str, shift_str, req_str, under_w_str, over_w_str = [p.strip() for p in line.split(",")]
        if shift_str in shift_str_to_id:
            day = int(day_str)
            p_idx = shift_str_to_id[shift_str]
            postes[p_idx].u_j[day] = int(req_str)
            postes[p_idx].v_min_j[day] = int(under_w_str)
            postes[p_idx].v_max_j[day] = int(over_w_str)

    modele = objets.Modele(h=h, J=J, W=W, E=employes, P=postes)
    return modele, staff_names, shift_names


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
    
    instance_file_path = os.path.basename(instance_file_path).removesuffix(".txt") + ".ros"
    sched_file.text = os.path.basename("Instances/" + instance_file_path)

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
      
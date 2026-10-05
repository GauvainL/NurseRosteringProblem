import objets

def parseur(file_path: str) -> objets.Modele:
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


# --- Zone de test ---
if __name__ == "__main__":
    modele, staff_names, shift_names = parseur("Instances//Instance1.txt")
    print(f"Modèle : {modele}")
    # print(f"Horizon : {modele.h} jours")
    # print(f"Nombre de postes : {len(modele.P)}")
    # print(f"Nombre d'employés : {len(modele.E)}")
    # print(f"Nombre de semaines : {modele.W}")
    # print(f"Exemple demande Poste 0, Jour 0 : {modele.P[0].u_j[0]} employés requis")
    # print(f"Exemple souhaits Employé 0 : {modele.E[0].s}")
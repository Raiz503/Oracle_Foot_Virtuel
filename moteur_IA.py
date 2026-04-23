import random

class CerveauOracle:
    def __init__(self):
        # 3. Base de Données : ADN des Équipes
        self.adn_equipes = {
            "London Reds": "Vertical",
            "Manchester Blue": "Vertical",
            "Liverpool": "Explosif",
            "Brentford": "Giant Killer",
            "Everton": "Linéaire",
            "A. Villa": "Linéaire",
            "Sunderland": "Lanterne"
        }

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        Module Principal qui traite les 4 Piliers et les Lois de l'Oracle.
        """
        cote_1, cote_x, cote_2 = cotes
        prob_1 = (1 / cote_1) * 100 if cote_1 > 0 else 0
        prob_x = (1 / cote_x) * 100 if cote_x > 0 else 0
        prob_2 = (1 / cote_2) * 100 if cote_2 > 0 else 0

        alertes = []
        modificateurs = {"dom": 0, "ext": 0, "nul": 0}

        # --- A. La Loi du Relâchement (Post-Sommet) ---
        # Si une équipe vient de gagner un gros match (simulé ici par une série de victoires contre un "Vertical")
        # Note: Dans l'intégration finale, on vérifiera l'adversaire précédent.
        if serie_dom >= 1 and self.adn_equipes.get(equipe_dom) == "Explosif":
            alertes.append(f"⚠️ {equipe_dom} : Risque de relâchement post-sommet (Profil Explosif).")
            modificateurs["nul"] += 10
            modificateurs["ext"] += 5

        # --- B. La Loi de Survie Critique (Alerte MSS) ---
        if journee >= 34:
            if rang_dom >= 17:
                alertes.append(f"🔥 ALERTE MSS : {equipe_dom} joue sa survie (+25% Résilience).")
                modificateurs["dom"] += 25
                modificateurs["nul"] += 15
            if rang_ext >= 17:
                alertes.append(f"🔥 ALERTE MSS : {equipe_ext} joue sa survie (+25% Résilience).")
                modificateurs["ext"] += 25
                modificateurs["nul"] += 15

        # --- C. La Loi du Plafond de Verre ---
        if serie_dom >= 3:
            alertes.append(f"🛑 Plafond de Verre : {equipe_dom} sur une série de 3+ victoires. Risque de Nul accru (+12%).")
            modificateurs["nul"] += 12
            modificateurs["dom"] -= 10
        if serie_ext >= 3:
            alertes.append(f"🛑 Plafond de Verre : {equipe_ext} sur une série de 3+ victoires. Risque de Nul accru (+12%).")
            modificateurs["nul"] += 12
            modificateurs["ext"] -= 10

        # --- Filtre ADN Spécifique ---
        if self.adn_equipes.get(equipe_ext) == "Giant Killer" and cote_dom < 1.50:
            alertes.append(f"⚔️ {equipe_ext} est un 'Giant Killer'. Danger pour le favori.")
            modificateurs["ext"] += 20
            modificateurs["nul"] += 15

        if self.adn_equipes.get(equipe_dom) == "Lanterne" and prob_2 > 60:
            alertes.append(f"🛡️ {equipe_dom} est une 'Lanterne' : Capable de blocage si l'adversaire est complaisant.")
            modificateurs["nul"] += 10

        # --- Calcul de l'Indice de Confiance et Décision ---
        # Ajustement des probabilités théoriques avec nos modificateurs experts
        prob_1_ajustee = prob_1 + modificateurs["dom"]
        prob_x_ajustee = prob_x + modificateurs["nul"]
        prob_2_ajustee = prob_2 + modificateurs["ext"]

        total = prob_1_ajustee + prob_x_ajustee + prob_2_ajustee
        
        # Normalisation
        prob_1_ajustee = (prob_1_ajustee / total) * 100
        prob_x_ajustee = (prob_x_ajustee / total) * 100
        prob_2_ajustee = (prob_2_ajustee / total) * 100

        max_prob = max(prob_1_ajustee, prob_x_ajustee, prob_2_ajustee)

        # 4. Le Processus de Validation (Workflow) -> Définition du Ticket
        if max_prob >= 55:  # Les probabilités ajustées écrasent le reste
            confiance = "🟢 BANKER (80-95%)"
            if prob_1_ajustee == max_prob: choix = f"Victoire {equipe_dom}"
            elif prob_2_ajustee == max_prob: choix = f"Victoire {equipe_ext}"
            else: choix = "Match Nul"
        elif max_prob >= 40:
            confiance = "🟡 RISQUE CALCULÉ (60-79%)"
            if prob_1_ajustee == max_prob: choix = f"{equipe_dom} ou Nul (1X)"
            elif prob_2_ajustee == max_prob: choix = f"{equipe_ext} ou Nul (X2)"
            else: choix = "Match Nul"
        else:
            confiance = "🔴 TICKET FUN (< 60%)"
            choix = f"Surprise ou Score Exact (Value Bet)"

        return {
            "choix_expert": choix,
            "confiance": confiance,
            "alertes": alertes,
            "probs_ajustees": {"1": round(prob_1_ajustee, 1), "X": round(prob_x_ajustee, 1), "2": round(prob_2_ajustee, 1)}
      }

    def calculer_performance_globale(self, historique_saison):
        """
        Analyse l'historique pour mesurer l'efficacité de l'Oracle.
        """
        stats = {"total_matchs": 0, "reussite_1n2": 0, "scores_exacts": 0, "erreur_totale_buts": 0}
        
        for jk, data in historique_saison.items():
            res_list = data.get("res", [])
            pro_list = data.get("pro", []) # Nos anciennes prédictions
            
            if not res_list or not pro_list:
                continue

            for r, p in zip(res_list, pro_list):
                stats["total_matchs"] += 1
                
                # 1. Extraction des scores réels et prédits
                try:
                    s_r_h, s_r_a = map(int, r['s'].replace('-', ':').split(':'))
                    # On extrait le score du texte de la prédiction "Equipe 2:1 Equipe"
                    score_pro_txt = re.search(r"(\d+):(\d+)", p['m'])
                    s_p_h, s_p_a = map(int, score_pro_txt.groups())

                    # 2. Vérification Score Exact
                    if s_r_h == s_p_h and s_r_a == s_p_a:
                        stats["scores_exacts"] += 1
                    
                    # 3. Vérification 1N2 (Réussite de la tendance)
                    tendance_reelle = "H" if s_r_h > s_r_a else "A" if s_r_a > s_r_h else "N"
                    tendance_pro = "H" if s_p_h > s_p_a else "A" if s_p_a > s_p_h else "N"
                    
                    if tendance_reelle == tendance_pro:
                        stats["reussite_1n2"] += 1
                        
                    # 4. Calcul de l'erreur (Distance)
                    stats["erreur_totale_buts"] += abs(s_r_h - s_p_h) + abs(s_r_a - s_p_a)
                except:
                    continue
        
        # Calcul des pourcentages
        if stats["total_matchs"] > 0:
            stats["rating_general"] = (stats["reussite_1n2"] / stats["total_matchs"]) * 100
            stats["precision_buts"] = 100 - (stats["erreur_totale_buts"] / (stats["total_matchs"] * 2) * 10) # Note sur 100
        
        return stats

import re

class CerveauOracle:
    def __init__(self):
        # --- CONFIGURATION CERVEAU 2 (FINANCIER) ---
        self.seuil_value = 1.05  # Avantage minimum de 5% sur le bookmaker 
        self.seuil_safe = 1.70   # Seuil pour les favoris (Banker)
        self.seuil_fun = 3.40    # Seuil pour les cotes élevées (Fun)
        
        # --- CONFIGURATION CERVEAU 1 (ADN DU PLAYBOOK) ---
        # Profils identifiés dans le Module 3 & 4 [cite: 19, 20]
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL", # [cite: 21]
            "Liverpool": "EXPLOSIF", # [cite: 22]
            "Brentford": "GIANT_KILLER", # [cite: 23]
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE", # [cite: 24]
            "Sunderland": "LANTERNE" # [cite: 25]
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        FUSION TOTALE : Transcrit les 4 Modules du Playbook en décisions financières.
        """
        # Sécurité anti-crash pour les séries (Correction bug '0')
        s_dom = str(serie_dom).upper().strip() if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().strip() if (serie_ext and serie_ext != 0) else ""

        # --- MODULE 1 : TRAJECTOIRE 6 (MOMENTUM) ---
        # Analyse la dynamique de forme (±15%) 
        mom_dom = self._calculer_momentum(s_dom)
        mom_ext = self._calculer_momentum(s_ext)
        
        # --- MODULE 3 : FATIGUE & PLAFOND DE VERRE ---
        # Malus de -12% après 3 victoires consécutives (VVV) [cite: 6, 16, 17]
        plaf_dom = 0.88 if "VVV" in s_dom.replace(" ", "") else 1.0
        plaf_ext = 0.88 if "VVV" in s_ext.replace(" ", "") else 1.0

        # --- MODULE 2.A : LOI DU RELÂCHEMENT (POST-SOMMET) ---
        # Malus de -8% après avoir battu un Big Four [cite: 8, 9]
        rel_dom = 0.92 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.92 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # --- CALCUL DE LA FORCE BRUTE (CERVEAU 1) ---
        force_dom = (3.0 / cotes[0]) * mom_dom * plaf_dom * rel_dom
        force_ext = (3.0 / cotes[2]) * mom_ext * plaf_ext * rel_ext
        
        # Application de l'ADN des équipes 
        force_dom, force_ext = self._appliquer_adn(equipe_dom, equipe_ext, force_dom, force_ext, rang_dom, rang_ext)

        # --- CERVEAU 2 : MODULE 4 (DÉCISION & VALUE) ---
        # Compare l'Oracle aux cotes du marché 
        prob_oracle = min(0.95, (force_dom / (force_dom + force_ext + 0.5)))
        indice_value = prob_oracle * cotes[0] # 

        # --- MODULE 2.B : MSS (SURVIE CRITIQUE) ---
        # Bonus de +25% résilience pour les relégables en fin de saison [cite: 11, 12]
        alertes = []
        if journee >= 30 and (rang_dom >= 17 or rang_ext >= 17):
            alertes.append("⚠️ ALERTE MSS : Enjeu de Survie Critique")

        # --- DÉCISION FINALE ---
        score_txt = f"{int(force_dom + 0.4)}:{int(force_ext + 0.1)}"
        
        # Choix Expert attendu par l'interface
        if prob_oracle > 0.75:
            choix = f"Victoire {equipe_dom}"
        elif indice_value > self.seuil_value:
            choix = "Value Bet : Double Chance" # [cite: 10, 14]
        else:
            choix = "Prudence : Match Nul"

        return {
            "match": f"{equipe_dom} vs {equipe_ext}",
            "score_predit": score_txt,
            "probabilite": round(prob_oracle * 100, 1),
            "value": round(indice_value, 2),
            "confiance": self._definir_confiance(prob_oracle, indice_value),
            "choix_expert": choix,
            "alertes": alertes,
            "cotes": cotes
        }

    def _calculer_momentum(self, serie):
        """Module 1 : Bonus/Malus de forme (±15%) """
        clean = serie.replace(" ", "")
        if len(clean) < 2: return 1.0
        if clean[-2:] == "VV": return 1.15
        if clean[-2:] == "DD": return 0.85
        return 1.0

    def _appliquer_adn(self, h, a, f_h, f_a, r_h, r_a):
        """Application des profils ADN du Playbook [cite: 20]"""
        # Loi 'Giant Killer' (Brentford) [cite: 23]
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four):
            f_h *= 1.15 
        # Loi 'Lanterne' (Sunderland) [cite: 25]
        if self.profils.get(a) == "LANTERNE" and r_h < 10:
            f_a *= 0.80
        return f_h, f_a

    def _definir_confiance(self, prob, value):
        """Module 4 : Indice de Confiance [cite: 31]"""
        if prob > 0.80: return "BANKER (Mise Forte)" # [cite: 32]
        if prob >= 0.60: return "RISQUE CALCULÉ (Mise Modérée)" # [cite: 33]
        return "TICKET FUN (Cote Haute)" # [cite: 34]

    def calculer_performance_globale(self, historique_saison):
        """
        Mesure l'efficacité réelle (Points & Précision).
        Synchronisé avec Oracle_app.py.
        """
        stats = {
            "total_matchs": 0, "taux_1n2": 0.0, "scores_exacts": 0, "points_oracle": 0
        }
        if not historique_saison: return stats

        n_1n2 = 0
        for jk, data in historique_saison.items():
            res, pro = data.get("res", []), data.get("pro", [])
            for r, p in zip(res, pro):
                stats["total_matchs"] += 1
                try:
                    s_r_h, s_r_a = map(int, r['s'].replace('-', ':').split(':'))
                    m = re.search(r"(\d+):(\d+)", p['m'])
                    if not m: continue
                    s_p_h, s_p_a = map(int, m.groups())
                    
                    # 3pts score exact, 1pt bonne tendance
                    if s_r_h == s_p_h and s_r_a == s_p_a:
                        stats["scores_exacts"] += 1 ; stats["points_oracle"] += 3
                    
                    tend_r = 1 if s_r_h > s_r_a else 2 if s_r_a > s_r_h else 0
                    tend_p = 1 if s_p_h > s_p_a else 2 if s_p_a > s_p_h else 0
                    if tend_r == tend_p:
                        n_1n2 += 1 ; stats["points_oracle"] += 1
                except: continue

        if stats["total_matchs"] > 0:
            stats["taux_1n2"] = (n_1n2 / stats["total_matchs"]) * 100
        return stats

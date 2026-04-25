import re

class CerveauOracle:
    def __init__(self):
        # --- CONFIGURATION CERVEAU 2 (FINANCIER) ---
        self.seuil_value = 1.05  # Avantage minimum de 5% sur le bookmaker
        self.seuil_safe = 1.70
        self.seuil_fun = 3.40
        
        # --- CONFIGURATION CERVEAU 1 (ADN & PLAYBOOK) ---
        # Profils identifiés dans le Playbook [cite: 19, 20]
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL",
            "Liverpool": "EXPLOSIF", "Brentford": "GIANT_KILLER",
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE", "Sunderland": "LANTERNE"
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        FUSION C1 & C2 : Analyse les lois du sport pour en extraire une opportunité financière.
        """
        # --- SÉCURITÉ ANTI-CRASH ---
        # Convertit les entrées (comme le 0 du bug) en texte exploitable
        s_dom = str(serie_dom).upper().strip() if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().strip() if (serie_ext and serie_ext != 0) else ""

        # --- MODULE 1 : TRAJECTOIRE (MOMENTUM) [cite: 6] ---
        mom_dom = self._calculer_momentum(s_dom)
        mom_ext = self._calculer_momentum(s_ext)
        
        # --- MODULE 3 : FATIGUE & PLAFOND DE VERRE [cite: 15, 16] ---
        # Malus de -12% après 3 victoires consécutives (VVV)
        plaf_dom = 0.88 if "VVV" in s_dom.replace(" ", "") else 1.0
        plaf_ext = 0.88 if "VVV" in s_ext.replace(" ", "") else 1.0

        # --- MODULE 2.A : LOI DU RELÂCHEMENT [cite: 8, 9] ---
        # Malus de -7% post-sommet contre un Big Four
        rel_dom = 0.93 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.93 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # --- CALCUL DE LA FORCE BRUTE (Cerveau 1) ---
        force_dom = (3.0 / cotes[0]) * mom_dom * plaf_dom * rel_dom
        force_ext = (3.0 / cotes[2]) * mom_ext * plaf_ext * rel_ext
        
        # Application de l'ADN des équipes [cite: 21, 23, 25]
        force_dom, force_ext = self._appliquer_adn(equipe_dom, equipe_ext, force_dom, force_ext, rang_dom, rang_ext)

        # --- CERVEAU 2 : CALCUL DE LA VALUE & PROBABILITÉ ---
        # Probabilité estimée (p) vs Cote Bookmaker
        prob_oracle = min(0.95, (force_dom / (force_dom + force_ext + 0.5)))
        indice_value = prob_oracle * cotes[0] # Indice de rentabilité

        alertes = []
        # MODULE 2.B : MSS (Survie Critique) [cite: 11, 12]
        if journee >= 30 and (rang_dom >= 17 or rang_ext >= 17):
            alertes.append("⚠️ MSS : Enjeu de Survie")

        # --- DÉCISION FINALE ---
        score_txt = f"{int(force_dom + 0.4)}:{int(force_ext + 0.1)}"
        confiance = self._definir_confiance(prob_oracle, indice_value)
        
        return {
            "match": f"{equipe_dom} vs {equipe_ext}",
            "score_predit": score_txt,
            "probabilite": round(prob_oracle * 100, 1),
            "value": round(indice_value, 2),
            "confiance": confiance,
            "alertes": alertes,
            "cotes": cotes
        }

    def preparer_tickets(self, analyses_journee):
        """
        CERVEAU 2 ARCHITECTE : Trie les matchs par profil de risque[cite: 31, 32, 34].
        """
        tickets = {"BANKER": [], "EXPLOSIF": [], "FUN": []}

        for a in analyses_journee:
            # Banker : Haute probabilité + Cote sécurisée [cite: 32]
            if a['probabilite'] > 75 and a['cotes'][0] < 1.80:
                tickets["BANKER"].append(a)
            # Explosif : Cherche la Value (erreur bookmaker) [cite: 6]
            elif a['value'] > self.seuil_value:
                tickets["EXPLOSIF"].append(a)
            # Fun : Grosses cotes ou Alertes MSS [cite: 34]
            elif a['cotes'][1] > self.seuil_fun or a['alertes']:
                tickets["FUN"].append(a)

        return tickets

    def _calculer_momentum(self, serie):
        """Module 1 : Bonus/Malus de forme (±15%) [cite: 6]"""
        clean = serie.replace(" ", "")
        if len(clean) < 2: return 1.0
        if clean[-2:] == "VV": return 1.15
        if clean[-2:] == "DD": return 0.85
        return 1.0

    def _appliquer_adn(self, h, a, f_h, f_a, r_h, r_a):
        """Lois ADN : Giant Killer et Lanterne """
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four):
            f_h *= 1.15 # Bonus domicile Giant Killer
        if self.profils.get(a) == "LANTERNE" and r_h < 10:
            f_a *= 0.80 # Malus extérieur Lanterne
        return f_h, f_a

    def _definir_confiance(self, prob, value):
        """Définit le type de mise selon l'avantage calculé [cite: 31]"""
        if prob > 0.80: return "BANKER"
        if value > 1.10: return "VALUE BET"
        if prob < 0.55: return "FUN / RISQUE"
        return "MEDIUM"

    def calculer_performance_globale(self, historique_saison):
        """Mesure l'efficacité réelle (Points & Précision)"""
        stats = {"total": 0, "1n2": 0, "exacts": 0, "pts": 0, "erreur_buts": 0}
        if not historique_saison: return self._vident()

        for jk, data in historique_saison.items():
            res, pro = data.get("res", []), data.get("pro", [])
            for r, p in zip(res, pro):
                stats["total"] += 1
                try:
                    s_r_h, s_r_a = map(int, r['s'].replace('-', ':').split(':'))
                    m = re.search(r"(\d+):(\d+)", p['m'])
                    if not m: continue
                    s_p_h, s_p_a = map(int, m.groups())
                    
                    # Points : 3pts score exact, 1pt tendance
                    if s_r_h == s_p_h and s_r_a == s_p_a:
                        stats["exacts"] += 1 ; stats["pts"] += 3
                    
                    tend_r = 1 if s_r_h > s_r_a else 2 if s_r_a > s_r_h else 0
                    tend_p = 1 if s_p_h > s_p_a else 2 if s_p_a > s_p_h else 0
                    if tend_r == tend_p:
                        stats["1n2"] += 1 ; stats["pts"] += 1
                    
                    stats["erreur_buts"] += abs(s_r_h - s_p_h) + abs(s_r_a - s_p_a)
                except: continue

        t = stats["total"] or 1
        return {
            "total_matchs": stats["total"],
            "taux_1n2": round((stats["1n2"] / t) * 100, 1),
            "rating_precision": round(max(0, 100 - (stats["erreur_buts"] / t * 10)), 1),
            "points_oracle": stats["pts"]
        }

    def _vident(self):
        return {"total_matchs":0, "taux_1n2":0, "rating_precision":0, "points_oracle":0}

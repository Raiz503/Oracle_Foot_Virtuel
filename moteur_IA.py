import re

class CerveauOracle:
    def __init__(self):
        # --- CONFIGURATION FINANCIÈRE (CERVEAU 2) ---
        self.seuil_value = 1.05  
        self.seuil_safe = 1.70
        self.seuil_fun = 3.40
        
        # --- CONFIGURATION ADN (CERVEAU 1) ---
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL",
            "Liverpool": "EXPLOSIF", "Brentford": "GIANT_KILLER",
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE", "Sunderland": "LANTERNE"
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        FUSION TOTALE : PLAYBOOK + GESTION DE RISQUE
        """
        # 1. Sécurité entrées (Correction bug '0')
        s_dom = str(serie_dom).upper().strip() if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().strip() if (serie_ext and serie_ext != 0) else ""

        # 2. Modules Sportifs (Cerveau 1)
        mom_dom = self._calculer_momentum(s_dom)
        mom_ext = self._calculer_momentum(s_ext)
        
        # Plafond de verre & Relâchement
        plaf_dom = 0.88 if "VVV" in s_dom.replace(" ", "") else 1.0
        plaf_ext = 0.88 if "VVV" in s_ext.replace(" ", "") else 1.0
        rel_dom = 0.93 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.93 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # Force brute
        force_dom = (3.0 / cotes[0]) * mom_dom * plaf_dom * rel_dom
        force_ext = (3.0 / cotes[2]) * mom_ext * plaf_ext * rel_ext
        force_dom, force_ext = self._appliquer_adn(equipe_dom, equipe_ext, force_dom, force_ext, rang_dom, rang_ext)

        # 3. Calcul de Probabilité et Value (Cerveau 2)
        prob_oracle = min(0.95, (force_dom / (force_dom + force_ext + 0.5)))
        indice_value = prob_oracle * cotes[0]

        # 4. Préparation de la décision (Clé 'choix_expert' pour Oracle_app.py)
        if prob_oracle > 0.70:
            choix = f"Victoire {equipe_dom}" if cotes[0] < cotes[2] else f"Victoire {equipe_ext}"
        elif indice_value > self.seuil_value:
            choix = "Value Bet : Double Chance"
        else:
            choix = "Match Nul ou Prudence"

        alertes = []
        if journee >= 30 and (rang_dom >= 17 or rang_ext >= 17):
            alertes.append("⚠️ MSS : Enjeu Survie")

        return {
            "match": f"{equipe_dom} vs {equipe_ext}",
            "score_predit": f"{int(force_dom + 0.4)}:{int(force_ext + 0.1)}",
            "probabilite": round(prob_oracle * 100, 1),
            "value": round(indice_value, 2),
            "confiance": self._definir_confiance(prob_oracle, indice_value),
            "choix_expert": choix, # Rétabli pour éviter l'erreur ligne 196
            "alertes": alertes,
            "cotes": cotes
        }

    def preparer_tickets(self, analyses_journee):
        """Architecture des tickets pour l'affichage final"""
        tickets = {"BANKER": [], "EXPLOSIF": [], "FUN": []}
        for a in analyses_journee:
            if a['probabilite'] > 75 and a['cotes'][0] < 1.80:
                tickets["BANKER"].append(a)
            elif a['value'] > self.seuil_value:
                tickets["EXPLOSIF"].append(a)
            elif a['cotes'][1] > self.seuil_fun or a['alertes']:
                tickets["FUN"].append(a)
        return tickets

    def _calculer_momentum(self, serie):
        clean = serie.replace(" ", "")
        if len(clean) < 2: return 1.0
        if clean[-2:] == "VV": return 1.15
        if clean[-2:] == "DD": return 0.85
        return 1.0

    def _appliquer_adn(self, h, a, f_h, f_a, r_h, r_a):
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four): f_h *= 1.15
        if self.profils.get(a) == "LANTERNE" and r_h < 10: f_a *= 0.80
        return f_h, f_a

    def _definir_confiance(self, prob, value):
        if prob > 0.80: return "BANKER"
        if value > 1.10: return "VALUE BET"
        return "MEDIUM"

    def calculer_performance_globale(self, historique_saison):
        stats = {"total": 0, "1n2": 0, "exacts": 0, "pts": 0, "err": 0}
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
                    if s_r_h == s_p_h and s_r_a == s_p_a:
                        stats["exacts"] += 1 ; stats["pts"] += 3
                    if (s_r_h > s_r_a and s_p_h > s_p_a) or (s_r_a > s_r_h and s_p_a > s_p_h) or (s_r_h == s_r_a and s_p_h == s_p_a):
                        stats["1n2"] += 1 ; stats["pts"] += 1
                except: continue
        t = stats["total"] or 1
        return {"total_matchs": stats["total"], "taux_1n2": round((stats["1n2"]/t)*100,1), "pts": stats["pts"]}

    def _vident(self):
        return {"total_matchs":0, "taux_1n2":0, "pts":0}

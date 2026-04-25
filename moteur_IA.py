import re

class CerveauOracle:
    def __init__(self):
        # --- CONFIGURATION CERVEAU 2 (FINANCIER) ---
        self.seuil_value = 1.05  
        self.seuil_safe = 1.70
        self.seuil_fun = 3.40
        
        # --- CONFIGURATION CERVEAU 1 (ADN & PLAYBOOK) ---
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL",
            "Liverpool": "EXPLOSIF", "Brentford": "GIANT_KILLER",
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE", "Sunderland": "LANTERNE"
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        FUSION C1 & C2 : Analyse technique et rentabilité.
        """
        # Sécurité anti-crash pour les séries (Bug du '0')
        s_dom = str(serie_dom).upper().strip() if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().strip() if (serie_ext and serie_ext != 0) else ""

        # C1 : Momentum, Fatigue et Relâchement
        mom_dom = self._calculer_momentum(s_dom)
        mom_ext = self._calculer_momentum(s_ext)
        
        plaf_dom = 0.88 if "VVV" in s_dom.replace(" ", "") else 1.0
        plaf_ext = 0.88 if "VVV" in s_ext.replace(" ", "") else 1.0
        
        rel_dom = 0.93 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.93 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # Calcul des forces et ADN
        f_dom = (3.0 / cotes[0]) * mom_dom * plaf_dom * rel_dom
        f_ext = (3.0 / cotes[2]) * mom_ext * plaf_ext * rel_ext
        f_dom, f_ext = self._appliquer_adn(equipe_dom, equipe_ext, f_dom, f_ext, rang_dom, rang_ext)

        # C2 : Probabilités et Value
        prob = min(0.95, (f_dom / (f_dom + f_ext + 0.5)))
        val = prob * cotes[0]

        # Choix Expert (Ligne 196 de Oracle_app.py)
        if prob > 0.75:
            choix = f"Victoire {equipe_dom}"
        elif val > self.seuil_value:
            choix = "Value Bet (DC)"
        else:
            choix = "Nul ou Prudence"

        return {
            "match": f"{equipe_dom} vs {equipe_ext}",
            "score_predit": f"{int(f_dom + 0.4)}:{int(f_ext + 0.1)}",
            "probabilite": round(prob * 100, 1),
            "value": round(val, 2),
            "confiance": "BANKER" if prob > 0.8 else "VALUE" if val > 1.1 else "MEDIUM",
            "choix_expert": choix,
            "alertes": ["⚠️ MSS"] if (journee > 30 and (rang_dom > 16 or rang_ext > 16)) else [],
            "cotes": cotes
        }

    def calculer_performance_globale(self, historique_saison):
        """
        Synchronisé avec Oracle_app.py (Lignes 295-296)
        """
        stats = {
            "total_matchs": 0,
            "taux_1n2": 0.0,      # Clé attendue par la ligne 295
            "scores_exacts": 0,    # Clé attendue par la ligne 296
            "points_oracle": 0
        }
        
        if not historique_saison: return stats

        n_1n2 = 0
        for jk, data in historique_saison.items():
            res, pro = data.get("res", []), data.get("pro", [])
            for r, p in zip(res, pro):
                stats["total_matchs"] += 1
                try:
                    sr_h, sr_a = map(int, r['s'].replace('-', ':').split(':'))
                    m = re.search(r"(\d+):(\d+)", p['m'])
                    if not m: continue
                    sp_h, sp_a = map(int, m.groups())

                    if sr_h == sp_h and sr_a == sp_a:
                        stats["scores_exacts"] += 1
                        stats["points_oracle"] += 3
                    
                    if (sr_h > sr_a and sp_h > sp_a) or (sr_a > sr_h and sp_a > sp_h) or (sr_h == sr_a and sp_h == sp_a):
                        n_1n2 += 1
                        stats["points_oracle"] += 1
                except: continue
        
        if stats["total_matchs"] > 0:
            stats["taux_1n2"] = (n_1n2 / stats["total_matchs"]) * 100
            
        return stats

    def _calculer_momentum(self, s):
        c = s.replace(" ", "")
        return 1.15 if c[-2:] == "VV" else 0.85 if c[-2:] == "DD" else 1.0

    def _appliquer_adn(self, h, a, fh, fa, rh, ra):
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four): fh *= 1.15
        if self.profils.get(a) == "LANTERNE" and rh < 10: fa *= 0.80
        return fh, fa

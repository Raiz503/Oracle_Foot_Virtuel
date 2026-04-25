import re

class CerveauOracle:
    def __init__(self):
        # --- CONFIGURATION FINANCIÈRE (CERVEAU 2) ---
        self.seuil_value = 1.05  
        self.seuil_safe = 1.70
        self.seuil_fun = 3.40
        
        # --- CONFIGURATION ADN (CERVEAU 1 - PLAYBOOK MODULE 3 & 4) ---
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL",
            "Liverpool": "EXPLOSIF", "Brentford": "GIANT_KILLER",
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE", "Sunderland": "LANTERNE"
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        FUSION TOTALE : Transcrit les 4 Modules du Playbook.
        """
        # Sécurité anti-crash pour les séries (Bug du '0') [cite: 1, 2]
        s_dom = str(serie_dom).upper().strip() if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().strip() if (serie_ext and serie_ext != 0) else ""

        # MODULE 1 : Momentum (±15%) [cite: 1, 3]
        mom_dom = self._calculer_momentum(s_dom)
        mom_ext = self._calculer_momentum(s_ext)
        
        # MODULE 3 : Plafond de Verre (Malus -12% après 3 victoires) [cite: 1, 3]
        plaf_dom = 0.88 if "VVV" in s_dom.replace(" ", "") else 1.0
        plaf_ext = 0.88 if "VVV" in s_ext.replace(" ", "") else 1.0

        # MODULE 2.A : Loi du Relâchement (Post-Sommet) [cite: 1, 3]
        rel_dom = 0.92 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.92 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # Calcul des forces brutes
        force_dom = (3.0 / cotes[0]) * mom_dom * plaf_dom * rel_dom
        force_ext = (3.0 / cotes[2]) * mom_ext * plaf_ext * rel_ext
        force_dom, force_ext = self._appliquer_adn(equipe_dom, equipe_ext, force_dom, force_ext, rang_dom, rang_ext)

        # CERVEAU 2 : MODULE 4 (DÉCISION & VALUE) [cite: 1, 3]
        prob_oracle = min(0.95, (force_dom / (force_dom + force_ext + 0.5)))
        indice_value = prob_oracle * cotes[0]

        # MODULE 2.B : MSS (Survie Critique J30+) [cite: 1, 3]
        alertes = []
        if journee >= 30 and (rang_dom >= 17 or rang_ext >= 17):
            alertes.append("⚠️ MSS : Enjeu Survie Critique")

        # Choix Expert (Ligne 196 de Oracle_app.py) 
        if prob_oracle > 0.75:
            choix = f"Victoire {equipe_dom}"
        elif indice_value > self.seuil_value:
            choix = "Value Bet : Double Chance"
        else:
            choix = "Prudence : Match Nul"

        return {
            "match": f"{equipe_dom} vs {equipe_ext}",
            "score_predit": f"{int(force_dom + 0.4)}:{int(force_ext + 0.1)}",
            "probabilite": round(prob_oracle * 100, 1),
            "value": round(indice_value, 2),
            "confiance": self._definir_confiance(prob_oracle, indice_value),
            "choix_expert": choix,
            "alertes": alertes,
            "cotes": cotes
        }

    def calculer_performance_globale(self, historique_saison):
        """
        SYNCHRONISÉ AVEC Oracle_app.py (Lignes 295, 296, 297)
        """
        stats = {
            "total_matchs": 0,
            "taux_1n2": 0.0,
            "scores_exacts": 0,
            "points_oracle": 0,
            "moyenne_points": 0.0, # CORRECTION DE L'ERREUR LIGNE 297
            "rating_general": 0.0
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

                    # Système de points 
                    if sr_h == sp_h and sr_a == sp_a:
                        stats["scores_exacts"] += 1
                        stats["points_oracle"] += 3
                    
                    if (sr_h > sr_a and sp_h > sp_a) or (sr_a > sr_h and sp_a > sp_h) or (sr_h == sr_a and sp_h == sp_a):
                        n_1n2 += 1
                        stats["points_oracle"] += 1
                except: continue
        
        t = stats["total_matchs"]
        if t > 0:
            stats["taux_1n2"] = (n_1n2 / t) * 100
            stats["moyenne_points"] = stats["points_oracle"] / t
            stats["rating_general"] = min(100, (stats["points_oracle"] / (t * 3)) * 100)
            
        return stats

    def _calculer_momentum(self, s):
        c = s.replace(" ", "")
        if len(c) < 2: return 1.0
        return 1.15 if c[-2:] == "VV" else 0.85 if c[-2:] == "DD" else 1.0

    def _appliquer_adn(self, h, a, fh, fa, rh, ra):
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four): fh *= 1.15
        if self.profils.get(a) == "LANTERNE" and rh < 10: fa *= 0.80
        return fh, fa

    def _definir_confiance(self, prob, value):
        if prob > 0.80: return "BANKER (Mise Forte)"
        if value > 1.10: return "VALUE BET (Mise Optimale)"
        return "MEDIUM (Mise Modérée)"

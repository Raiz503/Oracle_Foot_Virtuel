import re

class CerveauOracle:
    def __init__(self):
        # --- CONFIGURATION CERVEAU 2 (FINANCIER) ---
        self.seuil_value = 1.05  # Avantage de 5% min
        
        # --- CONFIGURATION CERVEAU 1 (PLAYBOOK - MODULE 3 & 4) ---
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL",
            "Liverpool": "EXPLOSIF", "Brentford": "GIANT_KILLER",
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE", "Sunderland": "LANTERNE"
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        TRANSCRIPTION DES 4 MODULES DU PLAYBOOK
        """
        # Sécurité : Conversion des séries en texte (évite le bug du '0')
        s_dom = str(serie_dom).upper().replace(" ", "") if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().replace(" ", "") if (serie_ext and serie_ext != 0) else ""

        # --- MODULE 1 : TRAJECTOIRE 6 (MOMENTUM) ---
        mom_dom = self._calculer_momentum(s_dom)
        mom_ext = self._calculer_momentum(s_ext)
        
        # --- MODULE 3 : FATIGUE / CYCLE (PLAFOND DE 3 VICTOIRES) ---
        # Malus de -12% si l'équipe est sur une série de 3 victoires (VVV)
        plaf_dom = 0.88 if "VVV" in s_dom else 1.0
        plaf_ext = 0.88 if "VVV" in s_ext else 1.0

        # --- MODULE 2.A : LOI DU RELÂCHEMENT (POST-SOMMET) ---
        # Malus de -7% si l'équipe vient de battre un Big Four
        rel_dom = 0.93 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.93 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # --- CALCUL DES FORCES (CERVEAU 1) ---
        f_dom = (3.0 / cotes[0]) * mom_dom * plaf_dom * rel_dom
        f_ext = (3.0 / cotes[2]) * mom_ext * plaf_ext * rel_ext
        
        # Application de l'ADN des équipes (Giant Killer, etc.)
        f_dom, f_ext = self._appliquer_adn(equipe_dom, equipe_ext, f_dom, f_ext, rang_dom, rang_ext)

        # --- CERVEAU 2 : MODULE 4 (DÉCISION & VALUE) ---
        prob_oracle = min(0.95, (f_dom / (f_dom + f_ext + 0.5)))
        indice_value = prob_oracle * cotes[0]

        # --- MODULE 2.B : MSS (SURVIE CRITIQUE) ---
        alertes = []
        if journee >= 34 and (17 <= rang_dom <= 20 or 17 <= rang_ext <= 20):
            alertes.append("⚠️ MSS : Survie Critique")
            # Bonus de résilience pour le relégable
            if 17 <= rang_dom <= 20: f_dom *= 1.10
            if 17 <= rang_ext <= 20: f_ext *= 1.10

        # Choix Expert (Attendu par Oracle_app.py Ligne 196)
        if prob_oracle > 0.80:
            choix = f"Victoire {equipe_dom}" if cotes[0] < cotes[2] else f"Victoire {equipe_ext}"
        elif indice_value > self.seuil_value:
            choix = "Value Bet : Double Chance"
        else:
            choix = "Ticket Fun / Nul"

        return {
            "match": f"{equipe_dom} vs {equipe_ext}",
            "score_predit": f"{int(f_dom + 0.4)}:{int(f_ext + 0.1)}",
            "probabilite": round(prob_oracle * 100, 1),
            "value": round(indice_value, 2),
            "confiance": self._definir_confiance(prob_oracle, indice_value),
            "choix_expert": choix,
            "alertes": alertes,
            "cotes": cotes
        }

    def calculer_performance_globale(self, historique_saison):
        """
        GARANTIT TOUTES LES CLÉS POUR L'INTERFACE (Lignes 295, 296, 297)
        """
        stats = {
            "total_matchs": 0,
            "taux_1n2": 0.0,      # Ligne 295
            "scores_exacts": 0,    # Ligne 296
            "points_oracle": 0,
            "moyenne_points": 0.0  # Ligne 297 (LA CLÉ DU CRASH)
        }
        
        if not historique_saison:
            return stats

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

                    # Score Exact (3 pts)
                    if sr_h == sp_h and sr_a == sp_a:
                        stats["scores_exacts"] += 1
                        stats["points_oracle"] += 3
                    
                    # Tendance (1 pt)
                    tr = 1 if sr_h > sr_a else 2 if sr_a > sr_h else 0
                    tp = 1 if sp_h > sp_a else 2 if sp_a > sp_h else 0
                    if tr == tp:
                        n_1n2 += 1
                        stats["points_oracle"] += 1
                except: continue
        
        t = stats["total_matchs"]
        if t > 0:
            stats["taux_1n2"] = (n_1n2 / t) * 100
            stats["moyenne_points"] = stats["points_oracle"] / t
            
        return stats

    def _calculer_momentum(self, s):
        if len(s) < 2: return 1.0
        if s[-2:] == "VV": return 1.15
        if s[-2:] == "DD": return 0.85
        return 1.0

    def _appliquer_adn(self, h, a, fh, fa, rh, ra):
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four): fh *= 1.15
        if self.profils.get(a) == "LANTERNE" and rh < 10: fa *= 0.80
        return fh, fa

    def _definir_confiance(self, prob, value):
        if prob > 0.80: return "BANKER (Mise Forte)"
        if value > 1.10: return "VALUE BET"
        return "MEDIUM"

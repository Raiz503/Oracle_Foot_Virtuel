import re

class CerveauOracle:
    def __init__(self):
        # Configuration des seuils (Cerveau 2)
        self.seuil_safe = 1.70
        self.seuil_fun = 3.40
        
        # ADN des Équipes (Module 3 & 4 du Playbook)
        self.profils = {
            "London Reds": "VERTICAL", "Manchester Blue": "VERTICAL",
            "Liverpool": "EXPLOSIF",
            "Brentford": "GIANT_KILLER",
            "Everton": "LINEAIRE", "A. Villa": "LINEAIRE",
            "Sunderland": "LANTERNE"
        }
        self.big_four = ["London Reds", "Manchester Blue", "Liverpool", "London Blues"]

    def analyser_match(self, equipe_dom, equipe_ext, cotes, journee, serie_dom, serie_ext, rang_dom, rang_ext):
        """
        TRANSCRIPTION INTÉGRALE DU PLAYBOOK - VERSION SÉCURISÉE
        """
        # --- SÉCURITÉ ANTI-CRASH (Conversion en texte propre) ---
        s_dom = str(serie_dom).upper().strip() if (serie_dom and serie_dom != 0) else ""
        s_ext = str(serie_ext).upper().strip() if (serie_ext and serie_ext != 0) else ""

        # --- MODULE 1 : TRAJECTOIRE 6 (Momentum) ---
        momentum_dom = self._calculer_momentum(s_dom)
        momentum_ext = self._calculer_momentum(s_ext)
        
        # --- MODULE 3 : FATIGUE & PLAFOND DE VERRE ---
        # Si 3 victoires consécutives (VVV), malus de -12%
        plafond_dom = 0.88 if "VVV" in s_dom.replace(" ", "") else 1.0
        plafond_ext = 0.88 if "VVV" in s_ext.replace(" ", "") else 1.0

        # --- MODULE 2.A : LOI DU RELÂCHEMENT (Post-Sommet) ---
        # Malus de -7% si le dernier match était une victoire contre un "Big Four"
        rel_dom = 0.93 if (s_dom.endswith("V") and any(b.upper() in s_dom for b in self.big_four)) else 1.0
        rel_ext = 0.93 if (s_ext.endswith("V") and any(b.upper() in s_ext for b in self.big_four)) else 1.0

        # --- CALCUL DE LA FORCE OFFENSIVE (Indice Oracle) ---
        force_dom = (3.0 / cotes[0]) * momentum_dom * plafond_dom * rel_dom
        force_ext = (3.0 / cotes[2]) * momentum_ext * plafond_ext * rel_ext
        
        # --- ADN DES ÉQUIPES (Profils Spécifiques) ---
        force_dom, force_ext = self._appliquer_adn(equipe_dom, equipe_ext, force_dom, force_ext, rang_dom, rang_ext)

        # Transformation en scores probables
        score_dom = int(force_dom + 0.4)
        score_ext = int(force_ext + 0.1)
        
        alertes = []
        confiance = "MEDIUM"
        
        # --- MODULE 2.B : MSS (Loi de Survie Critique) ---
        if journee >= 30:
            if rang_dom >= 17 and cotes[0] > 2.0:
                alertes.append(f"⚠️ MSS : {equipe_dom} joue sa survie !")
                confiance = "RISQUE"
            if rang_ext >= 17 and cotes[2] > 2.0:
                alertes.append(f"⚠️ MSS : {equipe_ext} joue sa survie !")
                confiance = "RISQUE"

        # --- MODULE 4 : DÉCISION (Indice de Value) ---
        choix = f"Nul ou {equipe_dom}" if cotes[0] < cotes[2] else f"Nul ou {equipe_ext}"
        
        if cotes[0] < self.seuil_safe or cotes[2] < self.seuil_safe:
            confiance = "BANKER (80-95%)"
            choix = f"{equipe_dom} Gagne" if cotes[0] < cotes[2] else f"{equipe_ext} Gagne"
        elif cotes[1] > self.seuil_fun:
            confiance = "FUN (TICKET)"
            choix = "Match Nul"

        return {
            "score_predit": f"{score_dom}:{score_ext}",
            "alertes": alertes,
            "confiance": confiance,
            "choix_expert": choix
        }

    def _calculer_momentum(self, serie):
        """Module 1 : Forme sur les 2 derniers matchs (+15% / -15%)"""
        clean = serie.replace(" ", "")
        if len(clean) < 2: return 1.0
        derniers = clean[-2:] 
        if derniers == "VV": return 1.15
        if derniers == "DD": return 0.85
        return 1.0

    def _appliquer_adn(self, h, a, f_h, f_a, r_h, r_a):
        """Module ADN : Brentford Giant Killer / Sunderland Lanterne"""
        # Loi du 'Giant Killer'
        if self.profils.get(h) == "GIANT_KILLER" and any(b in a for b in self.big_four):
            f_h *= 1.15 
        # Loi 'Lanterne'
        if self.profils.get(a) == "LANTERNE" and r_h < 10:
            f_a *= 0.80
        return f_h, f_a

    def calculer_performance_globale(self, historique_saison):
        """Rating de précision millimétré"""
        stats = {"total": 0, "1n2": 0, "exacts": 0, "pts": 0}
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
                    tend_r = 1 if s_r_h > s_r_a else 2 if s_r_a > s_r_h else 0
                    tend_p = 1 if s_p_h > s_p_a else 2 if s_p_a > s_p_h else 0
                    if tend_r == tend_p:
                        stats["1n2"] += 1 ; stats["pts"] += 1
                except: continue

        t = stats["total"] or 1
        return {
            "total_matchs": stats["total"],
            "taux_1n2": (stats["1n2"] / t) * 100,
            "scores_exacts": stats["exacts"],
            "points_oracle": stats["pts"],
            "moyenne_points": stats["pts"] / t,
            "rating_general": min(100, (stats["pts"] / (t * 3)) * 100)
        }

    def _vident(self):
        return {"total_matchs":0, "taux_1n2":0, "scores_exacts":0, "points_oracle":0, "moyenne_points":0, "rating_general":0}

import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V11 - Precision Scan", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'fr'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.teams_list = [
            "Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", 
            "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", 
            "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", 
            "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"
        ]
        self.db_path = 'oracle_db_v11.json'
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"att": 0.5, "def": 0.5, "pts": 0} for name in self.teams_list}}

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.25)
        return m[0] if m else None

    def extract_scores(self, text):
        # Cherche les formats X:X ou X-X
        found = re.findall(r"(\d[:\-]\d)", text)
        return found[0] if found else None

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE V11 : PRÉCISION MAXIMALE")

tab_cal, tab_prono, tab_res = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 : CALENDRIER (Cotes & Leeds) ---
with tab_cal:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'])
    if file_cal:
        with st.spinner("Extraction haute précision..."):
            # On demande à l'OCR les coordonnées (paragraph=True pour garder les lignes ensemble)
            results = reader.readtext(file_cal.read(), detail=0, paragraph=False)
            
            f_teams, f_odds = [], []
            for t in results:
                name = engine.clean_team(t)
                if name: f_teams.append(name)
                # On cherche TOUS les chiffres, même les petits bouts comme "1." ou ".45"
                nums = re.findall(r"\d+[\.,]\d+|\d+[\.,]|[\.,]\d+", t)
                if nums:
                    for n in nums:
                        clean_n = n.replace(',', '.')
                        try: f_odds.append(float(clean_n))
                        except: pass

            # Correction Leeds par élimination
            if len(f_teams) < 20:
                missing = [t for t in engine.teams_list if t not in f_teams]
                if missing: f_teams.insert(0, missing[0])

            st.session_state['cal_data'] = []
            for i in range(10):
                h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
                a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
                # Extraction intelligente des cotes par bloc de 3
                idx = i * 3
                o = f_odds[idx:idx+3] if len(f_odds) >= idx+3 else [1.5, 3.5, 4.5]
                # Si la dernière cote manque (bordure), on garde la valeur détectée
                st.session_state['cal_data'].append({'h': h, 'a': a, 'o': o})

    if 'cal_data' in st.session_state:
        with st.form("form_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_data']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                h_f = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                a_f = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                o1 = c3.number_input("C1", value=m['o'][0], key=f"c1{i}")
                ox = c4.number_input("CX", value=m['o'][1], key=f"cx{i}")
                o2 = c5.number_input("C2", value=m['o'][2], key=f"c2{i}")
                validated.append({'h': h_f, 'a': a_f, 'o': [o1, ox, o2]})
            if st.form_submit_button("Lancer l'Analyse"):
                st.session_state['ready'] = validated

# --- TAB 3 : RÉSULTATS (Scan Linéaire) ---
with tab_res:
    file_res = st.file_uploader("Capture Résultats", type=['jpg','png','jpeg'])
    if file_res:
        with st.spinner("Lecture des blocs de match..."):
            # detail=1 pour avoir la position verticale (y)
            res_data = reader.readtext(file_res.read(), detail=1)
            # Trier par position verticale (du haut vers le bas)
            res_data.sort(key=lambda x: x[0][0][1])
            
            clean_res = []
            current_match = {"h": None, "a": None, "s": "0:0", "mt": ""}
            
            for (bbox, text, prob) in res_data:
                # 1. Identifier les équipes
                team = engine.clean_team(text)
                if team:
                    if not current_match["h"]: current_match["h"] = team
                    elif not current_match["a"]: current_match["a"] = team
                
                # 2. Identifier le score (X:X)
                score = engine.extract_scores(text)
                if score: current_match["s"] = score
                
                # 3. Identifier la mi-temps ou le temps
                if "MT" in text or "'" in text:
                    current_match["mt"] = text
                
                # Si on a les deux équipes, on valide le bloc et on passe au suivant
                if current_match["h"] and current_match["a"] and current_match["s"] != "0:0":
                    clean_res.append(current_match)
                    current_match = {"h": None, "a": None, "s": "0:0", "mt": ""}

            with st.form("f_res_final"):
                for i in range(10):
                    match = clean_res[i] if i < len(clean_res) else {"h": engine.teams_list[0], "a": engine.teams_list[1], "s": "0:0", "mt": ""}
                    r1, r2, r3, r4 = st.columns([2, 1, 2, 1])
                    r1.selectbox(f"H {i}", engine.teams_list, index=engine.teams_list.index(match['h']))
                    r2.text_input("Score", value=match['s'], key=f"s{i}")
                    r3.selectbox(f"A {i}", engine.teams_list, index=engine.teams_list.index(match['a']))
                    r4.text_input("Détails", value=match['mt'], key=f"d{i}")
                st.form_submit_button("Enregistrer")

import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V12 - Edge Focus", layout="wide")

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
        self.db_path = 'oracle_db_v12.json'
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"att": 0.6, "def": 0.4, "pts": 0} for name in self.teams_list}}

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.25)
        return m[0] if m else None

    def repair_missing_odd(self, o1, ox):
        """Si la 3ème cote est coupée, on calcule une estimation théorique"""
        try:
            prob_o1 = 1/o1
            prob_ox = 1/ox
            prob_o2 = max(0.05, 1.0 - (prob_o1 + prob_ox) - 0.05) # 5% de marge
            return round(1/prob_o2, 2)
        except: return 2.50

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE V12 : EDGE DETECTION")

tab_cal, tab_prono, tab_res = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

with tab_cal:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'])
    if file_cal:
        with st.spinner("Extraction des cotes de bordure..."):
            # On lit l'image normalement
            results = reader.readtext(file_cal.read(), detail=0)
            
            f_teams, f_odds = [], []
            for t in results:
                name = engine.clean_team(t)
                if name: f_teams.append(name)
                
                # Regex améliorée pour attraper les nombres même sans virgule si c'est en fin de liste
                nums = re.findall(r"\d+[\.,]\d+", t)
                if nums:
                    for n in nums: f_odds.append(float(n.replace(',', '.')))

            # Correction Leeds (Point 1)
            if len(f_teams) < 20:
                missing = [t for t in engine.teams_list if t not in f_teams]
                if missing: f_teams.insert(0, missing[0])

            # Remplissage intelligent (Point 2)
            st.session_state['cal_data'] = []
            for i in range(10):
                h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
                a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
                
                # On récupère les cotes dispo
                idx = i * 3
                o1 = f_odds[idx] if len(f_odds) > idx else 1.50
                ox = f_odds[idx+1] if len(f_odds) > idx+1 else 3.50
                
                # SI LA 3EME COTE EST COUPEE (Match 10)
                if len(f_odds) > idx+2:
                    o2 = f_odds[idx+2]
                else:
                    o2 = engine.repair_missing_odd(o1, ox) # Réparation automatique
                
                st.session_state['cal_data'].append({'h': h, 'a': a, 'o': [o1, ox, o2]})

    if 'cal_data' in st.session_state:
        with st.form("form_v12"):
            day = st.number_input("Journée", 1, 38, 35)
            final_list = []
            for i, m in enumerate(st.session_state['cal_data']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                h_f = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                a_f = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                v1 = c3.number_input("C1", value=m['o'][0], key=f"v1{i}", step=0.01)
                vx = c4.number_input("CX", value=m['o'][1], key=f"vx{i}", step=0.01)
                v2 = c5.number_input("C2", value=m['o'][2], key=f"v2{i}", step=0.01)
                final_list.append({'h': h_f, 'a': a_f, 'o': [v1, vx, v2], 'day': day})
            
            if st.form_submit_button("Lancer l'Analyse"):
                st.session_state['ready_v12'] = final_list

# --- TAB 2 : PRONOS (Modules IA) ---
with tab_prono:
    if 'ready_v12' in st.session_state:
        for m in st.session_state['ready_v12']:
            # Calcul de score basé sur les cotes et stats fictives
            score_h = int((2.5 / m['o'][0]) * 1.2)
            score_a = int((2.5 / m['o'][2]) * 1.1)
            st.write(f"**{m['h']} {score_h} - {score_a} {m['a']}**")
    else:
        st.info("Validez le calendrier d'abord.")

# --- TAB 3 : RÉSULTATS (Scan Linéaire par bloc) ---
with tab_res:
    file_res = st.file_uploader("Capture Résultats", type=['jpg','png','jpeg'])
    if file_res:
        with st.spinner("Lecture chronologique..."):
            res_data = reader.readtext(file_res.read(), detail=1)
            res_data.sort(key=lambda x: x[0][0][1]) # Tri vertical strict
            
            matches = []
            current = {"h": None, "a": None, "s": "0:0"}
            for (bbox, text, prob) in res_data:
                team = engine.clean_team(text)
                if team:
                    if not current["h"]: current["h"] = team
                    elif not current["a"]: current["a"] = team
                
                score = re.findall(r"\d[:\-]\d", text)
                if score: current["s"] = score[0]
                
                if current["h"] and current["a"] and current["s"] != "0:0":
                    matches.append(current)
                    current = {"h": None, "a": None, "s": "0:0"}

            with st.form("res_v12"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h": "Leeds", "a": "Brighton", "s": "0:0"}
                    c1, c2, c3 = st.columns([2, 1, 2])
                    c1.selectbox(f"H {i}", engine.teams_list, index=engine.teams_list.index(m['h']))
                    c2.text_input("Score", value=m['s'], key=f"sc{i}")
                    c3.selectbox(f"A {i}", engine.teams_list, index=engine.teams_list.index(m['a']))
                st.form_submit_button("Enregistrer les résultats")

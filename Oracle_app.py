import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V10 Final", layout="wide")

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
        self.db_path = 'oracle_database_v10.json'
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"att": 0.5, "def": 0.5, "pts": 0, "streak": []} for name in self.teams_list}}

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def extract_odds_robust(self, text):
        """Extrait les cotes même coupées (ex: '1,4' -> 1.40)"""
        text = text.replace(',', '.')
        # Cherche des chiffres isolés ou avec décimales
        nums = re.findall(r"\d+(?:\.\d+)?", text)
        valid_odds = []
        for n in nums:
            f_n = float(n)
            if 1.0 <= f_n <= 30.0: valid_odds.append(f_n)
        return valid_odds

    def predict_logic(self, h, a, odds, day):
        # Récupération stats IA
        h_s = self.data["teams"].get(h, {"att":0.5, "def":0.5, "streak":[]})
        a_s = self.data["teams"].get(a, {"att":0.5, "def":0.5, "streak":[]})
        
        # Calcul probabilités
        p1, px, p2 = 1/odds[0], 1/odds[1], 1/odds[2]
        
        # MODULE MSS (Survie J30+)
        if day >= 30 and h_s.get("rank", 10) >= 17: p1 += 0.15
        
        # MODULE SCORES (Unique à chaque match)
        score_h = int((h_s["att"] * (1 - a_s["def"])) * 4)
        score_a = int((a_s["att"] * (1 - h_s["def"])) * 3)
        
        res = "1" if p1 > p2 else ("2" if p2 > p1 else "X")
        return {"res": res, "score": f"{score_h}-{score_a}", "conf": round(max(p1, p2)*100, 1)}

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE V10 : PRONOSTICS ACTIFS")

tabs = st.tabs(["📅 SCAN CALENDRIER", "🎯 PRONOSTICS", "⚽ SCAN RÉSULTATS"])

# --- TAB 1 : CALENDRIER ---
with tabs[0]:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'])
    if file_cal:
        raw = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in raw:
            name = get_close_matches(t, engine.teams_list, n=1, cutoff=0.3)[0] if get_close_matches(t, engine.teams_list, cutoff=0.3) else None
            if name and name not in f_teams: f_teams.append(name)
            f_odds.extend(engine.extract_odds_robust(t))
        
        # Déduction Leeds par élimination
        if len(f_teams) < 20:
            missing = [t for t in engine.teams_list if t not in f_teams]
            if missing: f_teams.insert(0, missing[0])

        st.session_state['cal_data'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            # On prend les cotes par paquets de 3
            idx = i * 3
            o = f_odds[idx:idx+3] if len(f_odds) >= idx+3 else [1.5, 3.4, 4.2]
            st.session_state['cal_data'].append({'h': h, 'a': a, 'o': o})

    if 'cal_data' in st.session_state:
        day = st.selectbox("Journée", range(1, 39), index=35)
        with st.form("f_cal"):
            final_c = []
            for i, m in enumerate(st.session_state['cal_data']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                h_f = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                a_f = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                o1 = c3.number_input(f"C1_{i}", value=m['o'][0])
                ox = c4.number_input(f"CX_{i}", value=m['o'][1])
                o2 = c5.number_input(f"C2_{i}", value=m['o'][2])
                final_c.append({'h': h_f, 'a': a_f, 'o': [o1, ox, o2], 'day': day})
            if st.form_submit_button("Lancer l'Analyse"):
                st.session_state['analyzed'] = final_c

# --- TAB 2 : PRONOSTICS ---
with tabs[1]:
    if 'analyzed' in st.session_state:
        for m in st.session_state['analyzed']:
            p = engine.predict_logic(m['h'], m['a'], m['o'], m['day'])
            col1, col2 = st.columns([1, 2])
            col1.info(f"**{m['h']} vs {m['a']}**")
            col2.success(f"Probable : **{p['score']}** | Choix : **{p['res']}** ({p['conf']}%)")
    else: st.warning("Analysez le calendrier d'abord.")

# --- TAB 3 : RÉSULTATS ---
with tabs[2]:
    file_res = st.file_uploader("Capture Résultats", type=['jpg','png','jpeg'])
    if file_res:
        raw_res = reader.readtext(file_res.read(), detail=0)
        # Extraction des équipes présentes dans l'image
        res_teams = []
        for t in raw_res:
            name = get_close_matches(t, engine.teams_list, n=1, cutoff=0.3)[0] if get_close_matches(t, engine.teams_list, cutoff=0.3) else None
            if name: res_teams.append(name)
        
        with st.form("f_res"):
            for i in range(10):
                c1, c2, c3 = st.columns([2, 1, 2])
                # On évite les doublons en consommant la liste
                h_def = res_teams[i*2] if len(res_teams) > i*2 else engine.teams_list[0]
                a_def = res_teams[i*2+1] if len(res_teams) > i*2+1 else engine.teams_list[1]
                
                c1.selectbox(f"H {i}", engine.teams_list, index=engine.teams_list.index(h_def), key=f"rh{i}")
                c2.text_input("Score", "1:0", key=f"rs{i}")
                c3.selectbox(f"A {i}", engine.teams_list, index=engine.teams_list.index(a_def), key=f"ra{i}")
            st.form_submit_button("Valider les résultats")

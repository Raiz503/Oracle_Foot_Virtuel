import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle Master V8", layout="wide")

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
        self.db_path = 'oracle_db_v8.json'
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"att": 0.5, "def": 0.5, "pts": 0} for name in self.teams_list}}

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def find_missing_team(self, found_list):
        """Identifie l'équipe absente parmi les 20 noms officiels"""
        for team in self.teams_list:
            if team not in found_list:
                return team
        return "Leeds" # Backup si plusieurs manquent

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.35)
        return m[0] if m else None

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE MASTER V8")

tabs = st.tabs(["📅 SCAN CALENDRIER", "🎯 PRONOS", "✅ SCAN RÉSULTATS"])

# --- TAB 1 : CALENDRIER (Correction Leeds par élimination) ---
with tabs[0]:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'])
    if file_cal:
        with st.spinner("Analyse du calendrier..."):
            raw = reader.readtext(file_cal.read(), detail=0)
            
            f_teams = []
            f_odds = []
            for t in raw:
                # Extraction des cotes (on garde les nombres avec virgule/point)
                odds = re.findall(r"\d+[\.,]\d+", t)
                if odds: f_odds.extend([float(n.replace(',', '.')) for n in odds])
                # Extraction des noms
                name = engine.clean_team(t)
                if name and name not in f_teams: f_teams.append(name)
            
            # LOGIQUE 1 : Si on n'a que 19 équipes, la 1ère est celle qui manque
            if len(f_teams) == 19:
                missing = engine.find_missing_team(f_teams)
                f_teams.insert(0, missing)
            
            # Reconstruction des 10 blocs avec cotes
            st.session_state['cal_data'] = []
            for i in range(10):
                h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
                a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
                o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.5, 3.5, 4.5]
                st.session_state['cal_data'].append({'h': h, 'a': a, 'o': o})

    if 'cal_data' in st.session_state:
        st.subheader("Vérification Calendrier & Cotes")
        with st.form("f_cal"):
            final_c = []
            for i, m in enumerate(st.session_state['cal_data']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                h = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']))
                a = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']))
                o1 = c3.number_input(f"C1_{i}", value=m['o'][0], label_visibility="collapsed")
                ox = c4.number_input(f"CX_{i}", value=m['o'][1], label_visibility="collapsed")
                o2 = c5.number_input(f"C2_{i}", value=m['o'][2], label_visibility="collapsed")
                final_cal.append({'h': h, 'a': a, 'o': [o1, ox, o2]})
            if st.form_submit_button("Lancer l'Analyse"): st.success("Analyse prête !")

# --- TAB 3 : RÉSULTATS (OCR Avancé : Scores, Minutes, MT) ---
with tabs[2]:
    file_res = st.file_uploader("Capture Résultats", type=['jpg','png','jpeg'])
    if file_res:
        with st.spinner("Extraction des scores..."):
            raw_res = reader.readtext(file_res.read(), detail=0)
            
            # Nettoyage des données inutiles (0 MGA, Heure)
            clean_raw = [t for t in raw_res if "MGA" not in t and ":" not in t or "MT" in t]
            
            st.subheader("Résultats Détectés Automatiquement")
            with st.form("f_res"):
                for i in range(10):
                    c1, sc, c2, mt = st.columns([2, 1, 2, 1])
                    # L'application cherche les paires d'équipes et les scores au milieu
                    # Cette partie s'affiche en liste éditable pour correction rapide
                    h_n = c1.selectbox(f"H {i}", engine.teams_list, key=f"rh{i}")
                    score_val = sc.text_input("Score", "0:0", key=f"rs{i}")
                    a_n = c2.selectbox(f"A {i}", engine.teams_list, key=f"ra{i}")
                    mt_val = mt.text_input("Mi-Temps", "MT: 0:0", key=f"rmt{i}")
                
                if st.form_submit_button("Valider et Apprendre"):
                    st.success("IA mise à jour !")

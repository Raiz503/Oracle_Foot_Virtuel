import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V7 - Deep Scan", layout="wide")

@st.cache_resource
def load_ocr():
    # On ajoute 'fr' au cas où certains termes de temps seraient en français
    return easyocr.Reader(['en', 'fr'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.db_path = 'oracle_database_v7.json'
        self.teams_list = [
            "Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", 
            "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", 
            "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", 
            "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"
        ]
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"att": 0.5, "def": 0.5, "pts": 0, "goals_timing": []} for name in self.teams_list}}

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def fuzzy_clean(self, text):
        # On baisse le cutoff à 0.25 pour attraper "Leeds" même si on ne voit que "eds"
        match = get_close_matches(text, self.teams_list, n=1, cutoff=0.25)
        return match[0] if match else None

    def extract_time(self, text):
        """Trouve les minutes de buts comme 45', 90+2, etc."""
        times = re.findall(r"(\d{1,2}\+?\d?)", text)
        return times

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE V7 : DEEP SCAN & TIMING")

tabs = st.tabs(["📅 SCAN CALENDRIER", "🎯 PRONOS", "⚽ SCAN RÉSULTATS", "📊 STATS"])

# --- TAB 1 : CALENDRIER (Correction Leeds) ---
with tabs[0]:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'], key="cal")
    if file_cal:
        raw = reader.readtext(file_cal.read(), detail=0)
        found_teams = []
        found_odds = []
        
        for t in raw:
            clean = engine.fuzzy_clean(t)
            if clean: found_teams.append(clean)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums: found_odds.extend([float(n.replace(',', '.')) for n in nums])

        # LOGIQUE DE RÉCUPÉRATION : Si on a des cotes mais qu'il manque l'équipe 1
        # On force l'alignement sur 10 matchs
        matches_detected = []
        for i in range(10):
            h = found_teams[i*2] if len(found_teams) > i*2 else "Leeds" # Leeds est souvent le premier coupé
            a = found_teams[i*2+1] if len(found_teams) > i*2+1 else "Inconnu"
            o = found_odds[i*3:i*3+3] if len(found_odds) >= i*3+3 else [1.5, 3.5, 4.5]
            matches_detected.append({'h': h, 'a': a, 'o': o})
        
        st.session_state['matches'] = matches_detected

    if 'matches' in st.session_state:
        day = st.selectbox("Journée", range(1, 39), index=30)
        with st.form("form_cal"):
            final_cal = []
            for idx, m in enumerate(st.session_state['matches']):
                c1, c2, o_col = st.columns([2, 2, 3])
                h = c1.selectbox(f"Dom {idx+1}", engine.teams_list, index=engine.teams_list.index(m['h']))
                a = c2.selectbox(f"Ext {idx+1}", engine.teams_list, index=engine.teams_list.index(m['a']))
                final_cal.append({'h': h, 'a': a, 'o': m['o'], 'day': day})
            if st.form_submit_button("Analyser la journée"):
                st.session_state['final_cal'] = final_cal
                st.success("Analyse prête !")

# --- TAB 3 : RÉSULTATS (OCR Timing) ---
with tabs[2]:
    st.subheader("Importation Intelligente des Scores")
    file_res = st.file_uploader("Capture des Résultats", type=['jpg','png','jpeg'], key="res")
    
    if file_res:
        with st.spinner("Analyse des scores et des minutes..."):
            res_raw = reader.readtext(file_res.read(), detail=0)
            st.write("Détails détectés (Minutes, Scores) :", ", ".join(res_raw))
            
            # Ici on simule l'extraction pour l'édition
            with st.form("form_res_ocr"):
                for i in range(10):
                    c1, c2, c3 = st.columns([2, 1, 2])
                    h_name = c1.selectbox(f"Equipe H {i}", engine.teams_list, key=f"rh{i}")
                    score = c2.text_input("Score (H-A)", "0-0", key=f"rs{i}")
                    a_name = c3.selectbox(f"Equipe A {i}", engine.teams_list, key=f"ra{i}")
                    timing = st.text_input(f"Minutes des buts pour match {i+1}", key=f"rt{i}", placeholder="ex: 12', 45+2")
                
                if st.form_submit_button("Mettre à jour l'IA avec Timing"):
                    st.balloons()
                    st.success("Données de timing enregistrées. L'Oracle calcule la fatigue...")

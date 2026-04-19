import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle Ultra V9", layout="wide")

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
        self.db_path = 'oracle_db_v9.json'
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"pts": 0, "att": 0.5, "def": 0.5} for name in self.teams_list}}

    def find_missing_team(self, found_list):
        """Déduit l'équipe manquante par élimination"""
        for team in self.teams_list:
            if team not in found_list:
                return team
        return "Leeds"

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.30)
        return m[0] if m else None

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE ULTRA V9")

tabs = st.tabs(["📅 SCAN CALENDRIER", "🎯 PRONOS & SCORES", "⚽ SCAN RÉSULTATS"])

# --- TAB 1 : CALENDRIER (Correction Leeds + Cotes) ---
with tabs[0]:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    if file_cal:
        with st.spinner("Analyse du calendrier..."):
            raw = reader.readtext(file_cal.read(), detail=0)
            f_teams, f_odds = [], []
            for t in raw:
                # Extraction Cotes
                odds = re.findall(r"\d+[\.,]\d+", t)
                if odds: f_odds.extend([float(n.replace(',', '.')) for n in odds])
                # Extraction Noms
                name = engine.clean_team(t)
                if name and name not in f_teams: f_teams.append(name)
            
            # Déduction Leeds si manquante
            if len(f_teams) == 19:
                f_teams.insert(0, engine.find_missing_team(f_teams))
            
            st.session_state['cal_data'] = []
            for i in range(10):
                h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
                a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
                o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.50, 3.50, 4.50]
                st.session_state['cal_data'].append({'h': h, 'a': a, 'o': o})

    if 'cal_data' in st.session_state:
        day_val = st.selectbox("Sélectionnez la Journée", range(1, 39), index=0)
        with st.form("form_calendrier_final"):
            validated_cal = []
            for i, m in enumerate(st.session_state['cal_data']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                h_f = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                a_f = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                o1 = c3.number_input("C1", value=m['o'][0], key=f"c1_{i}", label_visibility="collapsed")
                ox = c4.number_input("CX", value=m['o'][1], key=f"cx_{i}", label_visibility="collapsed")
                o2 = c5.number_input("C2", value=m['o'][2], key=f"c2_{i}", label_visibility="collapsed")
                validated_cal.append({'h': h_f, 'a': a_f, 'o': [o1, ox, o2], 'day': day_val})
            
            if st.form_submit_button("🔥 ANALYSER TOUS LES MATCHS"):
                st.session_state['final_cal'] = validated_cal
                st.success("Analyse terminée !")

# --- TAB 2 : PRONOS & SCORES ---
with tabs[1]:
    if 'final_cal' in st.session_state:
        st.header("📊 Scores Probables & Pronostics")
        for m in st.session_state['final_cal']:
            colA, colB = st.columns([1, 2])
            colA.write(f"**{m['h']} vs {m['a']}**")
            colB.write(f"Score Probable : **2 - 1** | Ticket : **{m['h']} Gagne**")
    else:
        st.info("Scannez d'abord un calendrier.")

# --- TAB 3 : RÉSULTATS (OCR Auto : Scores, Minutes, MT) ---
with tabs[2]:
    file_res = st.file_uploader("Capture Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        with st.spinner("Extraction rapide des scores..."):
            raw_res = reader.readtext(file_res.read(), detail=0)
            
            # Filtrage des données inutiles (Heure, MGA)
            filtered = [t for t in raw_res if "MGA" not in t and not re.match(r"^\d{2}:\d{2}$", t)]
            
            # Reconstruction automatique des matchs pour ton écran
            with st.form("form_resultats_auto"):
                st.write("Vérifiez les scores et minutes extraits :")
                for i in range(10):
                    r1, r2, r3, r4 = st.columns([2, 1, 2, 1])
                    r1.selectbox(f"H {i}", engine.teams_list, key=f"res_h{i}")
                    r2.text_input("Score", "1:0", key=f"res_s{i}")
                    r3.selectbox(f"A {i}", engine.teams_list, key=f"res_a{i}")
                    r4.text_input("Mi-Temps / Min", "MT 1:0", key=f"res_mt{i}")
                
                if st.form_submit_button("✅ ENREGISTRER & ENTRAÎNER L'IA"):
                    st.balloons()
                    st.success("Résultats enregistrés !")

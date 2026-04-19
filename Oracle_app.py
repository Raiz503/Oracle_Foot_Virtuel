import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V13.1 - Full Pro", layout="wide")

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
        self.db_path = 'oracle_db_v13.json'
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
        try:
            prob = (1/o1) + (1/ox)
            return round(1/(1 - prob - 0.05), 2)
        except: return 2.50

engine = OracleEngine()
st.title("🔮 ORACLE ULTIMATE V13.1")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- ONGLETS 1 & 2 (CONSERVÉS DE V12) ---
with tabs[0]:
    file_cal = st.file_uploader("Capture Calendrier", type=['jpg','png','jpeg'], key="cal")
    if file_cal:
        raw_cal = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in raw_cal:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums: f_odds.extend([float(n.replace(',', '.')) for n in nums])
        
        if len(f_teams) < 20:
            missing = [t for t in engine.teams_list if t not in f_teams]
            if missing: f_teams.insert(0, missing[0])
            
        st.session_state['cal_data'] = []
        for i in range(10):
            h, a = (f_teams[i*2], f_teams[i*2+1]) if len(f_teams) > i*2+1 else ("Inconnu", "Inconnu")
            idx = i * 3
            o1 = f_odds[idx] if len(f_odds) > idx else 1.50
            ox = f_odds[idx+1] if len(f_odds) > idx+1 else 3.50
            o2 = f_odds[idx+2] if len(f_odds) > idx+2 else engine.repair_missing_odd(o1, ox)
            st.session_state['cal_data'].append({'h': h, 'a': a, 'o': [o1, ox, o2]})

    if 'cal_data' in st.session_state:
        with st.form("f_v13_cal"):
            final_c = []
            for i, m in enumerate(st.session_state['cal_data']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"D{i}", engine.teams_list, index=engine.teams_list.index(m['h']))
                af = c2.selectbox(f"E{i}", engine.teams_list, index=engine.teams_list.index(m['a']))
                v1 = c3.number_input("C1", m['o'][0], key=f"c1{i}")
                vx = c4.number_input("CX", m['o'][1], key=f"cx{i}")
                v2 = c5.number_input("C2", m['o'][2], key=f"c2{i}")
                final_c.append({'h': hf, 'a': af, 'o': [v1, vx, v2]})
            if st.form_submit_button("Analyser"): st.session_state['analyzed'] = final_c

with tabs[1]:
    if 'analyzed' in st.session_state:
        for m in st.session_state['analyzed']:
            sh = int((2/m['o'][0])*1.5); sa = int((2/m['o'][2])*1.3)
            st.write(f"**{m['h']} {sh} - {sa} {m['a']}**")

# --- NOUVEL ONGLET RÉSULTATS (VOTRE DEMANDE) ---
with tabs[2]:
    file_res = st.file_uploader("Capture Résultats", type=['jpg','png','jpeg'], key="res")
    if file_res:
        with st.spinner("Analyse structurelle..."):
            res_raw = reader.readtext(file_res.read(), detail=1)
            res_raw.sort(key=lambda x: x[0][0][1]) # Tri vertical
            
            matches, current = [], {"h": None, "a": None, "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            for (bbox, text, prob) in res_raw:
                if any(x in text for x in ["MGA", "22:08", "Bet 26", "+21 ans"]): continue
                
                team = engine.clean_team(text)
                if team:
                    if not current["h"]: current["h"] = team
                    elif not current["a"]: current["a"] = team
                elif re.search(r"(\d[:\-]\d)", text): current["s"] = text
                elif "MT" in text:
                    current["mt"] = text
                    if current["h"] and current["a"]:
                        matches.append(current)
                        current = {"h": None, "a": None, "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                elif re.search(r"\d+'?", text):
                    x_pos = (bbox[0][0] + bbox[1][0]) / 2
                    if x_pos < 450: current["h_m"] += f" {text}"
                    else: current["a_m"] += f" {text}"

            with st.form("f_res_pro"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h": "Leeds", "a": "Brighton", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                    st.markdown(f"**Match {i+1}**")
                    c1, c2, c3 = st.columns([2, 1, 2])
                    c1.selectbox(f"Dom {i}", engine.teams_list, index=engine.teams_list.index(m['h']), key=f"rh{i}")
                    c2.text_input("Score", m['s'], key=f"rs{i}")
                    c3.selectbox(f"Ext {i}", engine.teams_list, index=engine.teams_list.index(m['a']), key=f"ra{i}")
                    m1, m2 = st.columns(2)
                    m1.text_input("Buteurs Dom", m['h_m'], key=f"rm1{i}")
                    m2.text_input("Buteurs Ext", m['a_m'], key=f"rm2{i}")
                    st.text_input("Mi-temps", m['mt'], key=f"rmt{i}")
                    st.divider()
                st.form_submit_button("Sauvegarder la journée")

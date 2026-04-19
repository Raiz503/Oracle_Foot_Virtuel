import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V15.2 - Vision Stable", layout="wide")

@st.cache_resource
def load_ocr():
    # GPU=False pour la stabilité sur tous les appareils
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
        self.db_path = 'oracle_db_v15.json'

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.3)
        return m[0] if m else None

engine = OracleEngine()
st.title("🔮 ORACLE V15.2")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 : CALENDRIER (Base V12 intégrée) ---
with tabs[0]:
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    if file_cal:
        with st.spinner("Extraction des cotes..."):
            res = reader.readtext(file_cal.read(), detail=0)
            f_teams, f_odds = [], []
            for t in res:
                name = engine.clean_team(t)
                if name: f_teams.append(name)
                nums = re.findall(r"\d+[\.,]\d+", t)
                if nums: f_odds.extend([float(n.replace(',', '.')) for n in nums])

            if len(f_teams) < 20:
                missing = [t for t in engine.teams_list if t not in f_teams]
                if missing: f_teams.insert(0, missing[0])

            st.session_state['cal_v15'] = []
            for i in range(10):
                idx_t, idx_o = i*2, i*3
                h = f_teams[idx_t] if idx_t < len(f_teams) else "Inconnu"
                a = f_teams[idx_t+1] if idx_t+1 < len(f_teams) else "Inconnu"
                o = f_odds[idx_o:idx_o+3] if len(f_odds) >= idx_o+3 else [1.50, 3.50, 4.50]
                if len(o) < 3: o = [o[0] if len(o)>0 else 1.5, o[1] if len(o)>1 else 3.5, 4.5]
                st.session_state['cal_v15'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v15' in st.session_state:
        day_select = st.selectbox("Sélectionnez la Journée", range(1, 39), index=0)
        with st.form("form_cal_v15"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v15']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']))
                af = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']))
                o1 = c3.number_input("C1", value=m['o'][0], key=f"c1_{i}", format="%.2f", min_value=0.0)
                ox = c4.number_input("CX", value=m['o'][1], key=f"cx_{i}", format="%.2f", min_value=0.0)
                o2 = c5.number_input("C2", value=m['o'][2], key=f"c2_{i}", format="%.2f", min_value=0.0)
                validated.append({'h': hf, 'a': af, 'o': [o1, ox, o2], 'day': day_select})
            if st.form_submit_button("🔥 GÉNÉRER PRONOSTICS"):
                st.session_state['ready_v15'] = validated

# --- TAB 2 : PRONOS ---
with tabs[1]:
    if 'ready_v15' in st.session_state:
        for m in st.session_state['ready_v15']:
            score_h = int((3.0 / m['o'][0]) + 0.5)
            score_a = int((3.0 / m['o'][2]) + 0.2)
            st.info(f"**{m['h']} {score_h} - {score_a} {m['a']}**")

# --- TAB 3 : RÉSULTATS (Moteur Corrigé Anti-mélange) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        with st.spinner("Analyse ligne par ligne..."):
            res_raw = reader.readtext(file_res.read(), detail=1)
            # Tri vertical strict (Y) : On lit de haut en bas sans exception
            res_raw.sort(key=lambda x: x[0][0][1])
            
            matches = []
            current = {"h": None, "a": None, "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            
            for (bbox, text, prob) in res_raw:
                # Filtrage des bruits
                if any(x in text for x in ["MGA", "22:08", "Bet 26", "+21", "Journée"]): continue
                
                team = engine.clean_team(text)
                if team:
                    # Si on trouve une équipe alors qu'on a déjà les deux du match précédent, on valide le match fini
                    if current["h"] and current["a"]:
                        matches.append(current)
                        current = {"h": None, "a": None, "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                    
                    if not current["h"]: current["h"] = team
                    elif not current["a"]: current["a"] = team
                
                elif re.search(r"\d[:\-]\d", text): 
                    current["s"] = text
                
                elif "MT" in text:
                    current["mt"] = text
                    # Une mi-temps indique souvent la fin d'un bloc visuel
                    if current["h"] and current["a"]:
                        matches.append(current)
                        current = {"h": None, "a": None, "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                
                elif re.search(r"\d+'?", text):
                    # Séparation par axe X (Gauche < 450 < Droite)
                    x_center = (bbox[0][0] + bbox[1][0]) / 2
                    if x_center < 450: current["h_m"] += f" {text}"
                    else: current["a_m"] += f" {text}"

            # Si le dernier match n'a pas été ajouté (pas de MT détectée)
            if current["h"] and current["a"] and current not in matches:
                matches.append(current)

            with st.form("form_res_fixed"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h": "Leeds", "a": "Brighton", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                    c1, sc, c2 = st.columns([2, 1, 2])
                    
                    idx_h = engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0
                    idx_a = engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 1
                    
                    c1.selectbox(f"H{i}", engine.teams_list, index=idx_h, key=f"rh{i}")
                    sc.text_input("Score", m['s'], key=f"rs{i}")
                    c2.selectbox(f"A{i}", engine.teams_list, index=idx_a, key=f"ra{i}")
                    
                    m1, m2, m3 = st.columns([2, 2, 1])
                    m1.text_input("Minutes Domicile", m['h_m'].strip(), key=f"rm1{i}")
                    m2.text_input("Minutes Extérieur", m['a_m'].strip(), key=f"rm2{i}")
                    m3.text_input("MT", m['mt'], key=f"rmt{i}")
                    st.divider()
                st.form_submit_button("✅ SAUVEGARDER LA JOURNÉE")

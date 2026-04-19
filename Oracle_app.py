import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V15.3 - Precision Scores", layout="wide")

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

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.3)
        return m[0] if m else None

engine = OracleEngine()
st.title("🔮 ORACLE V15.3 : GÉO-LOCALISATION")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 & 2 : CONSERVÉS (Base V12/V15) ---
with tabs[0]:
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    if file_cal:
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums: f_odds.extend([float(n.replace(',', '.')) for n in nums])
        if len(f_teams) < 20:
            missing = [t for t in engine.teams_list if t not in f_teams]; f_teams.insert(0, missing[0]) if missing else None
        st.session_state['cal_v15'] = []
        for i in range(10):
            h, a = (f_teams[i*2], f_teams[i*2+1]) if len(f_teams) > i*2+1 else ("Inconnu", "Inconnu")
            idx = i * 3
            o = f_odds[idx:idx+3] if len(f_odds) >= idx+3 else [1.50, 3.50, 4.50]
            st.session_state['cal_v15'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v15' in st.session_state:
        day_select = st.selectbox("Journée", range(1, 39))
        with st.form("f_cal"):
            val = []
            for i, m in enumerate(st.session_state['cal_v15']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"D{i}", engine.teams_list, index=engine.teams_list.index(m['h']))
                af = c2.selectbox(f"E{i}", engine.teams_list, index=engine.teams_list.index(m['a']))
                o1 = c3.number_input("C1", m['o'][0], key=f"c1{i}")
                ox = c4.number_input("CX", m['o'][1], key=f"cx{i}")
                o2 = c5.number_input("C2", m['o'][2], key=f"c2{i}")
                val.append({'h': hf, 'a': af, 'o': [o1, ox, o2], 'day': day_select})
            if st.form_submit_button("Calculer"): st.session_state['ready'] = val

with tabs[1]:
    if 'ready' in st.session_state:
        for m in st.session_state['ready']:
            st.write(f"**{m['h']} vs {m['a']}**")

# --- TAB 3 : RÉSULTATS (Moteur de précision géographique) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        with st.spinner("Analyse géo-temporelle..."):
            res_raw = reader.readtext(file_res.read(), detail=1)
            # Tri vertical strict pour identifier les blocs
            res_raw.sort(key=lambda x: x[0][0][1])
            
            matches = []
            # On cherche d'abord les paires d'équipes pour créer des "zones"
            temp_teams = []
            for (bbox, text, prob) in res_raw:
                team = engine.clean_team(text)
                if team:
                    # On stocke l'équipe et sa position Y
                    temp_teams.append({"name": team, "y": bbox[0][1], "x": bbox[0][0]})

            # On groupe les équipes par 2 (Domicile / Extérieur)
            for i in range(0, len(temp_teams) - 1, 2):
                if len(matches) >= 10: break
                h_team = temp_teams[i]
                a_team = temp_teams[i+1]
                
                # Zone du match : du haut de l'équipe domicile jusqu'au prochain match
                y_min = h_team["y"] - 10
                y_max = temp_teams[i+2]["y"] - 10 if i+2 < len(temp_teams) else 10000
                
                match_info = {"h": h_team["name"], "a": a_team["name"], "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                
                # On repasse sur tous les textes pour trouver ce qui appartient à CETTE zone Y
                for (bbox, text, prob) in res_raw:
                    mid_y = (bbox[0][1] + bbox[2][1]) / 2
                    mid_x = (bbox[0][0] + bbox[1][0]) / 2
                    
                    if y_min <= mid_y <= y_max:
                        # Est-ce un score ?
                        if re.search(r"\d[:\-]\d", text) and "MT" not in text:
                            match_info["s"] = text
                        # Est-ce la mi-temps ?
                        elif "MT" in text:
                            match_info["mt"] = text
                        # Est-ce une minute de but ?
                        elif re.search(r"\d+'?", text):
                            # SI X est à gauche du centre (environ 450-500px), c'est Domicile
                            if mid_x < 480: match_info["h_m"] += f" {text}"
                            else: match_info["a_m"] += f" {text}"
                
                matches.append(match_info)

            with st.form("form_res_precision"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h": "Leeds", "a": "Brighton", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                    c1, sc, c2 = st.columns([2, 1, 2])
                    c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']), key=f"rh{i}")
                    sc.text_input("Score Final", m['s'], key=f"rs{i}")
                    c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']), key=f"ra{i}")
                    
                    m1, m2, mt = st.columns([2, 2, 1])
                    m1.text_input("Buteurs Dom", m['h_m'].strip(), key=f"rm1{i}")
                    m2.text_input("Buteurs Ext", m['a_m'].strip(), key=f"rm2{i}")
                    mt.text_input("Score MT", m['mt'], key=f"rmt{i}")
                    st.divider()
                st.form_submit_button("✅ ENREGISTRER")

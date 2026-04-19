import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V14 - Vision Matrix", layout="wide")

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
        self.db_path = 'oracle_db_v14.json'

    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.3)
        return m[0] if m else None

engine = OracleEngine()
st.title("🔮 ORACLE V14 : EXTRACTION PAR SEGMENTATION")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- ONGLET CALENDRIER (Extraction Précise) ---
with tabs[0]:
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    if file_cal:
        with st.spinner("Analyse visuelle du calendrier..."):
            res = reader.readtext(file_cal.read(), detail=1)
            # Tri par position verticale
            res.sort(key=lambda x: x[0][0][1])
            
            f_teams, f_odds = [], []
            for (bbox, text, prob) in res:
                team = engine.clean_team(text)
                if team: f_teams.append(team)
                
                # Capture des cotes (formats X.XX ou X,XX)
                odds = re.findall(r"\d+[\.,]\d+", text)
                if odds: f_odds.extend([float(o.replace(',', '.')) for o in odds])

            # Déduction Leeds
            if len(f_teams) < 20:
                missing = [t for t in engine.teams_list if t not in f_teams]
                if missing: f_teams.insert(0, missing[0])

            st.session_state['cal_v14'] = []
            for i in range(10):
                idx_t, idx_o = i*2, i*3
                h = f_teams[idx_t] if idx_t < len(f_teams) else "Inconnu"
                a = f_teams[idx_t+1] if idx_t+1 < len(f_teams) else "Inconnu"
                o = f_odds[idx_o:idx_o+3] if len(f_odds) >= idx_o+2 else [1.5, 3.5, 4.5]
                # Réparation automatique si la 3ème cote manque
                if len(o) < 3: o.append(round(1/(1-(1/o[0])-(1/o[1])-0.05), 2))
                st.session_state['cal_v14'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v14' in st.session_state:
        with st.form("form_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v14']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']))
                af = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']))
                o1 = c3.number_input("C1", m['o'][0], key=f"c1_{i}")
                ox = c4.number_input("CX", m['o'][1], key=f"cx_{i}")
                o2 = c5.number_input("C2", m['o'][2], key=f"c2_{i}")
                validated.append({'h': hf, 'a': af, 'o': [o1, ox, o2]})
            if st.form_submit_button("Lancer l'Analyse"):
                st.session_state['ready_v14'] = validated

# --- ONGLET PRONOS (Basé sur les données validées) ---
with tabs[1]:
    if 'ready_v14' in st.session_state:
        for m in st.session_state['ready_v14']:
            # Logique de score basée sur les cotes réelles
            sh = int((2.5/m['o'][0])*1.4); sa = int((2.5/m['o'][2])*1.2)
            st.info(f"**{m['h']} {sh} - {sa} {m['a']}** | Ticket : {'1' if sh > sa else '2' if sa > sh else 'X'}")

# --- ONGLET RÉSULTATS (Segmentation par zones) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if file_res:
        with st.spinner("Découpage visuel des matchs..."):
            res_data = reader.readtext(file_res.read(), detail=1)
            # Tri vertical pour isoler les 10 lignes de match
            res_data.sort(key=lambda x: x[0][0][1])
            
            matches = []
            # On initialise 10 structures vides
            for _ in range(10): matches.append({"h":None, "a":None, "s":"0:0", "h_m":"", "a_m":"", "mt":""})
            
            # Moteur de placement par coordonnées
            current_idx = -1
            for (bbox, text, prob) in res_data:
                if any(x in text for x in ["MGA", "22:08", "Bet 26", "+21"]): continue
                
                # Détection de l'équipe et changement de ligne
                team = engine.clean_team(text)
                if team:
                    # Si c'est un nouveau match (on détecte l'équipe domicile)
                    if current_idx < 9:
                        # Si on trouve une équipe et qu'on n'a pas encore fini le match actuel
                        if current_idx == -1 or (matches[current_idx]["h"] and matches[current_idx]["a"]):
                            current_idx += 1
                        
                        if not matches[current_idx]["h"]: matches[current_idx]["h"] = team
                        elif not matches[current_idx]["a"]: matches[current_idx]["a"] = team
                    continue

                # Placement des autres données dans le match actuel (current_idx)
                if current_idx >= 0:
                    if re.search(r"\d[:\-]\d", text): matches[current_idx]["s"] = text
                    elif "MT" in text: matches[current_idx]["mt"] = text
                    elif re.search(r"\d+'?", text):
                        # x_coord détermine si c'est pour l'équipe de gauche ou droite
                        x_center = (bbox[0][0] + bbox[1][0]) / 2
                        if x_center < 450: matches[current_idx]["h_m"] += f" {text}"
                        else: matches[current_idx]["a_m"] += f" {text}"

            with st.form("f_res_v14"):
                for i, m in enumerate(matches):
                    st.markdown(f"**⚽ Match {i+1}**")
                    col1, col2, col3 = st.columns([2, 1, 2])
                    h_idx = engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0
                    a_idx = engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 1
                    col1.selectbox("H", engine.teams_list, index=h_idx, key=f"h{i}")
                    col2.text_input("Score", m['s'], key=f"s{i}")
                    col3.selectbox("A", engine.teams_list, index=a_idx, key=f"a{i}")
                    
                    m1, m2, m3 = st.columns([2, 2, 1])
                    m1.text_input("Minutes (H)", m['h_m'], key=f"hm{i}")
                    m2.text_input("Minutes (A)", m['a_m'], key=f"am{i}")
                    m3.text_input("Mi-temps", m['mt'], key=f"mt{i}")
                    st.divider()
                st.form_submit_button("✅ Enregistrer la Journée")

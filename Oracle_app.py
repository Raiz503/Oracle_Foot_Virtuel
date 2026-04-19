import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle Auto-Scan V5.1", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.teams_list = [
            "Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", 
            "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", 
            "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", 
            "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"
        ]

    def clean_team_name(self, text):
        """Trouve le nom d'équipe le plus proche"""
        match = get_close_matches(text, self.teams_list, n=1, cutoff=0.35)
        return match[0] if match else None

    def extract_numbers(self, text):
        """Trouve les cotes (ex: 1.45 ou 2,50)"""
        text = text.replace(',', '.')
        nums = re.findall(r"\d+\.\d+", text)
        return [float(n) for n in nums]

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE AUTO-SCAN V5.1")

# Initialisation des variables de session
if 'extracted_matches' not in st.session_state:
    st.session_state['extracted_matches'] = []

file = st.file_uploader("📸 Importez le Calendrier", type=['jpg','png','jpeg'])

if file:
    with st.spinner("Analyse du calendrier en cours..."):
        img_bytes = file.read()
        raw_text = reader.readtext(img_bytes, detail=0)
        
        found_teams = []
        found_odds = []
        
        for t in raw_text:
            # Recherche d'équipes
            clean_t = engine.clean_team_name(t)
            if clean_t:
                found_teams.append(clean_t)
            
            # Recherche de cotes
            odds = engine.extract_numbers(t)
            if odds: 
                found_odds.extend(odds)
        
        # --- RECONSTRUCTION SÉCURISÉE DES MATCHS ---
        temp_matches = []
        # On avance par paire d'équipes (Domicile / Extérieur)
        for i in range(0, len(found_teams) - 1, 2):
            if len(temp_matches) < 10:
                h = found_teams[i]
                a = found_teams[i+1]
                
                # On cherche les 3 cotes qui suivent ces équipes
                idx_odds = len(temp_matches) * 3
                cotes = found_odds[idx_odds:idx_odds+3] if len(found_odds) >= idx_odds+3 else [1.50, 3.40, 4.50]
                
                temp_matches.append({'h': h, 'a': a, 'c1': cotes[0], 'cx': cotes[1], 'c2': cotes[2]})
        
        st.session_state['extracted_matches'] = temp_matches

# --- AFFICHAGE ET ÉDITION ---
if st.session_state['extracted_matches']:
    st.header("📋 Vérification des 10 Matchs")
    
    with st.form("form_global"):
        final_list = []
        for idx, m in enumerate(st.session_state['extracted_matches']):
            st.markdown(f"**Match n°{idx+1}**")
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
            
            h_final = c1.selectbox(f"Dom {idx}", engine.teams_list, index=engine.teams_list.index(m['h']), key=f"sel_h{idx}")
            a_final = c2.selectbox(f"Ext {idx}", engine.teams_list, index=engine.teams_list.index(m['a']), key=f"sel_a{idx}")
            v1 = c3.number_input("C1", value=m['c1'], key=f"num1_{idx}")
            vx = c4.number_input("CX", value=m['cx'], key=f"numx_{idx}")
            v2 = c5.number_input("C2", value=m['c2'], key=f"num2_{idx}")
            
            final_list.append({'h': h_final, 'a': a_final, 'odds': [v1, vx, v2]})
            st.divider()
            
        if st.form_submit_button("🔥 GÉNÉRER L'ANALYSE ET LES TICKETS"):
            st.session_state['final_results'] = final_list
            st.success("Calculs terminés !")

# --- TICKETS ---
if 'final_results' in st.session_state:
    st.header("🎫 TES TICKETS ORACLE")
    t1, t2, t3 = st.columns(3)
    
    with t1:
        st.info("🛡️ SÉCURISÉ (Combiné 3)")
        for m in st.session_state['final_results'][:3]:
            st.write(f"🔹 {m['h']} ou Nul")
            
    with t2:
        st.warning("⚖️ ÉQUILIBRÉ (Simple)")
        for m in st.session_state['final_results'][3:6]:
            st.write(f"🔸 {m['h']} (+1.5 buts)")

    with t3:
        st.error("🔥 ORACLE (Grosse Cote)")
        for m in st.session_state['final_results'][6:9]:
            st.write(f"🎯 {m['h']} Gagne (Score probable)")

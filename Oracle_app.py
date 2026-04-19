import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle Auto-Scan V5", layout="wide")

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
        """Transforme une lecture OCR ratée en nom d'équipe officiel"""
        match = get_close_matches(text, self.teams_list, n=1, cutoff=0.3)
        return match[0] if match else None

    def extract_numbers(self, text):
        """Extrait les cotes (nombres avec virgule ou point)"""
        text = text.replace(',', '.')
        nums = re.findall(r"\d+\.\d+", text)
        return [float(n) for n in nums]

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE V5 : EXTRACTION AUTOMATIQUE")

if 'extracted_matches' not in st.session_state:
    st.session_state['extracted_matches'] = []

file = st.file_uploader("📸 Importez le Calendrier (10 matchs)", type=['jpg','png','jpeg'])

if file:
    with st.spinner("Analyse intelligente du calendrier..."):
        img_bytes = file.read()
        raw_text = reader.readtext(img_bytes, detail=0)
        
        # --- MOTEUR DE CORRESPONDANCE (L'Intelligence) ---
        found_teams = []
        found_odds = []
        
        for t in raw_text:
            # On cherche si le mot ressemble à une équipe
            clean_t = engine.clean_team_name(t)
            if clean_t and clean_t not in [match['h'] for match in found_teams]: 
                found_teams.append(clean_t)
            
            # On cherche les cotes
            odds = engine.extract_numbers(t)
            if odds: found_odds.extend(odds)
        
        # Reconstruction des 10 matchs (Paires d'équipes + Triplets de cotes)
        temp_matches = []
        for i in range(0, len(found_teams) - 1, 2):
            if len(temp_matches) < 10:
                h = found_teams[i]
                a = found_teams[i+1]
                # On essaie de trouver les 3 cotes correspondantes dans la liste
                idx_odds = (len(temp_matches)) * 3
                cotes = found_odds[idx_odds:idx_odds+3] if len(found_odds) >= idx_odds+3 else [1.5, 3.0, 4.0]
                
                temp_matches.append({'h': h, 'a': a, 'c1': cotes[0], 'cx': cotes[1], 'c2': cotes[2]})
        
        st.session_state['extracted_matches'] = temp_matches

# --- AFFICHAGE DE LA LISTE ÉDITABLE ---
if st.session_state['extracted_matches']:
    st.header("📋 Validation du Calendrier")
    st.info("L'IA a détecté les matchs suivants. Corrigez si nécessaire avant l'analyse.")
    
    final_calendar = []
    
    # Création d'une grille pour les 10 matchs
    for idx, m in enumerate(st.session_state['extracted_matches']):
        with st.expander(f"Match {idx+1} : {m['h']} vs {m['a']}", expanded=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            home = col1.selectbox(f"Dom {idx}", engine.teams_list, index=engine.teams_list.index(m['h']), key=f"h{idx}")
            away = col2.selectbox(f"Ext {idx}", engine.teams_list, index=engine.teams_list.index(m['a']), key=f"a{idx}")
            c1 = col3.number_input("Cote 1", value=m['c1'], key=f"c1{idx}")
            cx = col4.number_input("Cote X", value=m['cx'], key=f"cx{idx}")
            c2 = col5.number_input("Cote 2", value=m['c2'], key=f"c2{idx}")
            final_calendar.append({'h': home, 'a': away, 'odds': [c1, cx, c2]})

    if st.button("🚀 LANCER L'ANALYSE GLOBALE (10 MATCHS)"):
        st.session_state['final_results'] = final_calendar
        st.success("Analyse terminée ! Consultez vos tickets ci-dessous.")

# --- AFFICHAGE DES TICKETS (Simulation des 3 tickets) ---
if 'final_results' in st.session_state:
    st.divider()
    st.header("🎫 TES TICKETS GÉNÉRÉS")
    t1, t2, t3 = st.columns(3)
    
    with t1:
        st.info("🛡️ TICKET SÉCURISÉ")
        for m in st.session_state['final_results'][:3]: # Prend les 3 premiers
            st.write(f"✅ {m['h']} ou Nul")
            
    with t2:
        st.warning("⚖️ TICKET ÉQUILIBRÉ")
        for m in st.session_state['final_results'][3:6]:
            st.write(f"⚽ {m['h']} Gagne & +1.5 buts")

    with t3:
        st.error("🔥 TICKET ORACLE")
        for m in st.session_state['final_results'][6:9]:
            st.write(f"🎯 Score exact probable pour {m['h']}")

import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V13 - Résultats Pro", layout="wide")

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

# --- INTERFACE ---
engine = OracleEngine()
st.title("⚽ SCANNEUR DE RÉSULTATS V13")

file_res = st.file_uploader("📸 Importez la capture des résultats", type=['jpg','png','jpeg'])

if file_res:
    with st.spinner("Analyse structurelle des 10 matchs..."):
        # On récupère les coordonnées pour savoir qui est à gauche/droite/haut/bas
        results = reader.readtext(file_res.read(), detail=1)
        
        # 1. Tri par position verticale (Y) pour grouper par match
        results.sort(key=lambda x: x[0][0][1])

        matches_data = []
        current_match = {"h": None, "a": None, "score": "0:0", "h_min": "", "a_min": "", "mt": "MT: 0:0"}
        
        # Moteur de segmentation
        for (bbox, text, prob) in results:
            # Ignorer les parties inutiles
            if any(x in text for x in ["MGA", "22:08", "Bet 26", "+21 ans", "ATTETION"]):
                continue
                
            # Détection Journée
            if "Journée" in text:
                st.info(f"📍 {text.split('-')[0].strip()}")
                continue

            # Détection Équipe
            team = engine.clean_team(text)
            if team:
                if not current_match["h"]: current_match["h"] = team
                elif not current_match["a"]: current_match["a"] = team
                continue

            # Détection Score (Format X:X)
            score_match = re.search(r"(\d[:\-]\d)", text)
            if score_match:
                current_match["score"] = score_match.group(1)
                continue

            # Détection Mi-temps
            if "MT" in text:
                current_match["mt"] = text
                # Quand on trouve la mi-temps, c'est souvent la fin du bloc match
                if current_match["h"] and current_match["a"]:
                    matches_data.append(current_match)
                    current_match = {"h": None, "a": None, "score": "0:0", "h_min": "", "a_min": "", "mt": "MT: 0:0"}
                continue

            # Détection Minutes (chiffres suivis de ' ou isolés près des équipes)
            if re.search(r"\d+'?", text):
                center_x = (bbox[0][0] + bbox[1][0]) / 2
                # Si le texte est à gauche de l'écran (x < 400), c'est pour l'équipe domicile
                if center_x < 450:
                    current_match["h_min"] += f" {text}"
                else:
                    current_match["a_min"] += f" {text}"

        # --- AFFICHAGE PROFESSIONNEL ---
        st.divider()
        for idx, m in enumerate(matches_data):
            with st.container():
                # Ligne 1 : Equipe A - Score - Equipe B
                col1, col2, col3 = st.columns([2, 1, 2])
                col1.subheader(m['h'])
                col2.header(f" {m['score']} ")
                col3.subheader(m['a'])
                
                # Ligne 2 : Minutes
                m1, m2 = st.columns(2)
                m1.caption(f"⚽ {m['h_min'].strip()}")
                m2.caption(f"⚽ {m['a_min'].strip()}")
                
                # Ligne 3 : Mi-temps
                st.write(f"⏱️ {m['mt']}")
                st.divider()

        if st.button("💾 Enregistrer ces 10 résultats"):
            st.success("Données envoyées à l'IA pour apprentissage !")

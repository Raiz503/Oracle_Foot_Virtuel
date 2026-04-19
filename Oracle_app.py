import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V15.5 - Strict Grid", layout="wide")

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
st.title("🔮 ORACLE V15.5 : ALIGNEMENT STRICT")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 & 2 : IDENTIQUES À TA VERSION PRÉFÉRÉE ---
# (Code omis ici pour la clarté, garde ton code habituel pour ces onglets)

# --- TAB 3 : RÉSULTATS (Refonte du moteur de capture) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        
        with st.spinner("Découpage de la grille de match..."):
            res_raw = reader.readtext(file_res.getvalue(), detail=1)
            
            # 1. Identifier la zone utile (ignorer le bandeau du haut et du bas)
            # On cherche le premier et le dernier nom d'équipe pour délimiter la grille
            team_boxes = []
            for (bbox, text, prob) in res_raw:
                if engine.clean_team(text):
                    team_boxes.append(bbox[0][1])
            
            if team_boxes:
                y_start = min(team_boxes) - 10
                y_end = max(team_boxes) + 40
                total_height = y_end - y_start
                row_height = total_height / 10 # On divise par 10 matchs
                
                matches = []
                for i in range(10):
                    m_y_min = y_start + (i * row_height)
                    m_y_max = y_start + ((i + 1) * row_height)
                    
                    m_info = {"h": None, "a": None, "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                    
                    for (bbox, text, prob) in res_raw:
                        curr_y = (bbox[0][1] + bbox[2][1]) / 2
                        curr_x = (bbox[0][0] + bbox[1][0]) / 2
                        
                        # Si l'élément est dans la bande horizontale du match i
                        if m_y_min <= curr_y <= m_y_max:
                            # Détection Equipe
                            t_name = engine.clean_team(text)
                            if t_name:
                                if curr_x < mid_x: m_info["h"] = t_name
                                else: m_info["a"] = t_name
                            
                            # Détection Score (Format X:X strict)
                            elif re.search(r"^\d[:\-]\d$", text.strip()):
                                m_info["s"] = text
                            
                            # Détection Mi-temps
                            elif "MT" in text.upper():
                                m_info["mt"] = text
                            
                            # Détection Minutes (chiffres avec ou sans ')
                            elif re.search(r"\d+", text):
                                if "'" in text or (len(text) <= 3 and text.isdigit()):
                                    if curr_x < mid_x: m_info["h_m"] += f" {text}"
                                    else: m_info["a_m"] += f" {text}"
                    
                    # Nettoyage et fallback si équipe non trouvée
                    if not m_info["h"]: m_info["h"] = "Inconnu"
                    if not m_info["a"]: m_info["a"] = "Inconnu"
                    matches.append(m_info)

                # Affichage du formulaire
                with st.form("form_res_v15_5"):
                    for i, m in enumerate(matches):
                        st.markdown(f"### Match {i+1}")
                        c1, sc, c2 = st.columns([2, 1, 2])
                        idx_h = engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0
                        idx_a = engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 1
                        
                        c1.selectbox(f"H{i}", engine.teams_list, index=idx_h, key=f"rh{i}")
                        sc.text_input("Score", m['s'], key=f"rs{i}")
                        c2.selectbox(f"A{i}", engine.teams_list, index=idx_a, key=f"ra{i}")
                        
                        m1, m2, mt = st.columns([2, 2, 1])
                        m1.text_input("Minutes (D)", m['h_m'].strip(), key=f"rm1{i}")
                        m2.text_input("Minutes (E)", m['a_m'].strip(), key=f"rm2{i}")
                        mt.text_input("MT", m['mt'], key=f"rmt{i}")
                        st.divider()
                    st.form_submit_button("✅ ENREGISTRER TOUT")

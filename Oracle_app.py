import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V16.0 - Anchor Precision", layout="wide")

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
st.title("🔮 ORACLE V16.0 : FIX A. VILLA")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 : CALENDRIER (Code stable conservé) ---
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
        st.session_state['cal_v16'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.5, 3.5, 4.5]
            st.session_state['cal_v16'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v16' in st.session_state:
        with st.form("f_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v16']):
                c1, c2 = st.columns(2)
                hf = c1.selectbox(f"H{i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = c2.selectbox(f"A{i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                validated.append({'h': hf, 'a': af, 'o': m['o']})
            if st.form_submit_button("Calculer"): st.session_state['ready_v16'] = validated

# --- TAB 3 : RÉSULTATS (Refonte du calage vertical) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        
        with st.spinner("Calibrage sur A. Villa et les 10 matchs..."):
            res_raw = reader.readtext(file_res.getvalue(), detail=1)
            res_raw.sort(key=lambda x: x[0][0][1]) # Tri par Y (Haut -> Bas)
            
            # 1. Trouver le point de départ réel (le premier match de la liste)
            all_detected_teams = []
            for (bbox, text, prob) in res_raw:
                team = engine.clean_team(text)
                if team:
                    all_detected_teams.append({"name": team, "y": bbox[0][1], "x": (bbox[0][0]+bbox[1][0])/2})
            
            # On ne garde que les équipes situées dans la zone centrale (entre 15% et 90% de la hauteur)
            # pour ignorer le bandeau de pub tout en haut.
            valid_teams = [t for t in all_detected_teams if h_img*0.12 < t["y"] < h_img*0.95]
            
            # 2. Grouper par match
            match_anchors = []
            for t in valid_teams:
                if t["x"] < mid_x: # C'est une équipe Domicile
                    if not match_anchors or abs(t["y"] - match_anchors[-1]["y"]) > 45:
                        match_anchors.append(t)

            matches = []
            for i, anchor in enumerate(match_anchors):
                if len(matches) >= 10: break
                
                y_start = anchor["y"] - 15
                y_end = match_anchors[i+1]["y"] - 15 if i+1 < len(match_anchors) else h_img*0.98
                
                m_info = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                
                for (bbox, text, prob) in res_raw:
                    curr_y = (bbox[0][1] + bbox[2][1]) / 2
                    curr_x = (bbox[0][0] + bbox[1][0]) / 2
                    
                    if y_start <= curr_y <= y_end:
                        t_name = engine.clean_team(text)
                        # Equipe Away
                        if t_name and curr_x > mid_x and t_name != m_info["h"]:
                            m_info["a"] = t_name
                        # Score Final (Strict format X:X)
                        elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper():
                            m_info["s"] = text
                        # MT
                        elif "MT" in text.upper(): m_info["mt"] = text
                        # Minutes
                        elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                            if curr_x < mid_x: m_info["h_m"] += f" {text}"
                            else: m_info["a_m"] += f" {text}"
                
                if m_info["a"] != "Inconnu": # On ne valide le match que s'il y a deux équipes
                    matches.append(m_info)

            # AFFICHAGE
            with st.form("form_v16"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h":"","a":"","s":"","h_m":"","a_m":"","mt":""}
                    st.write(f"### Match {i+1} : {m['h']} vs {m['a']}")
                    c1, c2, c3 = st.columns([1,1,1])
                    sc = c1.text_input("Score", m['s'], key=f"s{i}")
                    mt = c2.text_input("MT", m['mt'], key=f"mt{i}")
                    
                    m1, m2 = st.columns(2)
                    m1.text_input("Buts Dom", m['h_m'].strip(), key=f"bd{i}")
                    m2.text_input("Buts Ext", m['a_m'].strip(), key=f"be{i}")
                    st.divider()
                st.form_submit_button("✅ SAUVEGARDER")

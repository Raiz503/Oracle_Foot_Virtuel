import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V15.8 - Repères Précis", layout="wide")

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
st.title("🔮 ORACLE V15.8")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 : CALENDRIER ---
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
        st.session_state['cal_v15'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.5, 3.5, 4.5]
            st.session_state['cal_v15'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v15' in st.session_state:
        day_sel = st.selectbox("Journée", range(1, 39))
        with st.form("f_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v15']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"D{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = c2.selectbox(f"E{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 1)
                o1 = c3.number_input("C1", m['o'][0], key=f"c1{i}")
                ox = c4.number_input("CX", m['o'][1], key=f"cx{i}")
                o2 = c5.number_input("C2", m['o'][2], key=f"c2{i}")
                validated.append({'h': hf, 'a': af, 'o': [o1, ox, o2], 'day': day_sel})
            if st.form_submit_button("VALIDER CALENDRIER"):
                st.session_state['ready_v15'] = validated

# --- TAB 2 : PRONOS ---
with tabs[1]:
    if 'ready_v15' in st.session_state:
        for m in st.session_state['ready_v15']:
            st.info(f"**{m['h']} vs {m['a']}** (Journée {m['day']})")

# --- TAB 3 : RÉSULTATS (Correction Repères Premier/Dernier) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        
        with st.spinner("Analyse des repères..."):
            res_raw = reader.readtext(file_res.getvalue(), detail=1)
            res_raw.sort(key=lambda x: x[0][0][1])
            
            # 1. On ignore les 10% du haut et du bas de l'image (zones de menus/titres)
            # Cela évite de détecter des équipes qui ne font pas partie de la liste
            limit_top = h_img * 0.10
            limit_bottom = h_img * 0.92
            
            match_anchors = []
            for (bbox, text, prob) in res_raw:
                y_pos = bbox[0][1]
                x_pos = (bbox[0][0] + bbox[1][0]) / 2
                
                if limit_top < y_pos < limit_bottom:
                    team = engine.clean_team(text)
                    if team and x_pos < mid_x: # Equipe Domicile
                        # Si l'ancre est trop proche de la précédente (doublon), on l'ignore
                        if not match_anchors or abs(y_pos - match_anchors[-1]["y"]) > 40:
                            match_anchors.append({"name": team, "y": y_pos})

            matches = []
            for i, anchor in enumerate(match_anchors):
                if len(matches) >= 10: break
                
                y_start = anchor["y"] - 15
                y_end = match_anchors[i+1]["y"] - 15 if i+1 < len(match_anchors) else limit_bottom
                
                m_info = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                
                for (bbox, text, prob) in res_raw:
                    curr_y = (bbox[0][1] + bbox[2][1]) / 2
                    curr_x = (bbox[0][0] + bbox[1][0]) / 2
                    
                    if y_start <= curr_y <= y_end:
                        t_name = engine.clean_team(text)
                        if t_name and curr_x > mid_x: m_info["a"] = t_name
                        elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper():
                            m_info["s"] = text
                        elif "MT" in text.upper(): m_info["mt"] = text
                        elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                            if curr_x < mid_x: m_info["h_m"] += f" {text}"
                            else: m_info["a_m"] += f" {text}"
                matches.append(m_info)

            with st.form("form_res_v15_8"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h":"...","a":"...","s":"0:0","h_m":"","a_m":"","mt":""}
                    c1, sc, c2 = st.columns([2, 1, 2])
                    idx_h = engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0
                    idx_a = engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 1
                    c1.selectbox(f"H{i}", engine.teams_list, index=idx_h, key=f"rh{i}")
                    sc.text_input("Score", m['s'], key=f"rs{i}")
                    c2.selectbox(f"A{i}", engine.teams_list, index=idx_a, key=f"ra{i}")
                    
                    m1, m2, mt = st.columns([2, 2, 1])
                    m1.text_input("Buteurs D", m['h_m'].strip(), key=f"rm1{i}")
                    m2.text_input("Buteurs E", m['a_m'].strip(), key=f"rm2{i}")
                    mt.text_input("MT", m['mt'], key=f"rmt{i}")
                    st.divider()
                st.form_submit_button("💾 ENREGISTRER RÉSULTATS")

import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V15.7 - Full Vision", layout="wide")

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
st.title("🔮 ORACLE V15.7 : FINAL FIX")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 : CALENDRIER (Sécurisé) ---
with tabs[0]:
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    if file_cal:
        with st.spinner("Extraction Calendrier..."):
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
                o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.50, 3.50, 4.50]
                st.session_state['cal_v15'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v15' in st.session_state:
        day_sel = st.selectbox("Journée", range(1, 39), index=0)
        with st.form("form_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v15']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                o1 = c3.number_input("C1", value=m['o'][0], key=f"c1_{i}")
                ox = c4.number_input("CX", value=m['o'][1], key=f"cx_{i}")
                o2 = c5.number_input("C2", value=m['o'][2], key=f"c2_{i}")
                validated.append({'h': hf, 'a': af, 'o': [o1, ox, o2], 'day': day_sel})
            if st.form_submit_button("🔥 GÉNÉRER PRONOSTICS"):
                st.session_state['ready_v15'] = validated

# --- TAB 2 : PRONOS ---
with tabs[1]:
    if 'ready_v15' in st.session_state:
        for m in st.session_state['ready_v15']:
            s_h = int((3.0 / m['o'][0]) + 0.5)
            s_a = int((3.0 / m['o'][2]) + 0.2)
            st.info(f"**{m['h']} {s_h} - {s_a} {m['a']}**")

# --- TAB 3 : RÉSULTATS (Correction du 10ème match) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res)
        mid_x = img.size[0] / 2
        
        with st.spinner("Analyse du 1er au 10ème match..."):
            res_raw = reader.readtext(file_res.getvalue(), detail=1)
            res_raw.sort(key=lambda x: x[0][0][1])
            
            # Identification des ancres (équipes à gauche)
            match_anchors = []
            for (bbox, text, prob) in res_raw:
                team = engine.clean_team(text)
                if team and (bbox[0][0] + bbox[1][0])/2 < mid_x:
                    # On évite les doublons d'ancres trop proches
                    if not match_anchors or abs(bbox[0][1] - match_anchors[-1]["y"]) > 30:
                        match_anchors.append({"name": team, "y": bbox[0][1]})

            matches = []
            for i, anchor in enumerate(match_anchors):
                if len(matches) >= 10: break
                
                y_top = anchor["y"] - 20
                # CRITIQUE : Si c'est le dernier match, on prend TOUT jusqu'à la fin de l'image (9999)
                y_bottom = match_anchors[i+1]["y"] - 10 if i+1 < len(match_anchors) else 9999
                
                m_info = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                
                for (bbox, text, prob) in res_raw:
                    curr_y = (bbox[0][1] + bbox[2][1]) / 2
                    curr_x = (bbox[0][0] + bbox[1][0]) / 2
                    
                    if y_top <= curr_y <= y_bottom:
                        t_name = engine.clean_team(text)
                        # Equipe Extérieure
                        if t_name and curr_x > mid_x:
                            m_info["a"] = t_name
                        # Score Final (ex: 2:1)
                        elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper():
                            m_info["s"] = text
                        # Mi-temps
                        elif "MT" in text.upper():
                            m_info["mt"] = text
                        # Minutes (on exclut les scores)
                        elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                            if curr_x < mid_x: m_info["h_m"] += f" {text}"
                            else: m_info["a_m"] += f" {text}"
                
                matches.append(m_info)

            with st.form("form_res_v15_7"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h":"Inconnu","a":"Inconnu","s":"0:0","h_m":"","a_m":"","mt":""}
                    c1, sc, c2 = st.columns([2, 1, 2])
                    idx_h = engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0
                    idx_a = engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 1
                    
                    c1.selectbox(f"H{i}", engine.teams_list, index=idx_h, key=f"rh{i}")
                    sc.text_input("Score Final", m['s'], key=f"rs{i}")
                    c2.selectbox(f"A{i}", engine.teams_list, index=idx_a, key=f"ra{i}")
                    
                    m1, m2, mt = st.columns([2, 2, 1])
                    m1.text_input("Buts Dom", m['h_m'].strip(), key=f"rm1{i}")
                    m2.text_input("Buts Ext", m['a_m'].strip(), key=f"rm2{i}")
                    mt.text_input("Score MT", m['mt'], key=f"rmt{i}")
                    st.divider()
                st.form_submit_button("✅ TOUT SAUVEGARDER")

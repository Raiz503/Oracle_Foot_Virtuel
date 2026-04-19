import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V17.4 - Final Fix", layout="wide")

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

if 'saison_nom' not in st.session_state: st.session_state['saison_nom'] = "Saison 2026"

st.title(f"🔮 ORACLE V17.4")

tabs = st.tabs(["🌟 SAISON", "📅 CALENDRIER", "🎯 PRONOS & TICKETS", "⚽ RÉSULTATS"])

# --- TAB 0 : SAISON ---
with tabs[0]:
    st.session_state['saison_nom'] = st.text_input("Nom de la Saison actuelle", st.session_state['saison_nom'])
    if st.button("Nouvelle Saison (Reset)"):
        for key in ['cal_v16', 'ready_v16']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

# --- TAB 1 : CALENDRIER (Correction Cotes Match 10) ---
with tabs[1]:
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    if file_cal:
        # Lecture complète pour ne rien rater en bas d'image
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            
            # Recherche de nombres type X.XX ou X,XX
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums:
                for n in nums:
                    val = float(n.replace(',', '.'))
                    # Filtre pour éviter de prendre des scores comme cotes
                    if 1.01 <= val <= 50.0:
                        f_odds.append(val)
        
        st.session_state['cal_v16'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            # On pioche les cotes 3 par 3
            o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.50, 3.40, 4.20]
            st.session_state['cal_v16'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v16' in st.session_state:
        with st.form("f_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v16']):
                col1, col2, c1, cx, c2 = st.columns([2, 2, 1, 1, 1])
                hf = col1.selectbox(f"H{i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = col2.selectbox(f"A{i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                o1 = c1.number_input("C1", value=m['o'][0], key=f"c1_{i}", format="%.2f")
                ox = cx.number_input("CX", value=m['o'][1], key=f"cx_{i}", format="%.2f")
                o2 = c2.number_input("C2", value=m['o'][2], key=f"c2_{i}", format="%.2f")
                validated.append({'h': hf, 'a': af, 'o': [o1, ox, o2]})
            if st.form_submit_button("🔥 GÉNÉRER ANALYSE"):
                st.session_state['ready_v16'] = validated

# --- TAB 2 : PRONOS & TICKETS ---
with tabs[2]:
    if 'ready_v16' in st.session_state:
        t_safe, t_risque, t_fun = [], [], []
        for m in st.session_state['ready_v16']:
            # Calcul Score Probable
            s_h = int((3.0 / m['o'][0]) + 0.4) if m['o'][0] > 0 else 0
            s_a = int((3.0 / m['o'][2]) + 0.1) if m['o'][2] > 0 else 0
            st.info(f"⚽ **{m['h']} {s_h} - {s_a} {m['a']}** (Cotes: {m['o'][0]} | {m['o'][1]} | {m['o'][2]})")
            
            # Logique Tickets
            if m['o'][0] < 1.6 or m['o'][2] < 1.6: t_safe.append(f"{m['h']} / {m['a']}")
            if 1.7 <= m['o'][0] <= 2.6: t_risque.append(f"Gagne: {m['h']}")
            if m['o'][1] > 3.6: t_fun.append(f"Nul: {m['h']}-{m['a']}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.success("🟢 **TICKET SAFE**\n\n" + "\n".join(t_safe[:4]))
        with c2: st.warning("🟡 **TICKET RISQUE**\n\n" + "\n".join(t_risque[:3]))
        with c3: st.error("🔴 **TICKET FUN**\n\n" + "\n".join(t_fun[:3]))

# --- TAB 3 : RÉSULTATS (STRICT V16.2 - AUCUN CHANGEMENT) ---
with tabs[3]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        res_raw = reader.readtext(file_res.getvalue(), detail=1)
        res_raw.sort(key=lambda x: x[0][0][1])
        
        valid_teams = []
        for (bbox, text, prob) in res_raw:
            team = engine.clean_team(text)
            if team: valid_teams.append({"name": team, "y": bbox[0][1], "x": (bbox[0][0]+bbox[1][0])/2})
        
        valid_teams = [t for t in valid_teams if h_img*0.12 < t["y"] < h_img*0.95]
        
        match_anchors = []
        for t in valid_teams:
            if t["x"] < mid_x:
                if not match_anchors or abs(t["y"] - match_anchors[-1]["y"]) > 45:
                    match_anchors.append(t)

        matches = []
        for i, anchor in enumerate(match_anchors):
            if len(matches) >= 10: break
            y_start, y_end = anchor["y"] - 15, (match_anchors[i+1]["y"] - 15 if i+1 < len(match_anchors) else h_img*0.98)
            m_info = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            for (bbox, text, prob) in res_raw:
                curr_y, curr_x = (bbox[0][1] + bbox[2][1]) / 2, (bbox[0][0] + bbox[1][0]) / 2
                if y_start <= curr_y <= y_end:
                    t_name = engine.clean_team(text)
                    if t_name and curr_x > mid_x and t_name != m_info["h"]: m_info["a"] = t_name
                    elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper(): m_info["s"] = text
                    elif "MT" in text.upper(): m_info["mt"] = text
                    elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                        if curr_x < mid_x: m_info["h_m"] += f" {text}"
                        else: m_info["a_m"] += f" {text}"
            if m_info["a"] != "Inconnu": matches.append(m_info)

        with st.form("form_v16"):
            for i in range(10):
                m = matches[i] if i < len(matches) else {"h":"","a":"","s":"","h_m":"","a_m":"","mt":""}
                st.write(f"### Match {i+1} : {m['h']} vs {m['a']}")
                c1, c2, c3 = st.columns([1,1,1])
                sc = c1.text_input("Score Final", m['s'], key=f"s{i}")
                mt = c2.text_input("Score MT", m['mt'], key=f"mt{i}")
                m1, m2 = st.columns(2)
                m1.text_input("Buteurs D", m['h_m'].strip(), key=f"bd{i}")
                m2.text_input("Buteurs E", m['a_m'].strip(), key=f"be{i}")
                st.divider()
            st.form_submit_button("✅ SAUVEGARDER")

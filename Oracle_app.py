import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V18.1 - Permanent Database", layout="wide")

# --- MOTEUR DE PERSISTENCE (SAVE/LOAD) ---
DB_FILE = "oracle_history.json"

def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Initialisation de l'historique au démarrage
if 'history' not in st.session_state:
    st.session_state['history'] = load_history()

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

if 'saison_nom' not in st.session_state: 
    st.session_state['saison_nom'] = "Saison 2026"

st.title(f"🔮 ORACLE V18.1")

tabs = st.tabs(["🌟 SAISON", "📅 CALENDRIER", "🎯 PRONOS & TICKETS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : SAISON ---
with tabs[0]:
    st.session_state['saison_nom'] = st.text_input("Nom de la Saison", st.session_state['saison_nom'])
    if st.button("Effacer tout l'historique (Attention : Permanent)"):
        st.session_state['history'] = {}
        save_history({})
        st.rerun()

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    journee_num = st.number_input("Numéro de la Journée", min_value=1, max_value=50, value=1)
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    
    if file_cal:
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums:
                for n in nums:
                    val = float(n.replace(',', '.'))
                    if 1.01 <= val <= 60.0: f_odds.append(val)
        
        st.session_state['cal_v16'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            chunk = f_odds[i*3:i*3+3]
            o = [chunk[0] if len(chunk)>0 else 1.0, chunk[1] if len(chunk)>1 else 1.0, chunk[2] if len(chunk)>2 else 1.0]
            st.session_state['cal_v16'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v16' in st.session_state:
        with st.form("f_cal"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v16']):
                col1, col2, c1, cx, c2 = st.columns([2, 2, 1, 1, 1])
                hf = col1.selectbox(f"H{i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = col2.selectbox(f"A{i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                v1, vx, v2 = c1.number_input("C1", value=m['o'][0], key=f"c1_{i}"), cx.number_input("CX", value=m['o'][1], key=f"cx_{i}"), c2.number_input("C2", value=m['o'][2], key=f"c2_{i}")
                validated.append({'h': hf, 'a': af, 'o': [v1, vx, v2]})
            
            if st.form_submit_button("🔥 VALIDER ET ANALYSER"):
                st.session_state['ready_v16'] = validated
                # Sauvegarde permanente
                s_name = st.session_state['saison_nom']
                j_key = f"Journée {journee_num}"
                if s_name not in st.session_state['history']: st.session_state['history'][s_name] = {}
                if j_key not in st.session_state['history'][s_name]: st.session_state['history'][s_name][j_key] = {"cal": [], "res": []}
                st.session_state['history'][s_name][j_key]["cal"] = validated
                save_history(st.session_state['history'])
                st.toast("Analyse fini et va vers le pronostic", icon="📈")

# --- TAB 2 : PRONOS & TICKETS (Logique V17.7) ---
with tabs[2]:
    if 'ready_v16' in st.session_state:
        safe_data, risque_data, fun_data = [], [], []
        for m in st.session_state['ready_v16']:
            s_h, s_a = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            score_txt = f"{s_h} : {s_a}"
            st.write(f"⚽ **{m['h']} {score_txt} {m['a']}**")
            if m['o'][0] < 1.7: safe_data.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][0]})
            elif m['o'][2] < 1.7: safe_data.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][2]})
            if 1.7 <= m['o'][0] <= 3.0: risque_data.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][0]})
            elif 1.7 <= m['o'][2] <= 3.0: risque_data.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][2]})
            if m['o'][1] > 3.5: fun_data.append({"txt": f"{m['h']} {score_txt} {m['a']} (Nul)", "cote": m['o'][1]})
        
        st.divider(); c1, c2, c3 = st.columns(3)
        def show_t(col, title, data):
            with col:
                st.markdown(f"### {title}")
                if not data: st.write("Vide"); return
                total = 1.0; calc = ""
                for i, x in enumerate(data[:3]):
                    st.write(f"*{x['txt']} (Cote: {x['cote']})")
                    total *= x['cote']; calc += str(x['cote']) + (" x " if i < len(data[:3])-1 else "")
                st.info(f"Total: {calc} = **{round(total,2)}**")
        show_t(c1, "🟢 SAFE", safe_data); show_t(c2, "🟡 RISQUE", risque_data); show_t(c3, "🔴 FUN", fun_data)

# --- TAB 3 : RÉSULTATS (Logique V17.2) ---
with tabs[3]:
    j_res_num = st.number_input("Résultats pour la Journée", min_value=1, max_value=50, value=1)
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res); w, h_img = img.size; mid_x = w/2
        res_raw = reader.readtext(file_res.getvalue(), detail=1)
        res_raw.sort(key=lambda x: x[0][0][1])
        valid_teams = [t for t in [{"name": engine.clean_team(text), "y": bbox[0][1], "x": (bbox[0][0]+bbox[1][0])/2} for (bbox, text, prob) in res_raw] if t["name"] and h_img*0.12 < t["y"] < h_img*0.95]
        match_anchors = []
        for t in valid_teams:
            if t["x"] < mid_x:
                if not match_anchors or abs(t["y"] - match_anchors[-1]["y"]) > 45: match_anchors.append(t)
        matches = []
        for i, anchor in enumerate(match_anchors):
            if len(matches) >= 10: break
            y_s, y_e = anchor["y"]-15, (match_anchors[i+1]["y"]-15 if i+1 < len(match_anchors) else h_img*0.98)
            m_i = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            for (bbox, text, prob) in res_raw:
                cy, cx = (bbox[0][1]+bbox[2][1])/2, (bbox[0][0]+bbox[1][0])/2
                if y_s <= cy <= y_e:
                    tn = engine.clean_team(text)
                    if tn and cx > mid_x and tn != m_i["h"]: m_i["a"] = tn
                    elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper(): m_i["s"] = text
                    elif "MT" in text.upper(): m_i["mt"] = text
                    elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                        if cx < mid_x: m_i["h_m"] += f" {text}"
                        else: m_i["a_m"] += f" {text}"
            if m_i["a"] != "Inconnu": matches.append(m_i)
        
        with st.form("form_res"):
            final_res = []
            for i in range(10):
                m = matches[i] if i < len(matches) else {"h":"","a":"","s":"","h_m":"","a_m":"","mt":""}
                st.write(f"### Match {i+1} : {m['h']} vs {m['a']}")
                c1, c2 = st.columns(2)
                sc = c1.text_input("Score", m['s'], key=f"rs{i}")
                mt = c2.text_input("MT", m['mt'], key=f"rmt{i}")
                final_res.append({"h": m['h'], "a": m['a'], "s": sc, "mt": mt})
            
            if st.form_submit_button("✅ SAUVEGARDER"):
                s_name = st.session_state['saison_nom']
                j_key = f"Journée {j_res_num}"
                if s_name not in st.session_state['history']: st.session_state['history'][s_name] = {}
                if j_key not in st.session_state['history'][s_name]: st.session_state['history'][s_name][j_key] = {"cal": [], "res": []}
                st.session_state['history'][s_name][j_key]["res"] = final_res
                save_history(st.session_state['history']) # Sauvegarde permanente
                st.toast("c'est enregistré dans l'historique", icon="💾")

# --- TAB 4 : HISTORIQUE ---
with tabs[4]:
    st.header("📚 Archives Oracle")
    if not st.session_state['history']:
        st.info("Aucune donnée enregistrée.")
    else:
        s_sel = st.selectbox("Saison", list(st.session_state['history'].keys()))
        if s_sel:
            for j in list(st.session_state['history'][s_sel].keys()):
                with st.expander(f"📅 {j}"):
                    data = st.session_state['history'][s_sel][j]
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown("**📋 Calendrier**")
                        if data["cal"]:
                            st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "C1": m['o'][0], "CX": m['o'][1], "C2": m['o'][2]} for m in data["cal"]]))
                    with cb:
                        st.markdown("**⚽ Résultats**")
                        if data["res"]:
                            st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "Score": m['s'], "MT": m['mt']} for m in data["res"]]))

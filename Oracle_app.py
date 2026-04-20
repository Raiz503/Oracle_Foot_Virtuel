import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V19.0 - Multi-Saison Expert", layout="wide")

# --- PERSISTENCE ---
DB_FILE = "oracle_history.json"

def load_history():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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

# --- GESTION DES SAISONS ---
saisons_existantes = list(st.session_state['history'].keys())
if 'saison_active' not in st.session_state:
    st.session_state['saison_active'] = saisons_existantes[0] if saisons_existantes else "Saison 2026"

st.title(f"🔮 ORACLE V19.0")

tabs = st.tabs(["🌟 GESTION SAISON", "📅 CALENDRIER", "🎯 PRONOS & TICKETS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : NOUVELLE SAISON ---
with tabs[0]:
    st.subheader("📁 Gestion des Saisons")
    
    col_a, col_b = st.columns(2)
    with col_a:
        new_s_name = st.text_input("Nom de la nouvelle saison (ex: Saison 2027)")
        if st.button("➕ Créer la saison"):
            if new_s_name and new_s_name not in st.session_state['history']:
                st.session_state['history'][new_s_name] = {}
                save_history(st.session_state['history'])
                st.session_state['saison_active'] = new_s_name
                st.success(f"Saison {new_s_name} créée !")
                st.rerun()
    
    with col_b:
        if saisons_existantes:
            idx = saisons_existantes.index(st.session_state['saison_active']) if st.session_state['saison_active'] in saisons_existantes else 0
            st.session_state['saison_active'] = st.selectbox("Saison en cours d'utilisation", saisons_existantes, index=idx)
    
    st.divider()
    st.info(f"📍 Travail actuel sur : **{st.session_state['saison_active']}**")

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_num = st.number_input("Numéro de la Journée", min_value=1, max_value=50, value=1, key="j_cal")
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    
    if file_cal:
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t); 
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
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
                c1, c2, o1, ox, o2 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"H{i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = c2.selectbox(f"A{i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                v1, vx, v2 = o1.number_input("C1", value=m['o'][0], key=f"c1_{i}"), ox.number_input("CX", value=m['o'][1], key=f"cx_{i}"), o2.number_input("C2", value=m['o'][2], key=f"c2_{i}")
                validated.append({'h': hf, 'a': af, 'o': [v1, vx, v2]})
            
            if st.form_submit_button("🔥 VALIDER ET ARCHIVER"):
                st.session_state['ready_v16'] = validated
                s_name = st.session_state['saison_active']
                j_key = f"Journée {j_num}"
                if s_name not in st.session_state['history']: st.session_state['history'][s_name] = {}
                if j_key not in st.session_state['history'][s_name]: st.session_state['history'][s_name][j_key] = {"cal": [], "res": []}
                st.session_state['history'][s_name][j_key]["cal"] = validated
                save_history(st.session_state['history'])
                st.toast("Analyse fini et va vers le pronostic", icon="📈")

# --- TAB 2 : PRONOS & TICKETS ---
with tabs[2]:
    if 'ready_v16' in st.session_state:
        safe_d, risque_d, fun_d = [], [], []
        for m in st.session_state['ready_v16']:
            sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            score_txt = f"{sh} : {sa}"
            st.write(f"⚽ **{m['h']} {score_txt} {m['a']}**")
            if m['o'][0] < 1.7: safe_d.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][0]})
            elif m['o'][2] < 1.7: safe_d.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][2]})
            if 1.7 <= m['o'][0] <= 3.0: risque_d.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][0]})
            elif 1.7 <= m['o'][2] <= 3.0: risque_d.append({"txt": f"{m['h']} {score_txt} {m['a']}", "cote": m['o'][2]})
            if m['o'][1] > 3.5: fun_d.append({"txt": f"{m['h']} {score_txt} {m['a']} (Nul)", "cote": m['o'][1]})
        
        st.divider(); c1, c2, c3 = st.columns(3)
        def show_ticket(col, title, data):
            with col:
                st.markdown(f"### {title}")
                if not data: st.write("Vide"); return
                tot = 1.0; calc = ""
                for i, x in enumerate(data[:3]):
                    st.write(f"*{x['txt']} : {x['cote']}")
                    tot *= x['cote']; calc += str(x['cote']) + (" x " if i < len(data[:3])-1 else "")
                st.info(f"Total: {calc} = **{round(tot,2)}**")
        show_ticket(c1, "🟢 SAFE", safe_d); show_ticket(c2, "🟡 RISQUE", risque_d); show_ticket(c3, "🔴 FUN", fun_d)

# --- TAB 3 : RÉSULTATS (Moteur V17.7 Complet) ---
with tabs[3]:
    j_res_n = st.number_input("Résultats pour la Journée", min_value=1, max_value=50, value=1, key="j_res")
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if file_res:
        img = Image.open(file_res); w, h_i = img.size; mid_x = w/2
        raw = reader.readtext(file_res.getvalue(), detail=1)
        raw.sort(key=lambda x: x[0][0][1])
        teams = [t for t in [{"name": engine.clean_team(txt), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, txt, p) in raw] if t["name"] and h_i*0.12 < t["y"] < h_i*0.95]
        anchors = []
        for t in teams:
            if t["x"] < mid_x and (not anchors or abs(t["y"] - anchors[-1]["y"]) > 45): anchors.append(t)
        
        matches_res = []
        for i, a in enumerate(anchors):
            if len(matches_res) >= 10: break
            y_s, y_e = a["y"]-15, (anchors[i+1]["y"]-15 if i+1 < len(anchors) else h_i*0.98)
            info = {"h": a["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            for (bbox, txt, p) in raw:
                cy, cx = (bbox[0][1]+bbox[2][1])/2, (bbox[0][0]+bbox[1][0])/2
                if y_s <= cy <= y_e:
                    tn = engine.clean_team(txt)
                    if tn and cx > mid_x and tn != info["h"]: info["a"] = tn
                    elif re.search(r"^\d[:\-]\d$", txt.strip()) and "MT" not in txt.upper(): info["s"] = txt
                    elif "MT" in txt.upper(): info["mt"] = txt
                    elif re.search(r"\d+", txt) and not re.search(r"^\d[:\-]\d$", txt):
                        if cx < mid_x: info["h_m"] += f" {txt}'"
                        else: info["a_m"] += f" {txt}'"
            if info["a"] != "Inconnu": matches_res.append(info)
        
        with st.form("form_res"):
            final_save = []
            for i, r in enumerate(matches_res):
                st.write(f"### {r['h']} vs {r['a']}")
                col1, col2 = st.columns(2)
                fs = col1.text_input("Score Final", r['s'], key=f"fs{i}")
                ms = col2.text_input("Score MT", r['mt'], key=f"ms{i}")
                b1, b2 = st.columns(2)
                bm1 = b1.text_input("Buteurs D", r['h_m'], key=f"bm1{i}")
                bm2 = b2.text_input("Buteurs E", r['a_m'], key=f"bm2{i}")
                final_save.append({"h": r['h'], "a": r['a'], "s": fs, "mt": ms, "h_m": bm1, "a_m": bm2})
            
            if st.form_submit_button("✅ SAUVEGARDER"):
                sn = st.session_state['saison_active']
                jk = f"Journée {j_res_n}"
                if sn not in st.session_state['history']: st.session_state['history'][sn] = {}
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal": [], "res": []}
                st.session_state['history'][sn][jk]["res"] = final_save
                save_history(st.session_state['history'])
                st.toast("c'est enregistré dans l'historique", icon="💾")

# --- TAB 4 : HISTORIQUE (Avec fonctions de suppression) ---
with tabs[4]:
    st.header("📚 Archives Oracle")
    if not st.session_state['history']:
        st.info("Aucune donnée.")
    else:
        s_view = st.selectbox("Voir la saison :", list(st.session_state['history'].keys()))
        if s_view:
            for j_key in list(st.session_state['history'][s_view].keys()):
                with st.expander(f"📅 {j_key}"):
                    data = st.session_state['history'][s_view][j_key]
                    
                    # Bouton pour supprimer la journée
                    if st.button(f"🗑️ Supprimer {j_key}", key=f"del_{s_view}_{j_key}"):
                        del st.session_state['history'][s_view][j_key]
                        save_history(st.session_state['history'])
                        st.rerun()
                    
                    c_cal, c_res = st.columns(2)
                    with c_cal:
                        st.markdown("**📋 Calendrier**")
                        if data["cal"]:
                            st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "Cotes": f"{m['o'][0]} | {m['o'][1]} | {m['o'][2]}"} for m in data["cal"]]))
                    with c_res:
                        st.markdown("**⚽ Résultats**")
                        if data["res"]:
                            st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "Score": m['s'], "MT": m['mt'], "Buteurs": f"{m['h_m']} / {m['a_m']}"} for m in data["res"]]))

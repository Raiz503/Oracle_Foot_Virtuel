import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

# --- CONFIGURATION & DESIGN (V28) ---
st.set_page_config(page_title="Oracle Mahita - Fusion Expert", layout="wide")

st.markdown("""
    <style>
    .main-header { text-align: center; padding: 20px; border: 4px solid #7FFFD4; border-radius: 15px; background-color: #0E1117; box-shadow: 0px 0px 25px #7FFFD4; margin-bottom: 10px; }
    .header-title { color: #FFFFFF; font-size: 3.5em; font-weight: 900; text-transform: uppercase; -webkit-text-stroke: 1.5px #7FFFD4; }
    .img-container { border: 3px solid #7FFFD4; border-radius: 15px; padding: 10px; background: #1E1E1E; margin-bottom: 25px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- PERSISTENCE (V28/V19) ---
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

# --- HEADER & GESTION SAISON ---
st.markdown('<div class="main-header"><h1 class="header-title">Oracle Mahita</h1></div>', unsafe_allow_html=True)

saisons_existantes = list(st.session_state['history'].keys())
if not saisons_existantes:
    st.session_state['history']["Saison 2026"] = {}
    saisons_existantes = ["Saison 2026"]

if 'saison_active' not in st.session_state:
    st.session_state['saison_active'] = saisons_existantes[0]

tabs = st.tabs(["⚙️ GESTION", "📅 CALENDRIER", "🎯 PRONOS & TICKETS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : GESTION (V19/V28 Mix) ---
with tabs[0]:
    col_a, col_b = st.columns(2)
    with col_a:
        new_s_name = st.text_input("Nom de la nouvelle saison")
        if st.button("➕ Créer la saison"):
            if new_s_name and new_s_name not in st.session_state['history']:
                st.session_state['history'][new_s_name] = {}
                save_history(st.session_state['history'])
                st.rerun()
    with col_b:
        st.session_state['saison_active'] = st.selectbox("Saison Active", saisons_existantes, index=saisons_existantes.index(st.session_state['saison_active']))
    
    st.divider()
    st.download_button("📤 Exporter Backup (JSON)", json.dumps(st.session_state['history'], indent=4), "oracle_backup.json")

# --- TAB 1 : CALENDRIER (MOTEUR V19) ---
with tabs[1]:
    j_num = st.number_input("Numéro de la Journée", 1, 50, 1, key="j_cal")
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    
    if file_cal:
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            for n in nums:
                val = float(n.replace(',', '.'))
                if 1.01 <= val <= 60.0: f_odds.append(val)
        
        st.session_state['cal_temp'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            chunk = f_odds[i*3:i*3+3]
            o = [chunk[0] if len(chunk)>0 else 1.0, chunk[1] if len(chunk)>1 else 1.0, chunk[2] if len(chunk)>2 else 1.0]
            st.session_state['cal_temp'].append({'h': h, 'a': a, 'o': o})

    if 'cal_temp' in st.session_state:
        with st.form("f_cal_validation"):
            validated = []
            for i, m in enumerate(st.session_state['cal_temp']):
                c1, c2, o1, ox, o2 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"H{i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = c2.selectbox(f"A{i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                v1 = o1.number_input("C1", value=m['o'][0], key=f"c1_{i}")
                vx = ox.number_input("CX", value=m['o'][1], key=f"cx_{i}")
                v2 = o2.number_input("C2", value=m['o'][2], key=f"c2_{i}")
                validated.append({'h': hf, 'a': af, 'o': [v1, vx, v2]})
            
            if st.form_submit_button("🔥 VALIDER ET ANALYSER"):
                sn = st.session_state['saison_active']
                jk = f"Journée {j_num}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal": [], "res": []}
                st.session_state['history'][sn][jk]["cal"] = validated
                save_history(st.session_state['history'])
                st.session_state['current_ready'] = validated
                st.toast("Analyse finie et va vers le pronostic", icon="📈")

# --- TAB 2 : PRONOS & TICKETS (CONTENU V19) ---
with tabs[2]:
    if 'current_ready' in st.session_state:
        safe_d, risque_d, fun_d = [], [], []
        for m in st.session_state['current_ready']:
            # Calcul score probable (Logique V19)
            sh = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0
            sa = int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            score_txt = f"{sh} : {sa}"
            
            st.write(f"⚽ **{m['h']} {score_txt} {m['a']}**")
            
            # Répartition des tickets (Logique V19)
            if m['o'][0] < 1.7: safe_d.append({"txt": f"{m['h']} Gagne", "cote": m['o'][0]})
            elif m['o'][2] < 1.7: safe_d.append({"txt": f"{m['a']} Gagne", "cote": m['o'][2]})
            
            if 1.7 <= m['o'][0] <= 3.0: risque_d.append({"txt": f"{m['h']} {score_txt}", "cote": m['o'][0]})
            elif 1.7 <= m['o'][2] <= 3.0: risque_d.append({"txt": f"{m['a']} {score_txt}", "cote": m['o'][2]})
            
            if m['o'][1] > 3.4: fun_d.append({"txt": f"{m['h']} vs {m['a']} (Nul)", "cote": m['o'][1]})
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        def show_ticket(col, title, color, data):
            with col:
                st.markdown(f"### {title}")
                if not data: st.write("Aucun prono détecté."); return
                tot = 1.0; calc = ""
                for i, x in enumerate(data[:3]):
                    st.success(f"{x['txt']} : **{x['cote']}**")
                    tot *= x['cote']
                    calc += str(x['cote']) + (" x " if i < len(data[:3])-1 else "")
                st.info(f"Total: {round(tot,2)}")

        show_ticket(c1, "🟢 SAFE", "green", safe_d)
        show_ticket(c2, "🟡 RISQUE", "orange", risque_d)
        show_ticket(c3, "🔴 FUN", "red", fun_d)
    else:
        st.info("Validez un calendrier pour voir les pronostics.")

# --- TAB 3 : RÉSULTATS (MOTEUR V19 EFFICACE) ---
with tabs[3]:
    j_res_n = st.number_input("Résultats pour la Journée", 1, 50, 1, key="j_res")
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
        
        with st.form("form_res_v19"):
            final_save = []
            for i, r in enumerate(matches_res):
                st.write(f"**{r['h']} vs {r['a']}**")
                col1, col2 = st.columns(2)
                fs = col1.text_input("Score Final", r['s'], key=f"fs{i}")
                ms = col2.text_input("Score MT", r['mt'], key=f"ms{i}")
                bm1 = st.text_input("Buteurs D (min)", r['h_m'], key=f"bm1{i}")
                bm2 = st.text_input("Buteurs E (min)", r['a_m'], key=f"bm2{i}")
                final_save.append({"h": r['h'], "a": r['a'], "s": fs, "mt": ms, "h_m": bm1, "a_m": bm2})
            
            if st.form_submit_button("✅ SAUVEGARDER DANS L'HISTORIQUE"):
                sn = st.session_state['saison_active']
                jk = f"Journée {j_res_n}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal": [], "res": []}
                st.session_state['history'][sn][jk]["res"] = final_save
                save_history(st.session_state['history'])
                st.toast("C'est enregistré dans l'historique", icon="💾")

# --- TAB 4 : HISTORIQUE (SAUVEGARDE ET SUPPRESSION V28) ---
with tabs[4]:
    st.subheader("📚 Archives Oracle")
    s_view = st.selectbox("Saison à consulter", list(st.session_state['history'].keys()))
    
    if s_view in st.session_state['history']:
        for jk in sorted(st.session_state['history'][s_view].keys()):
            with st.expander(f"📅 {jk}"):
                data = st.session_state['history'][s_view][jk]
                
                col_del, col_space = st.columns([1, 4])
                if col_del.button(f"🗑️ Supprimer {jk}", key=f"del_{jk}"):
                    del st.session_state['history'][s_view][jk]
                    save_history(st.session_state['history'])
                    st.rerun()
                
                c_cal, c_res = st.columns(2)
                with c_cal:
                    st.markdown("**📋 Calendrier**")
                    if data.get("cal"):
                        st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "Cotes": f"{m['o'][0]} | {m['o'][1]} | {m['o'][2]}"} for m in data["cal"]]))
                with c_res:
                    st.markdown("**⚽ Résultats**")
                    if data.get("res"):
                        st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "Score": m['s'], "MT": m['mt']} for m in data["res"]]))

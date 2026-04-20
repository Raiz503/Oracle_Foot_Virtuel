import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

# Configuration de la page
st.set_page_config(page_title="Oracle Mahita", layout="wide")

# --- STYLE CSS : ORACLE MAHITA & NOTIFICATIONS ---
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 25px;
        border: 5px solid #7FFFD4; /* Vert d'eau */
        border-radius: 20px;
        background-color: #0E1117;
        box-shadow: 0px 0px 30px #7FFFD4;
        margin-bottom: 15px;
    }
    .header-title {
        color: #FFFFFF;
        font-size: 3.5em;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 6px;
        margin: 0;
        -webkit-text-stroke: 1.5px #7FFFD4;
        text-shadow: 0px 0px 15px #7FFFD4;
    }
    /* Style pour la sélection de saison centrée */
    .stSelectbox div[data-baseweb="select"] {
        border-color: #7FFFD4 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def custom_notify(text):
    msg = f"""
    <div style="
        padding: 15px; border: 3px solid #00FF00; border-radius: 10px;
        background-color: #0E1117; color: #FFFFFF; text-align: center;
        font-weight: 900; box-shadow: 0px 0px 20px #00FF00; margin: 15px 0px;
        font-size: 1.3em; text-transform: uppercase;
        -webkit-text-stroke: 1px #00FF00;
    ">
        {text}
    </div>
    """
    st.markdown(msg, unsafe_allow_html=True)

# --- BASE DE DONNÉES ---
DB_FILE = "oracle_history.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if 'history' not in st.session_state:
    st.session_state['history'] = load_db()
    if not st.session_state['history']: st.session_state['history']["Saison 2026"] = {}

# --- EN-TÊTE FIXE : ORACLE MAHITA ---
st.markdown('<div class="main-header"><h1 class="header-title">Oracle Mahita</h1></div>', unsafe_allow_html=True)

# Sélection de saison centrée sous le nom
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_b:
    saisons = list(st.session_state['history'].keys())
    s_active = st.selectbox("Saison en cours", saisons, label_visibility="collapsed")
    st.session_state['s_active'] = s_active
    st.markdown(f"<div style='text-align:center; color:#7FFFD4; font-weight:bold;'>MODE : {s_active}</div>", unsafe_allow_html=True)

# --- MOTEUR OCR ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'fr'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.teams_list = ["Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"]
    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.3)
        return m[0] if m else None

engine = OracleEngine()

# --- ONGLETS ---
tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS ACTUELS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️ RÉGLAGES"])

# --- TAB 1 : CALENDRIER ---
with tabs[0]:
    j_num = st.number_input("Journée", 1, 50, 1)
    f_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    
    if f_cal:
        # On ne lance l'OCR que si nécessaire
        if 'last_file' not in st.session_state or st.session_state['last_file'] != f_cal.name:
            res = reader.readtext(f_cal.read(), detail=0)
            t_f, o_f = [], []
            for t in res:
                n = engine.clean_team(t)
                if n: t_f.append(n)
                for val in re.findall(r"\d+[\.,]\d+", t): o_f.append(float(val.replace(',', '.')))
            
            st.session_state['tmp_cal'] = []
            for i in range(10):
                h = t_f[i*2] if len(t_f)>i*2 else "Inconnu"
                a = t_f[i*2+1] if len(t_f)>i*2+1 else "Inconnu"
                ck = o_f[i*3:i*3+3]
                st.session_state['tmp_cal'].append({'h': h, 'a': a, 'o': [ck[0] if len(ck)>0 else 1.0, ck[1] if len(ck)>1 else 1.0, ck[2] if len(ck)>2 else 1.0]})
            st.session_state['last_file'] = f_cal.name

    if 'tmp_cal' in st.session_state:
        with st.form("cal_form"):
            final_c = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                # Sécurité : On s'assure que la cote n'est pas 0
                v1 = o1.number_input("C1", value=max(0.1, m['o'][0]), key=f"c1_{i}")
                vx = ox.number_input("CX", value=max(0.1, m['o'][1]), key=f"cx_{i}")
                v2 = o2.number_input("C2", value=max(0.1, m['o'][2]), key=f"c2_{i}")
                final_c.append({'h':th, 'a':ta, 'o':[v1, vx, v2]})
            
            if st.form_submit_button("🔥 ANALYSER & VALIDER"):
                sn, jk = st.session_state['s_active'], f"Journée {j_num}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                
                # Calcul robuste des pronos
                p_list = []
                for m in final_c:
                    sh = int((3.0 / m['o'][0]) + 0.4) if m['o'][0] > 0 else 0
                    sa = int((3.0 / m['o'][2]) + 0.1) if m['o'][2] > 0 else 0
                    p_list.append({"m": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o']})
                
                st.session_state['history'][sn][jk]["cal"] = final_c
                st.session_state['history'][sn][jk]["pro"] = p_list
                st.session_state['ready_cal'] = final_c
                save_db(st.session_state['history'])
                st.session_state['show_notif_cal'] = True

        if st.session_state.get('show_notif_cal'):
            custom_notify("Analyse fini et va vers le pronostic")
            st.session_state['show_notif_cal'] = False

# --- TAB 2 : PRONOS ACTUELS ---
with tabs[1]:
    if 'ready_cal' in st.session_state:
        st.subheader("🎯 Prédictions de l'Oracle")
        for m in st.session_state['ready_cal']:
            sh = int((3.0 / m['o'][0]) + 0.4)
            sa = int((3.0 / m['o'][2]) + 0.1)
            st.markdown(f"### ⚽ {m['h']} <span style='color:#7FFFD4'>{sh}:{sa}</span> {m['a']}", unsafe_allow_html=True)
    else:
        st.info("Veuillez d'abord valider un calendrier dans le premier onglet.")

# --- TAB 3 : RÉSULTATS ---
with tabs[2]:
    j_res = st.number_input("Journée Résultat", 1, 50, 1, key="res_j")
    f_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if f_res:
        img = Image.open(f_res); w, hi = img.size; mid = w/2
        raw = reader.readtext(f_res.getvalue(), detail=1)
        raw.sort(key=lambda x: x[0][0][1])
        tms = [t for t in [{"n": engine.clean_team(txt), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, txt, p) in raw] if t["n"] and hi*0.12 < t["y"] < hi*0.95]
        ancs = []
        for t in tms:
            if t["x"] < mid and (not ancs or abs(t["y"] - ancs[-1]["y"]) > 45): ancs.append(t)
        
        extracted = []
        for i, a in enumerate(ancs):
            if len(extracted) >= 10: break
            ys, ye = a["y"]-15, (ancs[i+1]["y"]-15 if i+1 < len(ancs) else hi*0.98)
            inf = {"h": a["n"], "a": "Inconnu", "s": "0:0", "hm": "", "am": "", "mt": ""}
            for (bb, tx, p) in raw:
                cy, cx = (bb[0][1]+bb[2][1])/2, (bb[0][0]+bb[1][0])/2
                if ys <= cy <= ye:
                    tn = engine.clean_team(tx)
                    if tn and cx > mid and tn != inf["h"]: inf["a"] = tn
                    elif re.search(r"^\d[:\-]\d$", tx.strip()) and "MT" not in tx.upper(): inf["s"] = tx
                    elif "MT" in tx.upper(): inf["mt"] = tx
                    elif re.search(r"\d+", tx) and not re.search(r"^\d[:\-]\d$", tx):
                        if cx < mid: inf["hm"] += f" {tx}'"
                        else: inf["am"] += f" {tx}'"
            if inf["a"] != "Inconnu": extracted.append(inf)
        
        with st.form("res_form"):
            val_data = []
            for i, r in enumerate(extracted):
                st.markdown(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2); fs = c1.text_input("Final", r['s'], key=f"s_{i}"); ms = c2.text_input("MT", r['mt'], key=f"m_{i}")
                bh = st.text_input("Buts Dom", r['hm'], key=f"bh_{i}"); ba = st.text_input("Buts Ext", r['am'], key=f"ba_{i}")
                val_data.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":bh, "am":ba})
            if st.form_submit_button("✅ ENREGISTRER"):
                sn, jk = st.session_state['s_active'], f"Journée {j_res}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                st.session_state['history'][sn][jk]["res"] = val_data
                save_db(st.session_state['history'])
                st.session_state['show_notif_res'] = True

        if st.session_state.get('show_notif_res'):
            custom_notify("c'est enregistré dans l'historique")
            st.session_state['show_notif_res'] = False

# --- TAB 4 : HISTORIQUE ---
with tabs[3]:
    s_sel = st.selectbox("Historique de la saison", list(st.session_state['history'].keys()))
    for jk, data in st.session_state['history'][s_sel].items():
        with st.expander(f"📅 {jk}"):
            h_tabs = st.tabs(["📋 Calendrier", "🎯 Pronostic", "⚽ Résultat"])
            with h_tabs[0]: st.table(data.get("cal", []))
            with h_tabs[1]: st.table(data.get("pro", []))
            with h_tabs[2]: st.table(data.get("res", []))

# --- TAB 5 : RÉGLAGES ---
with tabs[4]:
    st.subheader("⚙️ Paramètres")
    c1, c2 = st.columns(2)
    with c1:
        new_s = st.text_input("Nom nouvelle saison")
        if st.button("Créer"):
            if new_s: st.session_state['history'][new_s] = {}; save_db(st.session_state['history']); st.rerun()
    with c2:
        up = st.file_uploader("📥 Importer JSON", type="json")
        if up: st.session_state['history'].update(json.load(up)); save_db(st.session_state['history']); st.rerun()
    if st.session_state['history']:
        st.download_button("📤 Exporter BDD", data=json.dumps(st.session_state['history'], indent=4), file_name="oracle_data.json")

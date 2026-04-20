import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V20.2 - Scan Restauré", layout="wide")

# --- STYLE NOTIFICATIONS NÉON VERT ---
def custom_notify(text):
    msg = f"""
    <div style="
        padding: 15px; border: 3px solid #00FF00; border-radius: 10px;
        background-color: #0E1117; color: #FFFFFF; text-align: center;
        font-weight: 900; box-shadow: 0px 0px 20px #00FF00; margin: 20px 0px;
        font-size: 1.2em; text-transform: uppercase;
        -webkit-text-stroke: 1px #00FF00;
    ">
        {text}
    </div>
    """
    st.markdown(msg, unsafe_allow_html=True)

# --- GESTION BASE DE DONNÉES ---
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

# --- INTERFACE ---
st.title("🔮 ORACLE V20.2")

tabs = st.tabs(["🌟 SAISONS & IMPORT/EXPORT", "📅 CALENDRIER", "🎯 PRONOS ACTUELS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : SAISONS & GESTION ---
with tabs[0]:
    st.subheader("💾 Sauvegarde")
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state['history']:
            json_data = json.dumps(st.session_state['history'], indent=4)
            st.download_button("📥 EXPORTER JSON", data=json_data, file_name="oracle_backup.json")
    with c2:
        up = st.file_uploader("📤 IMPORTER JSON", type="json")
        if up:
            st.session_state['history'].update(json.load(up))
            save_db(st.session_state['history']); st.success("Fusionné !")

    st.divider()
    if not st.session_state['history']: st.session_state['history']["Saison 2026"] = {}
    ca, cb = st.columns(2)
    with ca:
        ns = st.text_input("Nom nouvelle saison")
        if st.button("Créer"):
            if ns: st.session_state['history'][ns] = {}; save_db(st.session_state['history']); st.rerun()
    with cb:
        st.session_state['s_active'] = st.selectbox("Saison de travail :", list(st.session_state['history'].keys()))

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_num = st.number_input("Journée", 1, 50, 1, key="jcal")
    f_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    if f_cal:
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

    if 'tmp_cal' in st.session_state:
        with st.form("cal_val"):
            final_c = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                final_c.append({'h':th, 'a':ta, 'o':[o1.number_input("C1",value=m['o'][0],key=f"oc1{i}"), ox.number_input("CX",value=m['o'][1],key=f"ocx{i}"), o2.number_input("C2",value=m['o'][2],key=f"oc2{i}")]})
            if st.form_submit_button("🔥 VALIDER"):
                sn, jk = st.session_state['s_active'], f"Journée {j_num}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                st.session_state['history'][sn][jk]["cal"] = final_c
                p_list = [{"m": f"{m['h']} {int((3.0/m['o'][0])+0.4)}:{int((3.0/m['o'][2])+0.1)} {m['a']}", "c": m['o']} for m in final_c]
                st.session_state['history'][sn][jk]["pro"] = p_list
                save_db(st.session_state['history']); st.session_state['ready_cal'] = final_c
                custom_notify("Analyse fini et va vers le pronostic")

# --- TAB 2 : PRONOS ---
with tabs[2]:
    if 'ready_cal' in st.session_state:
        for m in st.session_state['ready_cal']:
            sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            st.write(f"⚽ **{m['h']} {sh}:{sa} {m['a']}**")

# --- TAB 3 : RÉSULTATS (MOTEUR V17.7 RESTAURÉ) ---
with tabs[3]:
    j_res = st.number_input("Journée Résultat", 1, 50, 1, key="jres")
    f_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if f_res:
        img = Image.open(f_res); w, hi = img.size; mid = w/2
        raw = reader.readtext(f_res.getvalue(), detail=1)
        raw.sort(key=lambda x: x[0][0][1])
        # Filtrage et détection des ancres (équipes à gauche)
        tms = [t for t in [{"n": engine.clean_team(txt), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, txt, p) in raw] if t["n"] and hi*0.12 < t["y"] < hi*0.95]
        ancs = []
        for t in tms:
            if t["x"] < mid and (not ancs or abs(t["y"] - ancs[-1]["y"]) > 45): ancs.append(t)
        
        extracted_matches = []
        for i, a in enumerate(ancs):
            if len(extracted_matches) >= 10: break
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
            if inf["a"] != "Inconnu": extracted_matches.append(inf)
        
        with st.form("res_val_form"):
            final_res_data = []
            for i, r in enumerate(extracted_matches):
                st.markdown(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Score Final", r['s'], key=f"rs{i}")
                ms = c2.text_input("Score MT", r['mt'], key=f"rm{i}")
                b1, b2 = st.columns(2)
                bh = b1.text_input("Buteurs Domicile", r['hm'], key=f"rbh{i}")
                ba = b2.text_input("Buteurs Extérieur", r['am'], key=f"rba{i}")
                final_res_data.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":bh, "am":ba})
            
            if st.form_submit_button("✅ ENREGISTRER DANS L'HISTORIQUE"):
                sn, jk = st.session_state['s_active'], f"Journée {j_res}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                st.session_state['history'][sn][jk]["res"] = final_res_data
                save_db(st.session_state['history'])
                custom_notify("c'est enregistré dans l'historique")

# --- TAB 4 : HISTORIQUE ---
with tabs[4]:
    if not st.session_state['history']: st.info("Vide.")
    else:
        s_sel = st.selectbox("Saison", list(st.session_state['history'].keys()))
        for jk in list(st.session_state['history'][s_sel].keys()):
            with st.expander(f"📅 {jk}"):
                if st.button("🗑️ Supprimer", key=f"del_{jk}"):
                    del st.session_state['history'][s_sel][jk]; save_db(st.session_state['history']); st.rerun()
                stabs = st.tabs(["📋 Calendrier", "🎯 Pronostic", "⚽ Résultat"])
                d = st.session_state['history'][s_sel][jk]
                with stabs[0]: 
                    if d.get("cal"): st.table(d["cal"])
                with stabs[1]:
                    if d.get("pro"): st.table(d["pro"])
                with stabs[2]:
                    if d.get("res"): st.table(d["res"])

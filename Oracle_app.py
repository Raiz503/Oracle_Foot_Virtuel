import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V19.1 - Stabilisé", layout="wide")

# --- PERSISTENCE ---
DB_FILE = "oracle_history.json"

def load_history():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if data else {}
        except: return {}
    return {}

def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Initialisation sécurisée
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

# --- RÉGLAGE DE LA SAISON ACTIVE ---
saisons_existantes = list(st.session_state['history'].keys())

if 'saison_active' not in st.session_state:
    if saisons_existantes:
        st.session_state['saison_active'] = saisons_existantes[0]
    else:
        st.session_state['saison_active'] = "Saison 2026"
        st.session_state['history']["Saison 2026"] = {} # Création auto pour éviter le bug rouge

st.title(f"🔮 ORACLE V19.1")

tabs = st.tabs(["🌟 GESTION SAISON", "📅 CALENDRIER", "🎯 PRONOS & TICKETS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : GESTION SAISON ---
with tabs[0]:
    st.subheader("📁 Configuration des Saisons")
    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input("Nom de la nouvelle saison")
        if st.button("➕ Créer"):
            if new_name:
                st.session_state['history'][new_name] = {}
                save_history(st.session_state['history'])
                st.session_state['saison_active'] = new_name
                st.rerun()
    with c2:
        current_list = list(st.session_state['history'].keys())
        if current_list:
            idx = current_list.index(st.session_state['saison_active']) if st.session_state['saison_active'] in current_list else 0
            st.session_state['saison_active'] = st.selectbox("Travailler sur :", current_list, index=idx)
    st.info(f"Saison active : **{st.session_state['saison_active']}**")

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_num = st.number_input("Journée", 1, 50, 1, key="j_cal")
    f_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    if f_cal:
        res = reader.readtext(f_cal.read(), detail=0)
        f_t, f_o = [], []
        for t in res:
            n = engine.clean_team(t)
            if n: f_t.append(n)
            nums = re.findall(r"\d+[\.,]\d+", t)
            for num in nums:
                v = float(num.replace(',', '.'))
                if 1.01 <= v <= 60.0: f_o.append(v)
        st.session_state['cal_v16'] = []
        for i in range(10):
            h = f_t[i*2] if len(f_t)>i*2 else "Inconnu"
            a = f_t[i*2+1] if len(f_t)>i*2+1 else "Inconnu"
            ck = f_o[i*3:i*3+3]
            o = [ck[0] if len(ck)>0 else 1.0, ck[1] if len(ck)>1 else 1.0, ck[2] if len(ck)>2 else 1.0]
            st.session_state['cal_v16'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v16' in st.session_state:
        with st.form("f_cal_val"):
            val_data = []
            for i, m in enumerate(st.session_state['cal_v16']):
                c1, c2, o1, ox, o2 = st.columns([2, 2, 1, 1, 1])
                hf = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0, key=f"h{i}")
                af = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0, key=f"a{i}")
                v1 = o1.number_input("C1", value=m['o'][0], key=f"oc1{i}")
                vx = ox.number_input("CX", value=m['o'][1], key=f"ocx{i}")
                v2 = o2.number_input("C2", value=m['o'][2], key=f"oc2{i}")
                val_data.append({'h': hf, 'a': af, 'o': [v1, vx, v2]})
            if st.form_submit_button("🔥 VALIDER"):
                st.session_state['ready_v16'] = val_data
                sn = st.session_state['saison_active']
                jk = f"Journée {j_num}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal": [], "res": []}
                st.session_state['history'][sn][jk]["cal"] = val_data
                save_history(st.session_state['history'])
                st.toast("Analyse fini et va vers le pronostic")

# --- TAB 2 : PRONOS ---
with tabs[2]:
    if 'ready_v16' in st.session_state:
        s_d, r_d, f_d = [], [], []
        for m in st.session_state['ready_v16']:
            sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            st.write(f"⚽ **{m['h']} {sh}:{sa} {m['a']}**")
            if m['o'][0] < 1.7: s_d.append({"t": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o'][0]})
            elif m['o'][2] < 1.7: s_d.append({"t": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o'][2]})
            if 1.7 <= m['o'][0] <= 3.0: r_d.append({"t": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o'][0]})
            elif 1.7 <= m['o'][2] <= 3.0: r_d.append({"t": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o'][2]})
            if m['o'][1] > 3.5: f_d.append({"t": f"{m['h']} {sh}:{sa} {m['a']} (X)", "c": m['o'][1]})
        
        st.divider()
        cols = st.columns(3)
        names = ["🟢 SAFE", "🟡 RISQUE", "🔴 FUN"]
        for i, data in enumerate([s_d, r_d, f_d]):
            with cols[i]:
                st.subheader(names[i])
                if data:
                    t_c = 1.0; clc = ""
                    for j, x in enumerate(data[:3]):
                        st.write(f"*{x['t']} ({x['c']})")
                        t_c *= x['c']; clc += str(x['c']) + (" x " if j < len(data[:3])-1 else "")
                    st.success(f"Total: {clc} = **{round(t_c, 2)}**")

# --- TAB 3 : RÉSULTATS (V17.7 RE-FIX) ---
with tabs[3]:
    j_res = st.number_input("Journée", 1, 50, 1, key="jr")
    f_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if f_res:
        img = Image.open(f_res); w, hi = img.size; mid = w/2
        raw = reader.readtext(f_res.getvalue(), detail=1)
        raw.sort(key=lambda x: x[0][0][1])
        tms = [t for t in [{"n": engine.clean_team(txt), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, txt, p) in raw] if t["n"] and hi*0.12 < t["y"] < hi*0.95]
        ancs = []
        for t in tms:
            if t["x"] < mid and (not ancs or abs(t["y"] - ancs[-1]["y"]) > 45): ancs.append(t)
        
        matches = []
        for i, a in enumerate(ancs):
            if len(matches) >= 10: break
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
            if inf["a"] != "Inconnu": matches.append(inf)
        
        with st.form("f_res_save"):
            final = []
            for i, r in enumerate(matches):
                st.markdown(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Score Final", r['s'], key=f"f{i}")
                ms = c2.text_input("Score MT", r['mt'], key=f"m{i}")
                b1, b2 = st.columns(2)
                bh = b1.text_input("Buteurs D", r['hm'], key=f"bh{i}")
                ba = b2.text_input("Buteurs E", r['am'], key=f"ba{i}")
                final.append({"h": r['h'], "a": r['a'], "s": fs, "mt": ms, "hm": bh, "am": ba})
            if st.form_submit_button("✅ SAUVEGARDER"):
                sn = st.session_state['saison_active']
                jk = f"Journée {j_res}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal": [], "res": []}
                st.session_state['history'][sn][jk]["res"] = final
                save_history(st.session_state['history'])
                st.toast("c'est enregistré dans l'historique")

# --- TAB 4 : HISTORIQUE (Avec Suppression) ---
with tabs[4]:
    st.header("📚 Archives")
    if not st.session_state['history']: st.info("Vide.")
    else:
        sv = st.selectbox("Saison", list(st.session_state['history'].keys()))
        if sv:
            for jk in list(st.session_state['history'][sv].keys()):
                with st.expander(f"📅 {jk}"):
                    if st.button(f"🗑️ Supprimer {jk}", key=f"d_{sv}_{jk}"):
                        del st.session_state['history'][sv][jk]
                        save_history(st.session_state['history'])
                        st.rerun()
                    ca, cb = st.columns(2)
                    d = st.session_state['history'][sv][jk]
                    with ca:
                        if d["cal"]: st.table(pd.DataFrame([{"M": f"{m['h']} vs {m['a']}", "C": f"{m['o'][0]}|{m['o'][1]}|{m['o'][2]}"} for m in d["cal"]]))
                    with cb:
                        if d["res"]: st.table(pd.DataFrame([{"M": f"{m['h']} vs {m['a']}", "S": m['s'], "MT": m['mt'], "B": f"{m['hm']} / {m['am']}"} for m in d["res"]]))

import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image
import numpy as np

# Configuration
st.set_page_config(page_title="Oracle Mahita", layout="wide")

# --- DESIGN ---
st.markdown("""
    <style>
    .main-header { text-align: center; padding: 20px; border: 4px solid #7FFFD4; border-radius: 15px; background-color: #0E1117; box-shadow: 0px 0px 25px #7FFFD4; margin-bottom: 10px; }
    .header-title { color: #FFFFFF; font-size: 3.5em; font-weight: 900; text-transform: uppercase; -webkit-text-stroke: 1.5px #7FFFD4; }
    .img-container { border: 3px solid #7FFFD4; border-radius: 15px; padding: 10px; background: #1E1E1E; margin-bottom: 25px; text-align: center; }
    .next-day-box { text-align: center; background: rgba(127, 255, 212, 0.2); border: 1px solid #7FFFD4; border-radius: 10px; padding: 10px; color: #FFFFFF; font-weight: bold; width: 300px; margin: 10px auto; }
    </style>
    """, unsafe_allow_html=True)

def custom_notify(text):
    st.markdown(f"""<div style="padding:15px; border:3px solid #00FF00; border-radius:10px; background-color:#0E1117; color:#FFFFFF; text-align:center; font-weight:900; box-shadow:0px 0px 20px #00FF00; margin:15px 0px;">{text}</div>""", unsafe_allow_html=True)

# --- LOGIQUE CLASSEMENT (AVEC RANG) ---
def get_standings(season_data, teams_list):
    stats = {team: {"MJ": 0, "V": 0, "N": 0, "D": 0, "BP": 0, "BC": 0, "Diff": 0, "Pts": 0} for team in teams_list}
    for jk, data in season_data.items():
        if data.get("res"):
            for m in data["res"]:
                try:
                    s_h, s_a = map(int, m['s'].replace('-', ':').split(':'))
                    h, a = m['h'], m['a']
                    if h in stats and a in stats:
                        stats[h]["MJ"] += 1; stats[a]["MJ"] += 1
                        stats[h]["BP"] += s_h; stats[h]["BC"] += s_a
                        stats[a]["BP"] += s_a; stats[a]["BC"] += s_h
                        if s_h > s_a: stats[h]["V"] += 1; stats[h].update({"Pts": stats[h]["Pts"]+3}); stats[a]["D"] += 1
                        elif s_h < s_a: stats[a]["V"] += 1; stats[a].update({"Pts": stats[a]["Pts"]+3}); stats[h]["D"] += 1
                        else: stats[h]["N"] += 1; stats[h]["Pts"] += 1; stats[a]["N"] += 1; stats[a]["Pts"] += 1
                except: continue
    df = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Équipe'})
    df['Diff'] = df['BP'] - df['BC']
    df = df.sort_values(by=["Pts", "Diff", "BP"], ascending=False).reset_index(drop=True)
    df.insert(0, 'Rang', range(1, len(df) + 1))
    return df

# --- PERSISTENCE ---
DB_FILE = "oracle_history.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

if 'history' not in st.session_state:
    st.session_state['history'] = load_db()
    if not st.session_state['history']: st.session_state['history']["Saison 2026"] = {}

# --- OCR ENGINE ---
@st.cache_resource
def load_ocr(): return easyocr.Reader(['en', 'fr'], gpu=False)
reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.teams_list = ["Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"]
    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.3)
        return m[0] if m else None

engine = OracleEngine()

# --- HEADER ---
st.markdown('<div class="main-header"><h1 class="header-title">Oracle Mahita</h1></div>', unsafe_allow_html=True)
saisons = list(st.session_state['history'].keys())
s_active = st.selectbox("Saison", saisons, label_visibility="collapsed")
st.session_state['s_active'] = s_active

# Détection Journée
res_days = [int(re.search(r'\d+', k).group()) for k in st.session_state['history'][s_active].keys() if st.session_state['history'][s_active][k].get("res")]
next_j = max(res_days) + 1 if res_days else 1
st.markdown(f'<div class="next-day-box">PROCHAINE ÉTAPE : J-{next_j}</div>', unsafe_allow_html=True)

tabs = st.tabs(["🏆 CLASSEMENT", "📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️"])

# --- TAB CALENDRIER (SCAN AMÉLIORÉ) ---
with tabs[1]:
    j_cal = st.number_input("Journée", 1, 50, next_j)
    f_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'])
    if f_cal:
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(f_cal, caption="IMAGE SOURCE - CALENDRIER", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        img_bytes = f_cal.getvalue()
        raw_res = reader.readtext(img_bytes, detail=0)
        
        # Moteur de scan Calendrier (Extracteur de cotes et équipes)
        t_found, o_found = [], []
        for txt in raw_res:
            team = engine.clean_team(txt)
            if team: t_found.append(team)
            # Capture des cotes (ex: 1.45 ou 2,30)
            cotes = re.findall(r"\d+[\.,]\d+", txt)
            for c in cotes: o_found.append(float(c.replace(',', '.')))
        
        tmp = []
        for i in range(min(10, len(t_found)//2)):
            h, a = t_found[i*2], t_found[i*2+1]
            cks = o_found[i*3:i*3+3]
            tmp.append({'h': h, 'a': a, 'o': [cks[0] if len(cks)>0 else 1.0, cks[1] if len(cks)>1 else 1.0, cks[2] if len(cks)>2 else 1.0]})
        st.session_state['tmp_cal'] = tmp

    if 'tmp_cal' in st.session_state:
        with st.form("f_cal_stable"):
            final = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                final.append({'h':th, 'a':ta, 'o':[o1.number_input("C1", value=m['o'][0], key=f"o1{i}"), ox.number_input("CX", value=m['o'][1], key=f"ox{i}"), o2.number_input("C2", value=m['o'][2], key=f"o2{i}")]})
            if st.form_submit_button("🔥 VALIDER LE CALENDRIER"):
                jk = f"Journée {j_cal}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["cal"] = final
                st.session_state['history'][s_active][jk]["pro"] = [{"m": f"{m['h']} {int((3.0/max(0.1, m['o'][0]))+0.4)}:{int((3.0/max(0.1, m['o'][2]))+0.1)} {m['a']}", "c": m['o']} for m in final]
                save_db(st.session_state['history']); st.session_state['ready_cal'] = final
                custom_notify("Analyse fini et va vers le pronostic")

# --- TAB RÉSULTATS (SCAN STABLE V17.7) ---
with tabs[3]:
    j_res = st.number_input("Journée Résultats", 1, 50, next_j)
    f_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if f_res:
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(f_res, caption="IMAGE SOURCE - RÉSULTATS", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        img_pil = Image.open(f_res); w, hi = img_pil.size; mid = w/2
        raw = reader.readtext(f_res.getvalue(), detail=1)
        # Filtrage et tri vertical
        raw.sort(key=lambda x: x[0][0][1])
        
        # Moteur Scan Résultats
        teams_data = [t for t in [{"n": engine.clean_team(tx), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, tx, p) in raw] if t["n"] and hi*0.1 < t["y"] < hi*0.95]
        anchors = []
        for t in teams_data:
            if t["x"] < mid and (not anchors or abs(t["y"] - anchors[-1]["y"]) > 40): anchors.append(t)
        
        extracted = []
        for i, a in enumerate(anchors):
            ys, ye = a["y"]-15, (anchors[i+1]["y"]-15 if i+1 < len(anchors) else hi*0.98)
            inf = {"h": a["n"], "a": "Inconnu", "s": "0:0", "hm": "", "am": "", "mt": ""}
            for (box, tx, p) in raw:
                cy, cx = (box[0][1]+box[2][1])/2, (box[0][0]+box[1][0])/2
                if ys <= cy <= ye:
                    tn = engine.clean_team(tx)
                    if tn and cx > mid and tn != inf["h"]: inf["a"] = tn
                    elif re.search(r"^\d[:\-]\d$", tx.strip()) and "MT" not in tx.upper(): inf["s"] = tx
                    elif "MT" in tx.upper(): inf["mt"] = tx
                    elif re.search(r"\d+", tx):
                        if cx < mid: inf["hm"] += f" {tx}'"
                        else: inf["am"] += f" {tx}'"
            if inf["a"] != "Inconnu": extracted.append(inf)
        
        with st.form("f_res_stable"):
            val_r = []
            for i, r in enumerate(extracted):
                st.write(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Final", r['s'], key=f"fs{i}")
                mt = c2.text_input("MT", r['mt'], key=f"mt{i}")
                bh = st.text_input("Buts Dom", r['hm'], key=f"bh{i}")
                ba = st.text_input("Buts Ext", r['am'], key=f"ba{i}")
                val_r.append({"h":r['h'], "a":r['a'], "s":fs, "mt":mt, "hm":bh, "am":ba})
            if st.form_submit_button("✅ ENREGISTRER RÉSULTATS + CLASSEMENT"):
                jk = f"Journée {j_res}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["res"] = val_r
                # Snapshot du classement
                df_rank = get_standings(st.session_state['history'][s_active], engine.teams_list)
                st.session_state['history'][s_active][jk]["rank"] = df_rank.to_dict(orient='records')
                save_db(st.session_state['history'])
                custom_notify("c'est enregistré dans l'historique")

# --- TAB HISTORIQUE ---
with tabs[4]:
    s_days = sorted(st.session_state['history'][s_active].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for jk in s_days:
        with st.expander(f"📅 {jk}"):
            d = st.session_state['history'][s_active][jk]
            h_sub = st.tabs(["📋 Calendrier", "🎯 Prono", "⚽ Résultat", "📊 Classement J."])
            with h_sub[0]: 
                st.table(d.get("cal", []))
                if d.get("cal") and st.button(f"🔮 Prédire (Simulation)", key=f"sim{jk}"):
                    d["pro"] = [{"m": f"{m['h']} {int((3.0/max(0.1, m['o'][0]))+0.4)}:{int((3.0/max(0.1, m['o'][2]))+0.1)} {m['a']}", "c": m['o']} for m in d["cal"]]
                    save_db(st.session_state['history']); st.rerun()
            with h_sub[1]: st.table(d.get("pro", []))
            with h_sub[2]: st.table(d.get("res", []))
            with h_sub[3]: 
                if d.get("rank"): st.table(pd.DataFrame(d["rank"]))

# --- CLASSEMENT GÉNÉRAL ---
with tabs[0]:
    st.table(get_standings(st.session_state['history'][s_active], engine.teams_list))

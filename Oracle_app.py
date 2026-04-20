import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image

# Configuration
st.set_page_config(page_title="Oracle Mahita", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-header {
        text-align: center; padding: 20px; border: 4px solid #7FFFD4;
        border-radius: 15px; background-color: #0E1117;
        box-shadow: 0px 0px 25px #7FFFD4; margin-bottom: 10px;
    }
    .header-title {
        color: #FFFFFF; font-size: 3em; font-weight: 900;
        text-transform: uppercase; letter-spacing: 5px; margin: 0;
        -webkit-text-stroke: 1.5px #7FFFD4; text-shadow: 0px 0px 10px #7FFFD4;
    }
    .info-center { text-align: center; color: #7FFFD4; font-weight: bold; }
    .next-day-glow {
        color: #FFFFFF; background: rgba(127, 255, 212, 0.2);
        padding: 5px 15px; border-radius: 10px; border: 1px solid #7FFFD4;
        display: inline-block; margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def custom_notify(text):
    st.markdown(f"""<div style="padding:15px; border:3px solid #00FF00; border-radius:10px; background-color:#0E1117; color:#FFFFFF; text-align:center; font-weight:900; box-shadow:0px 0px 20px #00FF00; margin:15px 0px; font-size:1.2em;">{text}</div>""", unsafe_allow_html=True)

# --- LOGIQUE CALCUL CLASSEMENT (AVEC RANG) ---
def get_standings(season_data, teams_list):
    stats = {team: {"MJ": 0, "V": 0, "N": 0, "D": 0, "BP": 0, "BC": 0, "Diff": 0, "Pts": 0} for team in teams_list}
    for jk, data in season_data.items():
        if "res" in data and data["res"]:
            for m in data["res"]:
                try:
                    s_h, s_a = map(int, m['s'].replace('-', ':').split(':'))
                    h, a = m['h'], m['a']
                    if h in stats and a in stats:
                        stats[h]["MJ"] += 1; stats[a]["MJ"] += 1
                        stats[h]["BP"] += s_h; stats[h]["BC"] += s_a
                        stats[a]["BP"] += s_a; stats[a]["BC"] += s_h
                        if s_h > s_a: stats[h]["V"] += 1; stats[h]["Pts"] += 3; stats[a]["D"] += 1
                        elif s_h < s_a: stats[a]["V"] += 1; stats[a]["Pts"] += 3; stats[h]["D"] += 1
                        else: stats[h]["N"] += 1; stats[h]["Pts"] += 1; stats[a]["N"] += 1; stats[a]["Pts"] += 1
                except: continue
    for t in stats: stats[t]["Diff"] = stats[t]["BP"] - stats[t]["BC"]
    
    df = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Équipe'})
    df = df.sort_values(by=["Pts", "Diff", "BP"], ascending=False).reset_index(drop=True)
    
    # Ajout du numéro de Rang (1, 2, 3...)
    df.insert(0, 'Rang', range(1, len(df) + 1))
    return df

# --- GESTION BDD ---
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

# --- EN-TÊTE ---
st.markdown('<div class="main-header"><h1 class="header-title">Oracle Mahita</h1></div>', unsafe_allow_html=True)

c_l, c_m, c_r = st.columns([1, 1, 1])
with c_m:
    saisons = list(st.session_state['history'].keys())
    s_active = st.selectbox("Saison", saisons, label_visibility="collapsed")
    st.session_state['s_active'] = s_active
    
    # Journée suivante auto
    existing_days = []
    for k, v in st.session_state['history'][s_active].items():
        if v.get("res"):
            match = re.search(r'\d+', k)
            if match: existing_days.append(int(match.group()))
    next_day = max(existing_days) + 1 if existing_days else 1
    st.session_state['next_day'] = next_day
    
    st.markdown(f'<div style="text-align:center;"><div class="next-day-glow">PRÉDIRE : JOURNÉE {next_day}</div></div>', unsafe_allow_html=True)

# --- MOTEUR ---
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

# --- ONGLETS ---
tabs = st.tabs(["🏆 CLASSEMENT GÉNÉRAL", "📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️"])

# --- TAB 1 : CLASSEMENT ---
with tabs[0]:
    st.subheader(f"Classement - {s_active}")
    st.table(get_standings(st.session_state['history'][s_active], engine.teams_list))

# --- TAB 2 : CALENDRIER ---
with tabs[1]:
    j_input = st.number_input("Journée", 1, 50, st.session_state['next_day'])
    f_cal = st.file_uploader("Scan Calendrier", type=['jpg','png','jpeg'])
    if f_cal:
        res = reader.readtext(f_cal.read(), detail=0)
        t_f, o_f = [], []
        for t in res:
            n = engine.clean_team(t); 
            if n: t_f.append(n)
            for val in re.findall(r"\d+[\.,]\d+", t): o_f.append(float(val.replace(',', '.')))
        st.session_state['tmp_cal'] = []
        for i in range(10):
            h, a = (t_f[i*2] if len(t_f)>i*2 else "Inconnu"), (t_f[i*2+1] if len(t_f)>i*2+1 else "Inconnu")
            ck = o_f[i*3:i*3+3]
            st.session_state['tmp_cal'].append({'h': h, 'a': a, 'o': [ck[0] if len(ck)>0 else 1.0, ck[1] if len(ck)>1 else 1.0, ck[2] if len(ck)>2 else 1.0]})

    if 'tmp_cal' in st.session_state:
        with st.form("f_cal"):
            final_c = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                final_c.append({'h':th, 'a':ta, 'o':[o1.number_input("C1",value=m['o'][0],key=f"o1{i}"), ox.number_input("CX",value=m['o'][1],key=f"ox{i}"), o2.number_input("C2",value=m['o'][2],key=f"o2{i}")]})
            if st.form_submit_button("🔥 ANALYSER"):
                jk = f"Journée {j_input}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["cal"] = final_c
                # Calcul prono
                st.session_state['history'][s_active][jk]["pro"] = [{"m": f"{m['h']} {int((3.0/m['o'][0])+0.4)}:{int((3.0/m['o'][2])+0.1)} {m['a']}", "c": m['o']} for m in final_c]
                save_db(st.session_state['history']); st.session_state['ready_cal'] = final_c
                custom_notify("Analyse terminée !"); st.rerun()

# --- TAB 4 : RÉSULTATS ---
with tabs[3]:
    j_res_input = st.number_input("Journée Résultats", 1, 50, st.session_state['next_day'])
    f_res = st.file_uploader("Scan Résultats", type=['jpg','png','jpeg'])
    if f_res:
        img = Image.open(f_res); w, hi = img.size; mid = w/2
        raw = reader.readtext(f_res.getvalue(), detail=1); raw.sort(key=lambda x: x[0][0][1])
        tms = [t for t in [{"n": engine.clean_team(txt), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, txt, p) in raw] if t["n"] and hi*0.12 < t["y"] < hi*0.95]
        ancs = []
        for t in tms:
            if t["x"] < mid and (not ancs or abs(t["y"] - ancs[-1]["y"]) > 45): ancs.append(t)
        
        extracted = []
        for i, a in enumerate(ancs):
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

        with st.form("f_res_val"):
            res_val_data = []
            for i, r in enumerate(extracted):
                st.write(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2); fs = c1.text_input("Final", r['s'], key=f"sf{i}"); ms = c2.text_input("MT", r['mt'], key=f"sm{i}")
                bh = st.text_input("Dom", r['hm'], key=f"sbh{i}"); ba = st.text_input("Ext", r['am'], key=f"sba{i}")
                res_val_data.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":bh, "am":ba})
            
            if st.form_submit_button("✅ ENREGISTRER"):
                jk = f"Journée {j_res_input}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["res"] = res_val_data
                # Snapshot classement avec RANG
                df_snap = get_standings(st.session_state['history'][s_active], engine.teams_list)
                st.session_state['history'][s_active][jk]["rank"] = df_snap.to_dict(orient='records')
                save_db(st.session_state['history']); custom_notify("Enregistré et Classé !"); st.rerun()

# --- TAB 5 : HISTORIQUE ---
with tabs[4]:
    sorted_days = sorted(st.session_state['history'][s_active].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for jk in sorted_days:
        with st.expander(f"📅 {jk}"):
            d = st.session_state['history'][s_active][jk]
            h_tabs = st.tabs(["📋 Calendrier", "🎯 Pronostic", "⚽ Résultat", "📊 Classement"])
            
            with h_tabs[0]: 
                if d.get("cal"):
                    st.table(d["cal"])
                    # --- BOUTON PRÉDIRE (SIMULATION) ---
                    if st.button(f"🔮 Relancer la prédiction (Simulation)", key=f"pred_{jk}"):
                        new_pros = []
                        for m in d["cal"]:
                            sh = int((3.0 / m['o'][0]) + 0.4)
                            sa = int((3.0 / m['o'][2]) + 0.1)
                            new_pros.append({"m": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o']})
                        st.session_state['history'][s_active][jk]["pro"] = new_pros
                        save_db(st.session_state['history'])
                        st.success(f"Prédictions mises à jour pour la {jk} !")
                        st.rerun()
            
            with h_tabs[1]: st.table(d.get("pro", []))
            with h_tabs[2]: st.table(d.get("res", []))
            with h_tabs[3]: 
                if d.get("rank"): st.table(pd.DataFrame(d["rank"]))
                else: st.info("Pas de classement archivé.")

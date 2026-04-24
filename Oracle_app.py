import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image
import numpy as np
from moteur_IA import CerveauOracle  # On appelle notre nouveau cerveau

# Initialiser le cerveau
oracle_brain = CerveauOracle()

# Configuration
st.set_page_config(page_title="Oracle Mahita V30", layout="wide")

# --- STYLE CSS : ORACLE MAHITA & NOTIFICATIONS ---
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 25px;
        border: 5px solid #7FFFD4;
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
    .prono-safe { border-left: 5px solid #00FF00; padding: 10px; background: rgba(0, 255, 0, 0.1); margin-bottom: 10px; border-radius: 5px; }
    .prono-risque { border-left: 5px solid #FFA500; padding: 10px; background: rgba(255, 165, 0, 0.1); margin-bottom: 10px; border-radius: 5px; }
    .prono-fun { border-left: 5px solid #FF4B4B; padding: 10px; background: rgba(255, 75, 75, 0.1); margin-bottom: 10px; border-radius: 5px; }
    .alerte-oracle { color: #FFD700; font-size: 0.85em; font-style: italic; margin-top: 5px; }
    
    .stSelectbox div[data-baseweb="select"] { border-color: #7FFFD4 !important; }
    .next-day-box { text-align: center; color: #7FFFD4; font-weight: bold; font-size: 1.2em; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

def custom_notify(text):
    msg = f"""<div style="padding: 15px; border: 3px solid #00FF00; border-radius: 10px; background-color: #0E1117; color: #FFFFFF; text-align: center; font-weight: 900; box-shadow: 0px 0px 20px #00FF00; margin: 15px 0px; font-size: 1.3em; text-transform: uppercase; -webkit-text-stroke: 1px #00FF00;">{text}</div>"""
    st.markdown(msg, unsafe_allow_html=True)

# --- CALCUL CLASSEMENT ---
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
    df = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Équipe'})
    for t in stats: df.loc[df['Équipe'] == t, 'Diff'] = stats[t]['BP'] - stats[t]['BC']
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

# --- ENGINE OCR ---
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

col_l, col_m, col_r = st.columns([1, 1, 1])
with col_m:
    saisons = list(st.session_state['history'].keys())
    s_active = st.selectbox("Saison", saisons, label_visibility="collapsed")
    st.session_state['s_active'] = s_active
    
    days = [int(re.search(r'\d+', k).group()) for k in st.session_state['history'][s_active].keys() if st.session_state['history'][s_active][k].get("res")]
    next_j = max(days) + 1 if days else 1
    st.markdown(f'<div class="next-day-box">PROCHAINE ÉTAPE : J-{next_j}</div>', unsafe_allow_html=True)

# --- NAVIGATION ---
tabs = st.tabs(["🏆 CLASSEMENT", "📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️ GESTION", "📊 PERFORMANCE & RATING"])

# --- TAB 0 : CLASSEMENT ---
with tabs[0]:
    current_standings = get_standings(st.session_state['history'][s_active], engine.teams_list)
    st.table(current_standings)

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_cal = st.number_input("Journée", 1, 50, next_j)
    f_cal = st.file_uploader("📸 Sélectionner le Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    
    if f_cal:
        image_bytes = f_cal.getvalue()
        res = reader.readtext(image_bytes, detail=0)
        t_f, o_f = [], []
        for t in res:
            n = engine.clean_team(t); 
            if n: t_f.append(n)
            for val in re.findall(r"\d+[\.,]\d+", t): o_f.append(float(val.replace(',', '.')))
        
        st.session_state['tmp_cal'] = []
        for i in range(10):
            h = t_f[i*2] if len(t_f)>i*2 else "Inconnu"
            a = t_f[i*2+1] if len(t_f)>i*2+1 else "Inconnu"
            o = o_f[i*3:i*3+3]
            st.session_state['tmp_cal'].append({'h': h, 'a': a, 'o': [o[0] if len(o)>0 else 1.0, o[1] if len(o)>1 else 1.0, o[2] if len(o)>2 else 1.0]})

    if 'tmp_cal' in st.session_state:
        with st.form("form_cal"):
            final_c = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                final_c.append({'h':th, 'a':ta, 'o':[o1.number_input("C1", value=m['o'][0], key=f"o1_{i}"), ox.number_input("CX", value=m['o'][1], key=f"ox_{i}"), o2.number_input("C2", value=m['o'][2], key=f"o2_{i}")]})
            
            if st.form_submit_button("🔥 VALIDER & ENREGISTRER"):
                jk = f"Journée {j_cal}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["cal"] = final_c
                # Le "pro" est maintenant calculé par le moteur IA
                st.session_state['history'][s_active][jk]["pro"] = [{"m": f"{m['h']} {int((3.0/m['o'][0])+0.4)}:{int((3.0/m['o'][2])+0.1)} {m['a']}", "c": m['o']} for m in final_c]
                st.session_state['current_ready'] = final_c
                st.session_state['current_j_num'] = j_cal # On stocke la journée pour le cerveau
                save_db(st.session_state['history'])
                custom_notify("Calendrier enregistré !")

# --- TAB 2 : PRONOS & TICKETS (RECTIFIÉ AVEC LE CERVEAU 1) ---
with tabs[2]:
    if 'current_ready' in st.session_state:
        safe_d, risque_d, fun_d = [], [], []
        j_num = st.session_state.get('current_j_num', 1)
        standings = get_standings(st.session_state['history'][s_active], engine.teams_list)

        for m in st.session_state['current_ready']:
            # --- APPEL AU CERVEAU ORACLE (ÉTAPE 2) ---
            # On récupère les rangs pour la Loi de Survie
            r_dom = standings[standings['Équipe'] == m['h']]['Rang'].values[0] if m['h'] in standings['Équipe'].values else 10
            r_ext = standings[standings['Équipe'] == m['a']]['Rang'].values[0] if m['a'] in standings['Équipe'].values else 10
            
            analyse = oracle_brain.analyser_match(
                equipe_dom=m['h'], equipe_ext=m['a'], cotes=m['o'], 
                journee=j_num, serie_dom=0, serie_ext=0, rang_dom=r_dom, rang_ext=r_ext
            )
            
            score_txt = f"{int((3.0/m['o'][0])+0.4)} : {int((3.0/m['o'][2])+0.1)}"
            
            # Affichage de l'analyse experte
            with st.container():
                st.markdown(f"⚽ **{m['h']} {score_txt} {m['a']}**")
                for alerte in analyse['alertes']:
                    st.markdown(f"<div class='alerte-oracle'>{alerte}</div>", unsafe_allow_html=True)
            
            # Distribution dans les tickets selon la Confiance du Cerveau
            item = {"txt": analyse['choix_expert'], "cote": max(m['o']), "match": f"{m['h']} vs {m['a']}"}
            if "BANKER" in analyse['confiance']: safe_d.append(item)
            elif "RISQUE" in analyse['confiance']: risque_d.append(item)
            else: fun_d.append(item)

        st.divider()
        c1, c2, c3 = st.columns(3)
        def show_ticket_with_style(col, title, css_class, data):
            with col:
                st.markdown(f"### {title}")
                if not data: st.write("Pas de match."); return
                total_cote = 1.0; calc_string = ""
                for i, x in enumerate(data[:3]):
                    st.markdown(f"""<div class="{css_class}"><b>{x['match']}</b><br>{x['txt']}</div>""", unsafe_allow_html=True)
                    total_cote *= 1.5 # Estimation simplifiée pour le style
                st.info(f"⚡ Analyse Oracle : **{title}**")

        show_ticket_with_style(c1, "🟢 TICKET SAFE", "prono-safe", safe_d)
        show_ticket_with_style(c2, "🟡 TICKET RISQUE", "prono-risque", risque_d)
        show_ticket_with_style(c3, "🔴 TICKET FUN", "prono-fun", fun_d)
    else:
        st.info("Veuillez d'abord valider un calendrier.")

# --- TAB 3 : RÉSULTATS ---
with tabs[3]:
    j_res = st.number_input("Journée Résultat", 1, 50, next_j)
    f_res = st.file_uploader("📸 Sélectionner les Résultats", type=['jpg','png','jpeg'], key="up_res")
    if f_res:
        img = Image.open(f_res); w, hi = img.size; mid = w/2
        raw = reader.readtext(f_res.getvalue(), detail=1); raw.sort(key=lambda x: x[0][0][1])
        tms = [t for t in [{"n": engine.clean_team(tx), "y": b[0][1], "x": (b[0][0]+b[1][0])/2} for (b, tx, p) in raw] if t["n"] and hi*0.12 < t["y"] < hi*0.95]
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
            if inf["a"] != "Inconnu": extracted.append(inf)
        
        with st.form("form_res"):
            val_r = []
            for i, r in enumerate(extracted):
                st.markdown(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Final", r['s'], key=f"rs_{i}")
                ms = c2.text_input("MT", r['mt'], key=f"rm_{i}")
                val_r.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":"", "am":""})
            if st.form_submit_button("✅ ENREGISTRER LES RÉSULTATS"):
                jk = f"Journée {j_res}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["res"] = val_r
                st.session_state['history'][s_active][jk]["rank"] = get_standings(st.session_state['history'][s_active], engine.teams_list).to_dict(orient='records')
                save_db(st.session_state['history'])
                custom_notify("Résultats enregistrés !")

# --- TAB 4 : HISTORIQUE ---
with tabs[4]:
    sorted_j = sorted(st.session_state['history'][s_active].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for jk in sorted_j:
        with st.expander(f"📅 {jk}"):
            d = st.session_state['history'][s_active][jk]
            h_tabs = st.tabs(["📋 Calendrier", "🎯 Prono", "⚽ Résultat", "📊 Classement"])
            with h_tabs[0]: 
                st.table(d.get("cal", []))
                if d.get("cal") and st.button(f"🔮 Prédire", key=f"sim_{jk}"):
                    st.session_state['current_ready'] = d["cal"]
                    st.session_state['current_j_num'] = int(re.search(r'\d+', jk).group())
                    st.rerun()
            with h_tabs[1]: st.table(d.get("pro", []))
            with h_tabs[2]: st.table(d.get("res", []))
            with h_tabs[3]: 
                if d.get("rank"): st.table(pd.DataFrame(d["rank"]))

# --- TAB 5 : GESTION ---
with tabs[5]:
    ns = st.text_input("Nom de la nouvelle Saison")
    if st.button("➕ Créer la Saison"): 
        if ns: st.session_state['history'][ns] = {}; save_db(st.session_state['history']); st.rerun()
    st.divider()
    if st.session_state['history']:
        st.download_button("📥 EXPORTER BACKUP", data=json.dumps(st.session_state['history'], indent=4), file_name="oracle_backup.json")

# --- TAB 6 : PERFORMANCE & RATING ---
with tabs[6]:
    st.markdown("<div class='main-header'><h1 class='header-title'>📊 RATING & PERFORMANCE</h1></div>", unsafe_allow_html=True)
    stats_perf = oracle_brain.calculer_performance_globale(st.session_state['history'][s_active])
    if stats_perf["total_matchs"] == 0:
        st.info("ℹ️ L'Oracle a besoin de résultats pour calculer son rating.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matchs", stats_perf["total_matchs"])
        c2.metric("Réussite 1N2", f"{stats_perf['taux_1n2']:.1f}%")
        c3.metric("Scores Exacts", stats_perf["scores_exacts"])
        c4.metric("Points/Match", f"{stats_perf['moyenne_points']:.2f}")
        st.divider()
        rating = stats_perf["rating_general"]
        color = "green" if rating >= 80 else "orange" if rating >= 50 else "red"
        st.progress(rating / 100)
        st.markdown(f"**Score Global : <span style='color:{color}; font-size:25px;'>{rating:.1f} / 100</span>**", unsafe_allow_html=True)

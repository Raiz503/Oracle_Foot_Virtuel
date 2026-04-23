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
    /* Styles pour les Pronostics (Tickets) */
    .prono-safe { border-left: 5px solid #00FF00; padding: 10px; background: rgba(0, 255, 0, 0.1); margin-bottom: 10px; border-radius: 5px; }
    .prono-risque { border-left: 5px solid #FFA500; padding: 10px; background: rgba(255, 165, 0, 0.1); margin-bottom: 10px; border-radius: 5px; }
    .prono-fun { border-left: 5px solid #FF4B4B; padding: 10px; background: rgba(255, 75, 75, 0.1); margin-bottom: 10px; border-radius: 5px; }
    
    .stSelectbox div[data-baseweb="select"] { border-color: #7FFFD4 !important; }
    .next-day-box { text-align: center; color: #7FFFD4; font-weight: bold; font-size: 1.2em; margin-top: 10px; }
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
# Définition de 6 onglets (Index 0 à 5)
tabs = st.tabs(["🏆 CLASSEMENT", "📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️ GESTION"])

# --- TAB 0 : CLASSEMENT ---
with tabs[0]:
    st.table(get_standings(st.session_state['history'][s_active], engine.teams_list))

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_cal = st.number_input("Journée", 1, 50, next_j)
    f_cal = st.file_uploader("📸 Sélectionner le Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    
    if f_cal:
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(f_cal, caption="📄 Image source (Calendrier)", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        image_bytes = f_cal.getvalue()
        res = reader.readtext(image_bytes, detail=0)
        
        t_f, o_f = [], []
        for t in res:
            n = engine.clean_team(t)
            if n: t_f.append(n)
            for val in re.findall(r"\d+[\.,]\d+", t): o_f.append(float(val.replace(',', '.')))
        
        st.session_state['tmp_cal'] = []
        for i in range(10):
            h = t_f[i*2] if len(t_f)>i*2 else "Inconnu"
            a = t_f[i*2+1] if len(t_f)>i*2+1 else "Inconnu"
            o = o_f[i*3:i*3+3]
            st.session_state['tmp_cal'].append({'h': h, 'a': a, 'o': [o[0] if len(o)>0 else 1.0, o[1] if len(o)>1 else 1.0, o[2] if len(o)>2 else 1.0]})

    if 'tmp_cal' in st.session_state:
        st.info("💡 Vérifie les données ci-dessous avec l'image avant de valider.")
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
                st.session_state['history'][s_active][jk]["pro"] = [{"m": f"{m['h']} {int((3.0/max(0.1, m['o'][0]))+0.4)}:{int((3.0/max(0.1, m['o'][2]))+0.1)} {m['a']}", "c": m['o']} for m in final_c]
                save_db(st.session_state['history'])
                # Correction : On utilise 'current_ready' pour que l'onglet PRONOS le reconnaisse
                st.session_state['current_ready'] = final_c 
                custom_notify("Analyse terminée et enregistrée !")

# --- TAB 2 : PRONOS & TICKETS ---
with tabs[2]:
    if 'current_ready' in st.session_state:
        safe_d, risque_d, fun_d = [], [], []
        for m in st.session_state['current_ready']:
            sh = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0
            sa = int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            score_txt = f"{sh} : {sa}"
            
            st.write(f"⚽ **{m['h']} {score_txt} {m['a']}**")
            
            if m['o'][0] < 1.7: safe_d.append({"txt": f"{m['h']} Gagne", "cote": m['o'][0], "match": f"{m['h']} {score_txt} {m['a']}"})
            elif m['o'][2] < 1.7: safe_d.append({"txt": f"{m['a']} Gagne", "cote": m['o'][2], "match": f"{m['h']} {score_txt} {m['a']}"})
            
            if 1.7 <= m['o'][0] <= 3.0: risque_d.append({"txt": f"{m['h']} ({score_txt})", "cote": m['o'][0], "match": f"{m['h']} vs {m['a']}"})
            elif 1.7 <= m['o'][2] <= 3.0: risque_d.append({"txt": f"{m['a']} ({score_txt})", "cote": m['o'][2], "match": f"{m['h']} vs {m['a']}"})
            
            if m['o'][1] > 3.4: fun_d.append({"txt": "Match Nul", "cote": m['o'][1], "match": f"{m['h']} vs {m['a']}"})
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        
        def show_ticket_with_style(col, title, css_class, data):
            with col:
                st.markdown(f"### {title}")
                if not data: 
                    st.write("Pas de match.")
                    return
                total_cote = 1.0
                calc_string = ""
                for i, x in enumerate(data[:3]):
                    st.markdown(f"""<div class="{css_class}"><b>{x['match']}</b><br>{x['txt']} : <b>{x['cote']}</b></div>""", unsafe_allow_html=True)
                    total_cote *= x['cote']
                    calc_string += str(x['cote']) + (" x " if i < len(data[:3])-1 else "")
                st.info(f"🧮 {calc_string} = **{round(total_cote, 2)}**")

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
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(f_res, caption="⚽ Image source (Résultats)", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
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
                    elif re.search(r"\d+", tx) and not re.search(r"^\d[:\-]\d$", tx):
                        if cx < mid: inf["hm"] += f" {tx}'"
                        else: inf["am"] += f" {tx}'"
            if inf["a"] != "Inconnu": extracted.append(inf)
        
        with st.form("form_res"):
            val_r = []
            for i, r in enumerate(extracted):
                st.markdown(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Final", r['s'], key=f"rs_{i}")
                ms = c2.text_input("MT", r['mt'], key=f"rm_{i}")
                bh = st.text_input("Buteurs Dom", r['hm'], key=f"rbh_{i}")
                ba = st.text_input("Buteurs Ext", r['am'], key=f"rba_{i}")
                val_r.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":bh, "am":ba})
            
            if st.form_submit_button("✅ ENREGISTRER LES RÉSULTATS"):
                jk = f"Journée {j_res}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {"cal":[], "res":[], "pro":[], "rank":[]}
                st.session_state['history'][s_active][jk]["res"] = val_r
                df_snap = get_standings(st.session_state['history'][s_active], engine.teams_list)
                st.session_state['history'][s_active][jk]["rank"] = df_snap.to_dict(orient='records')
                save_db(st.session_state['history'])
                custom_notify("Résultats et classement enregistrés !")

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
                    st.rerun()
            with h_tabs[1]: st.table(d.get("pro", []))
            with h_tabs[2]: st.table(d.get("res", []))
            with h_tabs[3]: 
                if d.get("rank"): st.table(pd.DataFrame(d["rank"]))

# --- TAB 5 : GESTION (FUSIONNÉ) ---
with tabs[5]:
    st.subheader("📁 Gestion des Saisons")
    ns = st.text_input("Nom de la nouvelle Saison")
    if st.button("➕ Créer la Saison"): 
        if ns: 
            st.session_state['history'][ns] = {}
            save_db(st.session_state['history'])
            st.success(f"Saison {ns} créée !")
            st.rerun()

    st.divider()
    st.subheader("💾 Sauvegarde & Import")
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state['history']:
            json_data = json.dumps(st.session_state['history'], indent=4)
            st.download_button("📥 EXPORTER JSON (Backup)", data=json_data, file_name="oracle_backup.json")
    with c2:
        up = st.file_uploader("📤 IMPORTER JSON", type="json")
        if up:
            data_imported = json.load(up)
            st.session_state['history'].update(data_imported)
            save_db(st.session_state['history'])
            st.success("Données fusionnées avec succès !")
            
# --- NOUVEL ONGLET : 📊 PERFORMANCE & RATING ---
# Note : Ajustez l'index de tabs[...] selon votre structure (ex: tabs[5])
with tabs[6]:
    st.markdown("<div class='main-header'><h1 class='header-title'>📊 RATING & PERFORMANCE</h1></div>", unsafe_allow_html=True)
    
    # Récupération des statistiques via le moteur fusionné
    # s_active est le nom de la saison sélectionnée dans votre app
    stats_perf = oracle_brain.calculer_performance_globale(st.session_state['history'][s_active])
    
    if stats_perf["total_matchs"] == 0:
        st.info("ℹ️ L'Oracle a besoin de résultats enregistrés pour calculer son rating. Allez dans l'onglet '⚽ RÉSULTATS' pour commencer.")
    else:
        # --- LIGNE 1 : LES MÉTRIQUES CLÉS ---
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Matchs", stats_perf["total_matchs"])
        with col2:
            # On affiche le taux de réussite 1N2
            st.metric("Réussite 1N2", f"{stats_perf['taux_1n2']:.1f}%")
        with col3:
            # On affiche le nombre de scores exacts trouvés
            st.metric("Scores Exacts", stats_perf["scores_exacts"], help="Nombre de fois où le score final était identique à la prédiction.")
        with col4:
            # La moyenne de points par match (Système Oracle)
            st.metric("Points / Match", f"{stats_perf['moyenne_points']:.2f}")

        st.markdown("---")

        # --- LIGNE 2 : LE SCORE DE PRÉCISION (RATING) ---
        c_left, c_right = st.columns([2, 1])
        
        with c_left:
            st.subheader("🎯 Indice de Précision Mathématique")
            rating = stats_perf["rating_general"]
            
            # Affichage d'une barre de progression colorée
            if rating >= 80: color = "green"
            elif rating >= 50: color = "orange"
            else: color = "red"
            
            st.progress(rating / 100)
            st.markdown(f"**Score Global : <span style='color:{color}; font-size:25px;'>{rating:.1f} / 100</span>**", unsafe_allow_html=True)
            st.caption("Cet indice calcule la distance entre vos prédictions et les scores réels. Plus il est proche de 100, plus l'IA est 'chirurgicale'.")

        with c_right:
            st.subheader("💡 Analyse IA")
            if rating >= 75:
                st.success("L'Oracle est actuellement très précis. Les stratégies du Cerveau 1 sont bien calibrées pour cette saison.")
            elif rating >= 50:
                st.warning("Précision moyenne. L'IA suggère d'affiner les 'Conditions de Cotes' dans le Cerveau 2.")
            else:
                st.error("Précision faible. Attention aux surprises (MSS) ou au relâchement des favoris non détectés.")

        # --- LIGNE 3 : RÉCAPITULATIF DES POINTS ---
        st.info(f"🏆 **Points Totaux Oracle : {stats_perf['points_oracle']} pts** (Calculés sur : 3pts/Score Exact + 1pt/Bonne Tendance)")

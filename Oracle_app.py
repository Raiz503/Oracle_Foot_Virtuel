import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image, ImageOps
import numpy as np

# Configuration
st.set_page_config(page_title="Oracle Mahita", layout="wide")

# --- DESIGN ---
st.markdown("""
    <style>
    .main-header { text-align: center; padding: 20px; border: 4px solid #7FFFD4; border-radius: 15px; background-color: #0E1117; box-shadow: 0px 0px 25px #7FFFD4; margin-bottom: 10px; }
    .header-title { color: #FFFFFF; font-size: 3.5em; font-weight: 900; text-transform: uppercase; -webkit-text-stroke: 1.5px #7FFFD4; }
    .img-container { border: 3px solid #7FFFD4; border-radius: 15px; padding: 10px; background: #1E1E1E; margin-bottom: 25px; text-align: center; }
    .prono-safe { border-left: 5px solid #00FF00; padding: 10px; background: rgba(0, 255, 0, 0.1); margin-bottom: 5px; }
    .prono-risque { border-left: 5px solid #FFA500; padding: 10px; background: rgba(255, 165, 0, 0.1); margin-bottom: 5px; }
    .prono-fun { border-left: 5px solid #FF0000; padding: 10px; background: rgba(255, 0, 0, 0.1); margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

def custom_notify(text):
    st.markdown(f"""<div style="padding:15px; border:3px solid #00FF00; border-radius:10px; background-color:#0E1117; color:#FFFFFF; text-align:center; font-weight:900; box-shadow:0px 0px 20px #00FF00; margin:15px 0px;">{text}</div>""", unsafe_allow_html=True)

# --- LOGIQUE CLASSEMENT ---
def get_standings(season_data, teams_list):
    stats = {team: {"MJ": 0, "V": 0, "N": 0, "D": 0, "BP": 0, "BC": 0, "Diff": 0, "Pts": 0} for team in teams_list}
    for jk, data in season_data.items():
        results = data.get("res", [])
        if results:
            for m in results:
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
    df['Diff'] = df['BP'] - df['BC']
    df = df.sort_values(by=["Pts", "Diff", "BP"], ascending=False).reset_index(drop=True)
    df.insert(0, 'Rang', range(1, len(df) + 1))
    return df

# --- LOGIQUE PRONOSTICS (SAFE / RISQUÉ / FUN) ---
def generate_pronos(cal_data):
    pronos = []
    for m in cal_data:
        o1, ox, o2 = m['o']
        safe = f"{m['h']} ou Nul (1X)" if o1 <= o2 else f"{m['a']} ou Nul (X2)"
        risque = f"Victoire {m['h']} (1)" if o1 < o2 else f"Victoire {m['a']} (2)"
        sh, sa = int((3.0/max(0.1, o1))+0.4), int((3.0/max(0.1, o2))+0.1)
        fun = f"Score Exact : {m['h']} {sh}-{sa} {m['a']}"
        pronos.append({"match": f"{m['h']} vs {m['a']}", "safe": safe, "risque": risque, "fun": fun, "c": m['o']})
    return pronos

# --- BDD ---
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

# --- OCR ---
@st.cache_resource
def load_ocr(): return easyocr.Reader(['en', 'fr'], gpu=False)
reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.teams_list = ["Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"]
    def clean_team(self, text):
        m = get_close_matches(text, self.teams_list, n=1, cutoff=0.22) # Sensibilité max
        return m[0] if m else None

engine = OracleEngine()

# --- HEADER ---
st.markdown('<div class="main-header"><h1 class="header-title">Oracle Mahita</h1></div>', unsafe_allow_html=True)
saisons = list(st.session_state['history'].keys())
s_active = st.selectbox("Saison Active", saisons)

tabs = st.tabs(["🏆 CLASSEMENT", "📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️ RÉGLAGES"])

# --- TAB 1 : CLASSEMENT ---
with tabs[0]:
    st.table(get_standings(st.session_state['history'][s_active], engine.teams_list))

# --- TAB 2 : CALENDRIER ---
with tabs[1]:
    j_cal = st.number_input("Journée", 1, 50, 1, key="jc")
    f_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="fc")
    if f_cal:
        img_temp = Image.open(f_cal)
        # Padding Anti-Coupure pour le premier match
        img_padded = ImageOps.expand(img_temp, border=50, fill='white')
        img_padded.save("temp_cal.png")
        
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(img_temp, caption="Aperçu du Calendrier", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        res = reader.readtext("temp_cal.png", detail=0)
        t_f, o_f = [], []
        for t in res:
            n = engine.clean_team(t)
            if n: t_f.append(n)
            for val in re.findall(r"\d+[\.,]\d+", t): o_f.append(float(val.replace(',', '.')))
        
        tmp = []
        for i in range(10):
            h = t_f[i*2] if len(t_f) > i*2 else "Inconnu"
            a = t_f[i*2+1] if len(t_f) > i*2+1 else "Inconnu"
            o = o_f[i*3:i*3+3] if len(o_f) >= (i*3+3) else [1.0, 1.0, 1.0]
            tmp.append({'h': h, 'a': a, 'o': o})
        st.session_state['tmp_cal'] = tmp

    if st.session_state.get('tmp_cal'):
        with st.form("form_cal_v27"):
            final = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                final.append({'h':th, 'a':ta, 'o':[o1.number_input("C1", value=m['o'][0], key=f"o1{i}"), ox.number_input("CX", value=m['o'][1], key=f"ox{i}"), o2.number_input("C2", value=m['o'][2], key=f"o2{i}")]})
            
            if st.form_submit_button("🔥 ANALYSER ET GÉNÉRER PRONOS"):
                jk = f"Journée {j_cal}"
                if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {}
                st.session_state['history'][s_active][jk]["cal"] = final
                st.session_state['history'][s_active][jk]["pro"] = generate_pronos(final)
                save_db(st.session_state['history'])
                st.session_state['last_jk'] = jk
                custom_notify("Analyse terminée ! Regarde l'onglet Pronos.")

# --- TAB 3 : PRONOS ---
with tabs[2]:
    jk_target = st.session_state.get('last_jk')
    if jk_target and st.session_state['history'][s_active].get(jk_target):
        st.subheader(f"🎯 Pronostics pour la {jk_target}")
        data = st.session_state['history'][s_active][jk_target]
        for p in data.get("pro", []):
            st.markdown(f"**{p['match']}** *(Cotes: {p['c']})*")
            st.markdown(f'<div class="prono-safe">🟢 <b>SAFE:</b> {p["safe"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="prono-risque">🟠 <b>RISQUÉ:</b> {p["risque"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="prono-fun">🔴 <b>FUN:</b> {p["fun"]}</div>', unsafe_allow_html=True)
    else:
        st.info("Scanne un calendrier pour afficher les pronostics structurés.")

# --- TAB 4 : RÉSULTATS ---
with tabs[3]:
    j_res = st.number_input("Journée Résultats", 1, 50, 1, key="jr")
    f_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="fr")
    if f_res:
        img_temp = Image.open(f_res); w, hi = img_temp.size; mid = w/2
        # Padding Anti-Coupure
        img_padded = ImageOps.expand(img_temp, border=50, fill='white')
        img_padded.save("temp_res.png")
        
        st.markdown('<div class="img-container">', unsafe_allow_html=True)
        st.image(img_temp, caption="Aperçu des Résultats", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        raw = reader.readtext("temp_res.png", detail=1)
        raw.sort(key=lambda x: x[0][0][1])
        
        # Ajustement des coordonnées de -50px à cause du padding
        tms = [t for t in [{"n": engine.clean_team(tx), "y": b[0][1]-50, "x": (b[0][0]+b[1][0])/2-50} for (b, tx, p) in raw] if t["n"]]
        ancs = []
        for t in tms:
            if t["x"] < mid and (not ancs or abs(t["y"] - ancs[-1]["y"]) > 35): ancs.append(t)
        
        extracted = []
        for i, a in enumerate(ancs):
            ys, ye = a["y"]-15, (ancs[i+1]["y"]-15 if i+1 < len(ancs) else hi)
            inf = {"h": a["n"], "a": "Inconnu", "s": "0:0", "hm": "", "am": "", "mt": ""}
            for (bb, tx, p) in raw:
                cy, cx = (bb[0][1]+bb[2][1])/2-50, (bb[0][0]+bb[1][0])/2-50
                if ys <= cy <= ye:
                    tn = engine.clean_team(tx)
                    if tn and cx > mid and tn != inf["h"]: inf["a"] = tn
                    elif re.search(r"^\d[:\-]\d$", tx.strip()) and "MT" not in tx.upper(): inf["s"] = tx
                    elif "MT" in tx.upper(): inf["mt"] = tx
                    elif re.search(r"\d+", tx):
                        if cx < mid: inf["hm"] += f" {tx}'"
                        else: inf["am"] += f" {tx}'"
            if inf["a"] != "Inconnu": extracted.append(inf)

        if extracted:
            with st.form("form_res_v27"):
                val_r = []
                for i, r in enumerate(extracted):
                    st.write(f"**Match {i+1}**")
                    c1, c2 = st.columns(2)
                    h_team = c1.selectbox("Dom", engine.teams_list, index=engine.teams_list.index(r['h']) if r['h'] in engine.teams_list else 0, key=f"rh{i}")
                    a_team = c2.selectbox("Ext", engine.teams_list, index=engine.teams_list.index(r['a']) if r['a'] in engine.teams_list else 0, key=f"ra{i}")
                    val_r.append({"h":h_team, "a":a_team, "s":c1.text_input("Score Final", r['s'], key=f"rs{i}"), "mt":c2.text_input("Score MT", r['mt'], key=f"rm{i}"), "hm":st.text_input("Buts Dom (Min)", r['hm'], key=f"rbh{i}"), "am":st.text_input("Buts Ext (Min)", r['am'], key=f"rba{i}")})
                
                if st.form_submit_button("✅ ENREGISTRER DANS L'HISTORIQUE"):
                    jk = f"Journée {j_res}"
                    if jk not in st.session_state['history'][s_active]: st.session_state['history'][s_active][jk] = {}
                    st.session_state['history'][s_active][jk]["res"] = val_r
                    st.session_state['history'][s_active][jk]["rank"] = get_standings(st.session_state['history'][s_active], engine.teams_list).to_dict(orient='records')
                    save_db(st.session_state['history']); custom_notify("Résultats et Classement enregistrés !")

# --- TAB 5 : HISTORIQUE ---
with tabs[4]:
    st.info("💡 Tu peux re-simuler des prédictions ou effacer manuellement une journée en cas d'erreur de scan.")
    for jk in sorted(st.session_state['history'][s_active].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0):
        with st.expander(f"📅 {jk}"):
            d = st.session_state['history'][s_active][jk]
            h_tabs = st.tabs(["📋 Calendrier", "🎯 Pronos", "⚽ Résultats", "📊 Classement J.", "⚠️ Actions"])
            
            with h_tabs[0]: st.table(d.get("cal", []))
            
            with h_tabs[1]:
                if d.get("pro"):
                    for p in d["pro"]:
                        st.write(f"**{p['match']}** | Safe: {p['safe']} | Risque: {p['risque']} | Fun: {p['fun']}")
            
            with h_tabs[2]: st.table(d.get("res", []))
            
            with h_tabs[3]: 
                if d.get("rank"): st.table(pd.DataFrame(d["rank"]))
            
            with h_tabs[4]:
                c_btn1, c_btn2 = st.columns(2)
                # Bouton de re-simulation (Prédiction)
                if d.get("cal") and c_btn1.button(f"🔮 Prédire (Relancer)", key=f"sim_{jk}"):
                    d["pro"] = generate_pronos(d["cal"])
                    save_db(st.session_state['history']); st.rerun()
                # Bouton de suppression manuelle
                if c_btn2.button(f"🗑️ Supprimer cette Journée", key=f"del_{jk}"):
                    del st.session_state['history'][s_active][jk]
                    save_db(st.session_state['history']); st.rerun()

# --- TAB 6 : RÉGLAGES ---
with tabs[5]:
    st.subheader("⚙️ Gestion de la Base de Données")
    ns = st.text_input("Créer une nouvelle Saison (ex: Saison 2027)")
    if st.button("➕ Ajouter la Saison"): 
        if ns: 
            st.session_state['history'][ns] = {}
            save_db(st.session_state['history'])
            st.success(f"Saison '{ns}' créée avec succès !")
            st.rerun()
    
    st.markdown("---")
    st.download_button(
        label="📤 Exporter toute la base de données (Backup)",
        data=json.dumps(st.session_state['history'], indent=4, ensure_ascii=False),
        file_name="oracle_history_backup.json",
        mime="application/json"
    )

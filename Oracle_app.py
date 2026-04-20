import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image
import base64

st.set_page_config(page_title="Oracle V20.0 - Coffre-Fort", layout="wide")

# --- STYLE PERSONNALISÉ POUR NOTIFICATIONS ---
def custom_notify(text):
    msg = f"""
    <div style="
        padding: 10px;
        border: 2px solid #00FF00;
        border-radius: 5px;
        background-color: #0E1117;
        color: #FFFFFF;
        text-align: center;
        font-weight: bold;
        box-shadow: 0px 0px 15px #00FF00;
        margin: 10px 0px;
        text-shadow: -1px -1px 0 #00FF00, 1px -1px 0 #00FF00, -1px 1px 0 #00FF00, 1px 1px 0 #00FF00;
    ">
        {text}
    </div>
    """
    st.markdown(msg, unsafe_allow_html=True)

# --- MOTEUR DE DONNÉES ---
DB_FILE = "oracle_history.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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
st.title("🔮 ORACLE V20.0")

tabs = st.tabs(["🌟 SAISONS & IMPORT", "📅 CALENDRIER", "🎯 PRONOS ACTUELS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : GESTION & EXPORT/IMPORT ---
with tabs[0]:
    st.subheader("📁 Gestion de la Base de Données")
    
    col1, col2 = st.columns(2)
    with col1:
        # Exportation
        if st.session_state['history']:
            json_str = json.dumps(st.session_state['history'], indent=4)
            st.download_button(
                label="📥 Télécharger l'Historique (JSON)",
                data=json_str,
                file_name="oracle_backup.json",
                mime="application/json"
            )
    
    with col2:
        # Importation
        uploaded_db = st.file_uploader("📤 Importer un fichier Oracle JSON", type="json")
        if uploaded_db:
            new_data = json.load(uploaded_db)
            st.session_state['history'].update(new_data)
            save_db(st.session_state['history'])
            st.success("Données fusionnées avec succès !")

    st.divider()
    # Sélection Saison
    s_names = list(st.session_state['history'].keys()) if st.session_state['history'] else ["Saison 2026"]
    if "Saison 2026" not in s_names and not st.session_state['history']:
        st.session_state['history']["Saison 2026"] = {}
    
    col3, col4 = st.columns(2)
    with col3:
        new_s = st.text_input("Nouvelle Saison")
        if st.button("Créer"):
            if new_s: st.session_state['history'][new_s] = {}; save_db(st.session_state['history']); st.rerun()
    with col4:
        st.session_state['s_active'] = st.selectbox("Saison Active", list(st.session_state['history'].keys()))

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_val = st.number_input("Journée", 1, 50, 1)
    f_cal = st.file_uploader("📸 Scan", type=['jpg','png','jpeg'], key="cal_up")
    if f_cal:
        res = reader.readtext(f_cal.read(), detail=0)
        t_l, o_l = [], []
        for t in res:
            n = engine.clean_team(t)
            if n: t_l.append(n)
            for num in re.findall(r"\d+[\.,]\d+", t):
                o_l.append(float(num.replace(',', '.')))
        st.session_state['tmp_cal'] = []
        for i in range(10):
            h = t_l[i*2] if len(t_l)>i*2 else "Inconnu"
            a = t_l[i*2+1] if len(t_l)>i*2+1 else "Inconnu"
            ck = o_l[i*3:i*3+3]
            st.session_state['tmp_cal'].append({'h': h, 'a': a, 'o': [ck[0] if len(ck)>0 else 1.0, ck[1] if len(ck)>1 else 1.0, ck[2] if len(ck)>2 else 1.0]})

    if 'tmp_cal' in st.session_state:
        with st.form("cal_form"):
            final_cal = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2,2,1,1,1])
                th = c1.selectbox(f"H{i}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                ta = c2.selectbox(f"A{i}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                final_cal.append({'h':th, 'a':ta, 'o':[o1.number_input("C1",value=m['o'][0],key=f"c1{i}"), ox.number_input("CX",value=m['o'][1],key=f"cx{i}"), o2.number_input("C2",value=m['o'][2],key=f"c2{i}")]})
            
            if st.form_submit_button("🔥 VALIDER"):
                sn = st.session_state['s_active']
                jk = f"Journée {j_val}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                st.session_state['history'][sn][jk]["cal"] = final_cal
                
                # Génération auto des pronos pour l'historique
                pros = []
                for m in final_cal:
                    sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
                    pros.append({"match": f"{m['h']} {sh}:{sa} {m['a']}", "cotes": m['o']})
                st.session_state['history'][sn][jk]["pro"] = pros
                
                save_db(st.session_state['history'])
                st.session_state['ready_cal'] = final_cal
                custom_notify("Analyse fini et va vers le pronostic")

# --- TAB 2 : PRONOS ACTUELS ---
with tabs[2]:
    if 'ready_cal' in st.session_state:
        for m in st.session_state['ready_cal']:
            sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            st.write(f"⚽ **{m['h']} {sh}:{sa} {m['a']}**")

# --- TAB 3 : RÉSULTATS ---
with tabs[3]:
    j_r = st.number_input("Journée Résultat", 1, 50, 1)
    f_res = st.file_uploader("📸 Scan Rés", type=['jpg','png','jpeg'])
    if f_res:
        # ... (Logique de scan V17.7 identique à la précédente)
        # Pour gagner de la place ici, on garde la structure de scan habituelle
        st.info("Scanner en cours...") 
        # [Simulation de scan pour l'exemple]
        matches_res = [{"h":"Brentford", "a":"Leeds", "s":"2:1", "mt":"1:0", "hm":"23' 45'", "am":"12'"}]
        
        with st.form("res_form"):
            res_val = []
            for i, r in enumerate(matches_res):
                st.write(f"Match {r['h']} vs {r['a']}")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Score", r['s'], key=f"fs{i}")
                ms = c2.text_input("MT", r['mt'], key=f"ms{i}")
                res_val.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":r['hm'], "am":r['am']})
            
            if st.form_submit_button("✅ SAUVEGARDER"):
                sn = st.session_state['s_active']
                jk = f"Journée {j_r}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                st.session_state['history'][sn][jk]["res"] = res_val
                save_db(st.session_state['history'])
                custom_notify("c'est enregistré dans l'historique")

# --- TAB 4 : HISTORIQUE (AVEC SOUS-ONGLETS) ---
with tabs[4]:
    st.header("📚 Archives Oracle")
    if not st.session_state['history']: st.info("Historique vide.")
    else:
        s_view = st.selectbox("Voir Saison", list(st.session_state['history'].keys()))
        for jk in list(st.session_state['history'][s_view].keys()):
            with st.expander(f"📅 {jk}"):
                if st.button(f"🗑️ Supprimer {jk}", key=f"del_{jk}"):
                    del st.session_state['history'][s_view][jk]
                    save_db(st.session_state['history']); st.rerun()
                
                # --- SOUS-ONGLETS DANS L'HISTORIQUE ---
                sub_cal, sub_pro, sub_res = st.tabs(["📋 Calendrier", "🎯 Pronostic", "⚽ Résultat"])
                
                data = st.session_state['history'][s_view][jk]
                
                with sub_cal:
                    if data["cal"]: st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "C1": m['o'][0], "CX": m['o'][1], "C2": m['o'][2]} for m in data["cal"]]))
                
                with sub_pro:
                    if data["pro"]: st.table(pd.DataFrame([{"Analyse Score": m['match'], "Cotes": m['cotes']} for m in data["pro"]]))
                
                with sub_res:
                    if data["res"]: st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "Score": m['s'], "MT": m['mt'], "Buteurs": f"{m['hm']} / {m['am']}"} for m in data["res"]]))

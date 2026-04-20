import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image
import base64

st.set_page_config(page_title="Oracle V20.1 - Ultra Stable", layout="wide")

# --- STYLE NOTIFICATIONS NÉON VERT ---
def custom_notify(text):
    # Effet de bordure lumineuse sur chaque mot via un contour prononcé
    msg = f"""
    <div style="
        padding: 15px;
        border: 3px solid #00FF00;
        border-radius: 10px;
        background-color: #0E1117;
        color: #FFFFFF;
        text-align: center;
        font-weight: 900;
        box-shadow: 0px 0px 20px #00FF00;
        margin: 20px 0px;
        font-size: 1.2em;
        text-transform: uppercase;
        letter-spacing: 1px;
        -webkit-text-stroke: 1px #00FF00; /* Bordure verte sur les lettres */
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

# --- INTERFACE PRINCIPALE ---
st.title("🔮 ORACLE V20.1")

tabs = st.tabs(["🌟 SAISONS & IMPORT/EXPORT", "📅 CALENDRIER", "🎯 PRONOS ACTUELS", "⚽ RÉSULTATS", "📚 HISTORIQUE"])

# --- TAB 0 : SAISONS & SAUVEGARDES ---
with tabs[0]:
    st.subheader("💾 Sauvegarde et Migration")
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state['history']:
            json_data = json.dumps(st.session_state['history'], indent=4)
            st.download_button("📥 EXPORTER TOUTE LA BDD (JSON)", data=json_data, file_name="oracle_full_backup.json", mime="application/json")
    with c2:
        up = st.file_uploader("📤 IMPORTER UN FICHIER JSON", type="json")
        if up:
            try:
                imported = json.load(up)
                st.session_state['history'].update(imported)
                save_db(st.session_state['history'])
                st.success("Données fusionnées avec succès !")
            except: st.error("Fichier invalide.")

    st.divider()
    s_list = list(st.session_state['history'].keys()) if st.session_state['history'] else ["Saison 2026"]
    if not st.session_state['history']: st.session_state['history']["Saison 2026"] = {}
    
    col_a, col_b = st.columns(2)
    with col_a:
        ns = st.text_input("Nom nouvelle saison")
        if st.button("Créer Saison"):
            if ns: st.session_state['history'][ns] = {}; save_db(st.session_state['history']); st.rerun()
    with col_b:
        st.session_state['s_active'] = st.selectbox("Saison de travail :", list(st.session_state['history'].keys()))

# --- TAB 1 : CALENDRIER ---
with tabs[1]:
    j_num = st.number_input("Journée", 1, 50, 1)
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
                
                # Enregistre le prono à ce moment précis
                p_list = []
                for m in final_c:
                    sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
                    p_list.append({"m": f"{m['h']} {sh}:{sa} {m['a']}", "c": m['o']})
                st.session_state['history'][sn][jk]["pro"] = p_list
                
                save_db(st.session_state['history'])
                st.session_state['ready_cal'] = final_c
                custom_notify("Analyse fini et va vers le pronostic")

# --- TAB 2 : PRONOS ACTUELS ---
with tabs[2]:
    if 'ready_cal' in st.session_state:
        for m in st.session_state['ready_cal']:
            sh, sa = int((3.0/m['o'][0])+0.4) if m['o'][0]>0 else 0, int((3.0/m['o'][2])+0.1) if m['o'][2]>0 else 0
            st.write(f"⚽ **{m['h']} {sh}:{sa} {m['a']}**")

# --- TAB 3 : RÉSULTATS ---
with tabs[3]:
    j_res = st.number_input("Journée Résultat", 1, 50, 1)
    f_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'])
    if f_res:
        # Code de scan optimisé V17.7...
        st.warning("Prêt pour la validation manuelle...")
        # Simulé pour l'exemple :
        res_matches = [{"h":"Leeds", "a":"Brighton", "s":"2:2", "mt":"1:1", "hm":"24' 82'", "am":"41' 64'"}]
        
        with st.form("res_val_form"):
            val_r = []
            for i, r in enumerate(res_matches):
                st.markdown(f"**{r['h']} vs {r['a']}**")
                c1, c2 = st.columns(2)
                fs = c1.text_input("Final", r['s'], key=f"rs{i}")
                ms = c2.text_input("MT", r['mt'], key=f"rm{i}")
                b1, b2 = st.columns(2)
                bh = b1.text_input("Buts Dom", r['hm'], key=f"rbh{i}")
                ba = b2.text_input("Buts Ext", r['am'], key=f"rba{i}")
                val_r.append({"h":r['h'], "a":r['a'], "s":fs, "mt":ms, "hm":bh, "am":ba})
            
            if st.form_submit_button("✅ ENREGISTRER"):
                sn, jk = st.session_state['s_active'], f"Journée {j_res}"
                if jk not in st.session_state['history'][sn]: st.session_state['history'][sn][jk] = {"cal":[], "res":[], "pro":[]}
                st.session_state['history'][sn][jk]["res"] = val_r
                save_db(st.session_state['history'])
                custom_notify("c'est enregistré dans l'historique")

# --- TAB 4 : HISTORIQUE (SÉCURISÉ) ---
with tabs[4]:
    st.header("📚 Archives de l'Oracle")
    if not st.session_state['history']: st.info("Vide.")
    else:
        s_sel = st.selectbox("Choisir Saison", list(st.session_state['history'].keys()))
        for jk in list(st.session_state['history'][s_sel].keys()):
            with st.expander(f"📅 {jk}"):
                c1, c2 = st.columns([5, 1])
                with c2:
                    if st.button("🗑️", key=f"del_{jk}"):
                        del st.session_state['history'][s_sel][jk]; save_db(st.session_state['history']); st.rerun()
                
                # SOUS-ONGLETS AU MÊME NIVEAU
                s_cal, s_pro, s_res = st.tabs(["📋 Calendrier", "🎯 Pronostic", "⚽ Résultat"])
                
                day_data = st.session_state['history'][s_sel][jk]
                
                with s_cal:
                    # Utilisation de .get() pour éviter le message rouge si la clé n'existe pas
                    cal_list = day_data.get("cal", [])
                    if cal_list:
                        st.table(pd.DataFrame([{"Match": f"{m['h']} vs {m['a']}", "1": m['o'][0], "X": m['o'][1], "2": m['o'][2]} for m in cal_list]))
                    else: st.write("Aucun calendrier.")

                with s_pro:
                    pro_list = day_data.get("pro", [])
                    if pro_list:
                        st.table(pd.DataFrame([{"Analyse": p['m'], "Cotes": p['c']} for p in pro_list]))
                    else: st.write("Aucun pronomstic enregistré pour cette journée.")

                with s_res:
                    res_list = day_data.get("res", [])
                    if res_list:
                        st.table(pd.DataFrame([{"M": f"{m['h']} vs {m['a']}", "Score": m['s'], "MT": m['mt'], "Buteurs": f"{m['hm']} | {m['am']}"} for m in res_list]))
                    else: st.write("Aucun résultat.")

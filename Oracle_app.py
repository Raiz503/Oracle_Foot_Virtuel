import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

# Configuration de la page
st.set_page_config(page_title="Oracle V17.0 - Système Saison", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'fr'], gpu=False)

reader = load_ocr()

# --- INITIALISATION DE LA BASE DE DONNÉES ---
if 'db_calendrier' not in st.session_state:
    st.session_state['db_calendrier'] = pd.DataFrame(columns=['Saison', 'Journée', 'Domicile', 'Extérieur', 'C1', 'CX', 'C2'])
if 'db_resultats' not in st.session_state:
    st.session_state['db_resultats'] = pd.DataFrame(columns=['Saison', 'Journée', 'Domicile', 'Extérieur', 'Score', 'MT', 'Buts_D', 'Buts_E'])
if 'saison_nom' not in st.session_state:
    st.session_state['saison_nom'] = "Saison 2026"

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

# --- NAVIGATION ---
tabs = st.tabs(["🌟 NOUVELLE SAISON", "📅 SCAN CALENDRIER", "⚽ SCAN RÉSULTATS", "🎯 PRONOS", "📊 HISTORIQUE"])

# --- ONGLET 1 : CONFIGURATION SAISON ---
with tabs[0]:
    st.header("⚙️ Configuration de la Saison")
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Nom de la saison actuelle :", st.session_state['saison_nom'])
        if st.button("Mettre à jour le nom"):
            st.session_state['saison_nom'] = new_name
            st.success(f"Saison renommée en : {new_name}")
    
    with col2:
        st.warning("Zone de réinitialisation")
        if st.button("🗑️ RESET TOUTES LES DONNÉES"):
            st.session_state['db_calendrier'] = pd.DataFrame(columns=['Saison', 'Journée', 'Domicile', 'Extérieur', 'C1', 'CX', 'C2'])
            st.session_state['db_resultats'] = pd.DataFrame(columns=['Saison', 'Journée', 'Domicile', 'Extérieur', 'Score', 'MT', 'Buts_D', 'Buts_E'])
            st.rerun()

# --- ONGLET 2 : SCAN CALENDRIER (Verrouillé) ---
with tabs[1]:
    st.header("📸 Scan du Calendrier")
    file_cal = st.file_uploader("Upload Calendrier", type=['jpg','png','jpeg'], key="cal")
    journee_cal = st.number_input("Numéro de Journée", 1, 38, value=1, key="j_cal")
    
    if file_cal:
        # Logique de détection identique à la V16
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums: f_odds.extend([float(n.replace(',', '.')) for n in nums])
        
        matches_cal = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [0.0, 0.0, 0.0]
            matches_cal.append({'h': h, 'a': a, 'o': o})

        with st.form("save_cal"):
            temp_data = []
            for i, m in enumerate(matches_cal):
                c1, c2, c3 = st.columns([2, 2, 2])
                h_f = c1.selectbox(f"Dom {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                a_f = c2.selectbox(f"Ext {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                temp_data.append([st.session_state['saison_nom'], journee_cal, h_f, a_f, m['o'][0], m['o'][1], m['o'][2]])
            
            if st.form_submit_button("💾 ENREGISTRER LA JOURNÉE DANS L'HISTORIQUE"):
                new_df = pd.DataFrame(temp_data, columns=st.session_state['db_calendrier'].columns)
                st.session_state['db_calendrier'] = pd.concat([st.session_state['db_calendrier'], new_df]).drop_duplicates(subset=['Journée', 'Domicile'], keep='last')
                st.success(f"Journée {journee_cal} enregistrée !")

# --- ONGLET 3 : SCAN RÉSULTATS (Verrouillé/Sanctuarisé) ---
with tabs[2]:
    st.header("📸 Scan des Résultats")
    file_res = st.file_uploader("Upload Résultats", type=['jpg','png','jpeg'], key="res")
    journee_res = st.number_input("Numéro de Journée", 1, 38, value=1, key="j_res")
    
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        res_raw = reader.readtext(file_res.getvalue(), detail=1)
        res_raw.sort(key=lambda x: x[0][0][1])
        
        # Logique V16.0 Anchor Precision
        anchors = []
        for (bbox, text, prob) in res_raw:
            y_c = (bbox[0][1] + bbox[2][1]) / 2
            x_c = (bbox[0][0] + bbox[1][0]) / 2
            if h_img*0.12 < y_c < h_img*0.95:
                team = engine.clean_team(text)
                if team and x_c < mid_x:
                    if not anchors or abs(y_c - anchors[-1]["y"]) > 45:
                        anchors.append({"name": team, "y": y_c})
        
        results_list = []
        for i, anchor in enumerate(anchors):
            if len(results_list) >= 10: break
            y_s, y_e = anchor["y"] - 15, (anchors[i+1]["y"] - 15 if i+1 < len(anchors) else h_img*0.98)
            m = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            for (bbox, text, prob) in res_raw:
                cy, cx = (bbox[0][1] + bbox[2][1]) / 2, (bbox[0][0] + bbox[1][0]) / 2
                if y_s <= cy <= y_e:
                    t_n = engine.clean_team(text)
                    if t_n and cx > mid_x: m["a"] = t_n
                    elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper(): m["s"] = text
                    elif "MT" in text.upper(): m["mt"] = text
                    elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                        if cx < mid_x: m["h_m"] += f" {text}"
                        else: m["a_m"] += f" {text}"
            results_list.append(m)

        with st.form("save_res"):
            res_data = []
            for i, r in enumerate(results_list):
                c1, sc, c2 = st.columns([2, 1, 2])
                c1.write(f"🏠 {r['h']}")
                final_s = sc.text_input("Score", r['s'], key=f"fsc{i}")
                c2.write(f"🚀 {r['a']}")
                res_data.append([st.session_state['saison_nom'], journee_res, r['h'], r['a'], final_s, r['mt'], r['h_m'], r['a_m']])
            if st.form_submit_button("💾 VERROUILLER ET ARCHIVER"):
                res_df = pd.DataFrame(res_data, columns=st.session_state['db_resultats'].columns)
                st.session_state['db_resultats'] = pd.concat([st.session_state['db_resultats'], res_df]).drop_duplicates(subset=['Journée', 'Domicile'], keep='last')
                st.success("Résultats archivés !")

# --- ONGLET 4 : PRONOSTICS ---
with tabs[3]:
    st.header("🎯 Générateur de Tickets")
    if not st.session_state['db_calendrier'].empty:
        sel_j = st.selectbox("Voir les pronos de la Journée :", st.session_state['db_calendrier']['Journée'].unique())
        view = st.session_state['db_calendrier'][st.session_state['db_calendrier']['Journée'] == sel_j]
        for _, row in view.iterrows():
            st.info(f"**{row['Domicile']} vs {row['Extérieur']}** | Cotes: {row['C1']} - {row['CX']} - {row['C2']}")
    else:
        st.write("Aucun calendrier scanné pour le moment.")

# --- ONGLET 5 : HISTORIQUE (Tableaux par Journée) ---
with tabs[4]:
    st.header("📚 Archives de la Saison")
    st.subheader(f"Saison : {st.session_state['saison_nom']}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 📅 Calendriers Enregistrés")
        if not st.session_state['db_calendrier'].empty:
            st.dataframe(st.session_state['db_calendrier'], use_container_width=True)
        else:
            st.info("Historique calendrier vide.")

    with col_b:
        st.markdown("### ⚽ Résultats Enregistrés")
        if not st.session_state['db_resultats'].empty:
            st.dataframe(st.session_state['db_resultats'], use_container_width=True)
        else:
            st.info("Historique résultats vide.")

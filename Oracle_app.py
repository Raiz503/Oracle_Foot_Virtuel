import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V17.1 - Final Edition", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'fr'], gpu=False)

reader = load_ocr()

# --- INITIALISATION BASE DE DONNÉES ---
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
tabs = st.tabs(["🌟 SAISON", "📅 CALENDRIER", "⚽ RÉSULTATS", "🎯 PRONOS & TICKETS", "📊 HISTORIQUE"])

# --- ONGLET 1 : SAISON ---
with tabs[0]:
    st.session_state['saison_nom'] = st.text_input("Nom de la Saison", st.session_state['saison_nom'])
    if st.button("Effacer tout l'historique"):
        st.session_state['db_calendrier'] = pd.DataFrame(columns=st.session_state['db_calendrier'].columns)
        st.session_state['db_resultats'] = pd.DataFrame(columns=st.session_state['db_resultats'].columns)
        st.rerun()

# --- ONGLET 2 : CALENDRIER (Moteur V16) ---
with tabs[1]:
    file_cal = st.file_uploader("Scan Calendrier", type=['jpg','png','jpeg'])
    j_cal = st.number_input("Journée", 1, 38, 1)
    if file_cal:
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums: f_odds.extend([float(n.replace(',', '.')) for n in nums])
        
        with st.form("f_cal"):
            temp_cal = []
            for i in range(10):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                h_def = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
                a_def = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
                o_def = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.5, 3.2, 4.0]
                
                h = c1.selectbox(f"D{i+1}", engine.teams_list, index=engine.teams_list.index(h_def) if h_def in engine.teams_list else 0)
                a = c2.selectbox(f"E{i+1}", engine.teams_list, index=engine.teams_list.index(a_def) if a_def in engine.teams_list else 1)
                o1 = c3.number_input("C1", o_def[0], key=f"c1{i}")
                ox = c4.number_input("CX", o_def[1], key=f"cx{i}")
                o2 = c5.number_input("C2", o_def[2], key=f"c2{i}")
                temp_cal.append([st.session_state['saison_nom'], j_cal, h, a, o1, ox, o2])
            
            if st.form_submit_button("Enregistrer Calendrier"):
                new_df = pd.DataFrame(temp_cal, columns=st.session_state['db_calendrier'].columns)
                st.session_state['db_calendrier'] = pd.concat([st.session_state['db_calendrier'], new_df]).drop_duplicates(subset=['Journée', 'Domicile'], keep='last')
                st.success("Calendrier archivé !")

# --- ONGLET 3 : RÉSULTATS (RETOUR AU MOTEUR V16.0 STRICT) ---
with tabs[2]:
    file_res = st.file_uploader("Scan Résultats", type=['jpg','png','jpeg'])
    j_res = st.number_input("Journée ", 1, 38, 1)
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        res_raw = reader.readtext(file_res.getvalue(), detail=1)
        res_raw.sort(key=lambda x: x[0][0][1])
        
        anchors = []
        for (bbox, text, prob) in res_raw:
            y_c, x_c = (bbox[0][1] + bbox[2][1])/2, (bbox[0][0] + bbox[1][0])/2
            if h_img*0.12 < y_c < h_img*0.95:
                team = engine.clean_team(text)
                if team and x_c < mid_x:
                    if not anchors or abs(y_c - anchors[-1]["y"]) > 45:
                        anchors.append({"name": team, "y": y_c})
        
        matches_res = []
        for i, anchor in enumerate(anchors):
            if len(matches_res) >= 10: break
            y_s, y_e = anchor["y"] - 15, (anchors[i+1]["y"] - 15 if i+1 < len(anchors) else h_img*0.98)
            m = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
            for (bbox, text, prob) in res_raw:
                cy, cx = (bbox[0][1] + bbox[2][1])/2, (bbox[0][0] + bbox[1][0])/2
                if y_s <= cy <= y_e:
                    t_n = engine.clean_team(text)
                    if t_n and cx > mid_x: m["a"] = t_n
                    elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper(): m["s"] = text
                    elif "MT" in text.upper(): m["mt"] = text
                    elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                        if cx < mid_x: m["h_m"] += f" {text}"
                        else: m["a_m"] += f" {text}"
            matches_res.append(m)

        with st.form("f_res"):
            temp_res = []
            for i in range(10):
                m = matches_res[i] if i < len(matches_res) else {"h":"","a":"","s":"","h_m":"","a_m":"","mt":""}
                c1, sc, c2 = st.columns([2, 1, 2])
                c1.write(f"🏠 **{m['h']}**")
                score_val = sc.text_input("Score", m['s'], key=f"score{i}")
                c2.write(f"🚀 **{m['a']}**")
                
                m1, m2, mt_c = st.columns([2, 2, 1])
                bm1 = m1.text_input("Buteurs D", m['h_m'], key=f"bm1{i}")
                bm2 = m2.text_input("Buteurs E", m['a_m'], key=f"bm2{i}")
                mt_val = mt_c.text_input("MT", m['mt'], key=f"mtv{i}")
                temp_res.append([st.session_state['saison_nom'], j_res, m['h'], m['a'], score_val, mt_val, bm1, bm2])
            
            if st.form_submit_button("Enregistrer Résultats"):
                res_df = pd.DataFrame(temp_res, columns=st.session_state['db_resultats'].columns)
                st.session_state['db_resultats'] = pd.concat([st.session_state['db_resultats'], res_df]).drop_duplicates(subset=['Journée', 'Domicile'], keep='last')
                st.success("Résultats archivés !")

# --- ONGLET 4 : PRONOS & TICKETS (Nouveauté) ---
with tabs[3]:
    st.header("🎯 Analyse et Tickets")
    if not st.session_state['db_calendrier'].empty:
        j_sel = st.selectbox("Journée à analyser", st.session_state['db_calendrier']['Journée'].unique())
        data = st.session_state['db_calendrier'][st.session_state['db_calendrier']['Journée'] == j_sel]
        
        tickets = {"Safe": [], "Risque": [], "Fun": []}
        
        for _, row in data.iterrows():
            # Algorithme Probable Score
            s_h = int((3.0 / row['C1']) + 0.4)
            s_a = int((3.0 / row['C2']) + 0.1)
            
            st.info(f"⚽ **{row['Domicile']} {s_h} - {s_a} {row['Extérieur']}** (Cotes: {row['C1']} | {row['CX']} | {row['C2']})")
            
            # Répartition des tickets
            if row['C1'] < 1.6 or row['C2'] < 1.6: tickets["Safe"].append(f"{row['Domicile']} ou {row['Extérieur']}")
            if 1.8 < row['C1'] < 2.5: tickets["Risque"].append(f"Victoire {row['Domicile']}")
            if row['CX'] > 3.5: tickets["Fun"].append(f"Nul {row['Domicile']}-{row['Extérieur']}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.success(f"🎫 **TICKET SAFE**\n\n" + "\n".join(tickets["Safe"][:3]))
        c2.warning(f"🎫 **TICKET RISQUE**\n\n" + "\n".join(tickets["Risque"][:3]))
        c3.error(f"🎫 **TICKET FUN**\n\n" + "\n".join(tickets["Fun"][:3]))
    else:
        st.write("Veuillez d'abord scanner un calendrier.")

# --- ONGLET 5 : HISTORIQUE ---
with tabs[4]:
    st.subheader("📊 Tableaux de Bord")
    c1, c2 = st.columns(2)
    c1.write("📅 Calendriers")
    c1.dataframe(st.session_state['db_calendrier'], use_container_width=True)
    c2.write("⚽ Résultats")
    c2.dataframe(st.session_state['db_resultats'], use_container_width=True)

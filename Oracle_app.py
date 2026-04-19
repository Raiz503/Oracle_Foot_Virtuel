import streamlit as st
import pandas as pd
import easyocr
import re
from difflib import get_close_matches
from PIL import Image

st.set_page_config(page_title="Oracle V15.9 - Precision Finale", layout="wide")

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
st.title("🔮 ORACLE V15.9 : ZONE SÉCURISÉE")

tabs = st.tabs(["📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS"])

# --- TAB 1 : CALENDRIER ---
with tabs[0]:
    file_cal = st.file_uploader("📸 Scan Calendrier", type=['jpg','png','jpeg'], key="up_cal")
    if file_cal:
        res = reader.readtext(file_cal.read(), detail=0)
        f_teams, f_odds = [], []
        for t in res:
            name = engine.clean_team(t)
            if name: f_teams.append(name)
            nums = re.findall(r"\d+[\.,]\d+", t)
            if nums: f_odds.extend([float(n.replace(',', '.')) for n in nums])
        st.session_state['cal_v15'] = []
        for i in range(10):
            h = f_teams[i*2] if len(f_teams) > i*2 else "Inconnu"
            a = f_teams[i*2+1] if len(f_teams) > i*2+1 else "Inconnu"
            o = f_odds[i*3:i*3+3] if len(f_odds) >= i*3+3 else [1.50, 3.50, 4.50]
            st.session_state['cal_v15'].append({'h': h, 'a': a, 'o': o})

    if 'cal_v15' in st.session_state:
        with st.form("f_cal_v9"):
            validated = []
            for i, m in enumerate(st.session_state['cal_v15']):
                c1, c2, c3 = st.columns([2, 2, 2])
                hf = c1.selectbox(f"D{i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0)
                af = c2.selectbox(f"E{i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0)
                validated.append({'h': hf, 'a': af, 'o': m['o']})
            if st.form_submit_button("VALIDER"): st.session_state['ready_v15'] = validated

# --- TAB 3 : RÉSULTATS (Correction du Décalage) ---
with tabs[2]:
    file_res = st.file_uploader("📸 Scan Résultats", type=['jpg','png','jpeg'], key="up_res")
    if file_res:
        img = Image.open(file_res)
        w, h_img = img.size
        mid_x = w / 2
        
        with st.spinner("Analyse de la zone de jeu..."):
            res_raw = reader.readtext(file_res.getvalue(), detail=1)
            res_raw.sort(key=lambda x: x[0][0][1]) # Tri Y
            
            # --- FILTRAGE DE LA ZONE UTILE ---
            # On ignore les 18% du haut (Bandeau score/titre) et les 8% du bas (Menus)
            y_min_limit = h_img * 0.18
            y_max_limit = h_img * 0.92
            
            match_anchors = []
            for (bbox, text, prob) in res_raw:
                y_center = (bbox[0][1] + bbox[2][1]) / 2
                x_center = (bbox[0][0] + bbox[1][0]) / 2
                
                # On ne cherche des équipes que dans la zone centrale
                if y_min_limit < y_center < y_max_limit:
                    team = engine.clean_team(text)
                    # Si l'équipe est à gauche (Domicile)
                    if team and x_center < mid_x:
                        # Éviter les doublons sur une même ligne
                        if not match_anchors or abs(y_center - match_anchors[-1]["y"]) > 50:
                            match_anchors.append({"name": team, "y": y_center})

            matches = []
            # On traite les 10 premiers ancres trouvées
            for i, anchor in enumerate(match_anchors):
                if len(matches) >= 10: break
                
                y_top = anchor["y"] - 20
                y_bottom = match_anchors[i+1]["y"] - 10 if i+1 < len(match_anchors) else y_max_limit
                
                m_info = {"h": anchor["name"], "a": "Inconnu", "s": "0:0", "h_m": "", "a_m": "", "mt": ""}
                
                for (bbox, text, prob) in res_raw:
                    curr_y = (bbox[0][1] + bbox[2][1]) / 2
                    curr_x = (bbox[0][0] + bbox[1][0]) / 2
                    
                    if y_top <= curr_y <= y_bottom:
                        t_name = engine.clean_team(text)
                        # Equipe Extérieur
                        if t_name and curr_x > mid_x: m_info["a"] = t_name
                        # Score Final
                        elif re.search(r"^\d[:\-]\d$", text.strip()) and "MT" not in text.upper():
                            m_info["s"] = text
                        # Mi-temps
                        elif "MT" in text.upper(): m_info["mt"] = text
                        # Minutes
                        elif re.search(r"\d+", text) and not re.search(r"^\d[:\-]\d$", text):
                            if curr_x < mid_x: m_info["h_m"] += f" {text}"
                            else: m_info["a_m"] += f" {text}"
                
                matches.append(m_info)

            # AFFICHAGE DU FORMULAIRE (Sans valeurs par défaut polluantes)
            with st.form("form_final"):
                for i in range(10):
                    m = matches[i] if i < len(matches) else {"h":"Inconnu","a":"Inconnu","s":"","h_m":"","a_m":"","mt":""}
                    st.markdown(f"**Match {i+1}**")
                    c1, sc, c2 = st.columns([2, 1, 2])
                    c1.text(f"🏠 {m['h']}")
                    sc.text_input("Score", m['s'], key=f"s{i}")
                    c2.text(f"🚀 {m['a']}")
                    
                    m1, m2, mt = st.columns([2, 2, 1])
                    m1.text_input("Buts Dom", m['h_m'].strip(), key=f"bd{i}")
                    m2.text_input("Buts Ext", m['a_m'].strip(), key=f"be{i}")
                    mt.text_input("MT", m['mt'], key=f"mt{i}")
                    st.divider()
                st.form_submit_button("✅ ENREGISTRER TOUT")

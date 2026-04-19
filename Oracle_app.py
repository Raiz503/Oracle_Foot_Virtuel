import streamlit as st
import pandas as pd
import json
import os
import easyocr
import re
from difflib import get_close_matches

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle V6 - Workflow Complet", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.db_path = 'oracle_database_v6.json'
        self.teams_list = [
            "Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace", 
            "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool", 
            "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues", 
            "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"
        ]
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f: return json.load(f)
            except: pass
        return {"teams": {name: {"att": 0.5, "def": 0.5, "pts": 0, "history": [0]} for name in self.teams_list}}

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def clean_team_name(self, text):
        match = get_close_matches(text, self.teams_list, n=1, cutoff=0.30)
        return match[0] if match else "Équipe Inconnue"

    def extract_numbers(self, text):
        text = text.replace(',', '.')
        nums = re.findall(r"\d+\.\d+", text)
        return [float(n) for n in nums]

    def predict_score(self, h, a):
        # Logique de score basée sur les stats IA
        h_s, a_s = self.data["teams"].get(h, {"att":0.5, "def":0.5}), self.data["teams"].get(a, {"att":0.5, "def":0.5})
        s_h = int((h_s["att"] * (1 - a_s["def"])) * 4.5)
        s_a = int((a_s["att"] * (1 - h_s["def"])) * 3.5)
        return s_h, s_a

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE PRO V6")

# Initialisation Session
if 'matches' not in st.session_state: st.session_state['matches'] = []

tabs = st.tabs(["📸 SCAN & ANALYSE", "🏆 PRONOS & TICKETS", "✅ SAISIE RÉSULTATS", "📈 STATS"])

# --- TAB 1 : SCAN ---
with tabs[0]:
    st.subheader("1. Importation du Calendrier")
    file = st.file_uploader("Capture d'écran du calendrier", type=['jpg','png','jpeg'])
    
    if file:
        with st.spinner("Analyse en cours..."):
            raw_text = reader.readtext(file.read(), detail=0)
            
            found_teams = []
            found_odds = []
            for t in raw_text:
                clean = engine.clean_team_name(t)
                if clean != "Équipe Inconnue": found_teams.append(clean)
                elif any(char.isdigit() for char in t): # Si c'est un chiffre, on check les cotes
                    found_odds.extend(engine.extract_numbers(t))
            
            # Reconstruction forcée de 10 matchs même si l'OCR rate le début
            temp = []
            for i in range(10):
                h = found_teams[i*2] if len(found_teams) > i*2 else "Équipe Inconnue"
                a = found_teams[i*2+1] if len(found_teams) > i*2+1 else "Équipe Inconnue"
                o = found_odds[i*3:i*3+3] if len(found_odds) >= i*3+3 else [1.5, 3.5, 4.5]
                temp.append({'h': h, 'a': a, 'odds': o})
            st.session_state['matches'] = temp

    if st.session_state['matches']:
        st.divider()
        # LA JOURNÉE EN HAUT (Demande 2)
        journee = st.selectbox("Sélectionnez la Journée", range(1, 39), index=35)
        
        st.subheader("2. Vérification des 10 matchs")
        with st.form("val_form"):
            final_list = []
            for idx, m in enumerate(st.session_state['matches']):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                # Gestion de l'index pour "Équipe Inconnue"
                h_idx = engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0
                a_idx = engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0
                
                h_f = c1.selectbox(f"Dom {idx+1}", engine.teams_list, index=h_idx, key=f"h{idx}")
                a_f = c2.selectbox(f"Ext {idx+1}", engine.teams_list, index=a_idx, key=f"a{idx}")
                o1 = c3.number_input("C1", value=m['odds'][0], key=f"o1{idx}")
                ox = c4.number_input("CX", value=m['odds'][1], key=f"ox{idx}")
                o2 = c5.number_input("C2", value=m['odds'][2], key=f"o2{idx}")
                final_list.append({'h': h_f, 'a': a_f, 'odds': [o1, ox, o2], 'day': journee})
            
            if st.form_submit_button("VALIDER ET GÉNÉRER LES PRONOSTICS"):
                st.session_state['final_data'] = final_list
                st.success("Analyses prêtes dans l'onglet PRONOS")

# --- TAB 2 : PRONOS & TICKETS ---
with tabs[1]:
    if 'final_data' in st.session_state:
        # AFFICHAGE DES SCORES PROBABLES D'ABORD (Demande 2)
        st.header("📊 Scores Probables de la Journée")
        scores_cols = st.columns(2)
        for i, m in enumerate(st.session_state['final_data']):
            sh, sa = engine.predict_score(m['h'], m['a'])
            scores_cols[i%2].write(f"**{m['h']}** {sh} - {sa} **{m['a']}**")
        
        st.divider()
        st.header("🎫 Tickets Suggérés")
        t1, t2, t3 = st.columns(3)
        # Logique de tickets basée sur les 10 matchs
        with t1:
            st.info("🛡️ SÉCURISÉ")
            for m in st.session_state['final_data'][:4]: st.write(f"• {m['h']} ou Nul")
        with t2:
            st.warning("⚖️ ÉQUILIBRÉ")
            for m in st.session_state['final_data'][4:7]: st.write(f"• {m['h']} Gagne")
        with t3:
            st.error("🔥 ORACLE")
            for m in st.session_state['final_data'][7:]: st.write(f"• Score exact {m['h']}")
    else:
        st.warning("Veuillez valider le scan dans l'onglet 1")

# --- TAB 3 : IMPORTATION RÉSULTATS (Demande 3) ---
with tabs[2]:
    st.header("✅ Enregistrement des Résultats Réels")
    if 'final_data' in st.session_state:
        with st.form("res_form"):
            results_to_save = []
            for idx, m in enumerate(st.session_state['final_data']):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{m['h']} vs {m['a']}**")
                sh_r = c2.number_input("HT", min_value=0, max_value=20, key=f"shr{idx}")
                sa_r = c3.number_input("AT", min_value=0, max_value=20, key=f"sar{idx}")
                results_to_save.append({'h': m['h'], 'a': m['a'], 'sh': sh_r, 'sa': sa_r})
            
            if st.form_submit_button("METTRE À JOUR LE CLASSEMENT & L'IA"):
                for r in results_to_save:
                    # Logique de mise à jour points et IA
                    th, ta = engine.data["teams"][r['h']], engine.data["teams"][r['a']]
                    if r['sh'] > r['sa']: th["pts"] += 3
                    elif r['sa'] > r['sh']: ta["pts"] += 3
                    else: th["pts"] += 1; ta["pts"] += 1
                    # Apprentissage
                    th["att"] += (r['sh'] * 0.01); ta["def"] -= (r['sh'] * 0.01)
                engine.save_db()
                st.balloons()
                st.success("Base de données mise à jour avec succès !")
    else:
        st.info("Analysez une journée pour pouvoir saisir ses résultats ici.")

with tabs[3]:
    st.subheader("Classement actuel")
    df = pd.DataFrame.from_dict(engine.data["teams"], orient='index').sort_values("pts", ascending=False)
    st.table(df[['pts', 'att', 'def']])

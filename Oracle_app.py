import streamlit as st
import pandas as pd
import json
import os
import easyocr

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle Predictor", layout="centered")

class OracleEngine:
    def __init__(self):
        self.db_path = 'oracle_database.json'
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
        return {"teams": {name: {"att": 0.5, "def": 0.5, "pts": 0, "rank": 10, "streak": []} for name in self.teams_list}}

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def predict_logic(self, h, a, cotes, day):
        h_s, a_s = self.data["teams"][h], self.data["teams"][a]
        p1, px, p2 = 1/cotes[0], 1/cotes[1], 1/cotes[2]
        # Modules stratégiques
        if day >= 34 and h_s["rank"] >= 17: p1 += 0.20
        if h_s["streak"][-3:].count("W") == 3: p1 -= 0.12
        
        btts_val = (h_s["att"] * (1 - a_s["def"])) + (a_s["att"] * (1 - h_s["def"]))
        res = "1" if p1 > p2 else ("2" if p2 > p1 else "X")
        conf = (max(p1, p2) / (p1+px+p2)) * 100
        return {"match": f"{h} vs {a}", "res": res, "conf": conf, "btts": "OUI" if btts_val > 0.6 else "NON", "cotes": cotes}

# --- INTERFACE ---
engine = OracleEngine()
st.title("🔮 L'ORACLE : SYSTÈME DE TICKETS")

tab1, tab2, tab3 = st.tabs(["📸 Import & Analyse", "📊 Classement", "🏆 Tickets du Jour"])

with tab1:
    mode = st.radio("Type d'importation :", ["Calendrier (Prédiction)", "Résultats (Mise à jour)"])
    img_file = st.file_uploader("Prendre une photo", type=['jpg','png','jpeg'])
    
    # Simulation de l'extraction OCR éditable
    st.subheader("📝 Édition des données extraites")
    with st.form("form_ocr"):
        col1, col2, col3 = st.columns(3)
        h = col1.selectbox("Domicile", engine.teams_list)
        a = col2.selectbox("Extérieur", engine.teams_list)
        
        if mode == "Calendrier (Prédiction)":
            c1 = col1.number_input("Cote 1", 1.0, 20.0, 1.5)
            cx = col2.number_input("Cote X", 1.0, 20.0, 3.5)
            c2 = col3.number_input("Cote 2", 1.0, 20.0, 5.0)
            jour = st.slider("Journée", 1, 38, 30)
            
            if st.form_submit_button("Valider & Analyser"):
                analysis = engine.predict_logic(h, a, [c1, cx, c2], jour)
                st.session_state['last_analysed'] = analysis
                st.success("Analyse terminée. Consultez l'onglet 'Tickets'.")
        
        else:
            sh = col1.number_input("Score Dom", 0, 15, 0)
            sa = col2.number_input("Score Ext", 0, 15, 0)
            if st.form_submit_button("Valider le Résultat"):
                # Mise à jour IA
                if sh > sa: engine.data["teams"][h]["pts"] += 3
                elif sa > sh: engine.data["teams"][a]["pts"] += 3
                else: 
                    engine.data["teams"][h]["pts"] += 1
                    engine.data["teams"][a]["pts"] += 1
                engine.save_db()
                st.balloons()

with tab3:
    if 'last_analysed' in st.session_state:
        ans = st.session_state['last_analysed']
        st.subheader("🎫 Tes 3 Options de Ticket")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.info("**TICKET SÉCURISÉ**")
            st.write(f"{ans['match']}")
            st.write(f"Prono: **Double Chance**")
            st.write("Fiabilité: ⭐⭐⭐⭐⭐")
            
        with c2:
            st.warning("**TICKET ÉQUILIBRÉ**")
            st.write(f"{ans['match']}")
            st.write(f"Prono: **{ans['res']}**")
            st.write(f"BTTS: **{ans['btts']}**")
            
        with c3:
            st.error("**TICKET ORACLE**")
            st.write(f"{ans['match']}")
            st.write(f"Prono: **{ans['res']} & {ans['btts']}**")
            st.write(f"Confiance: **{ans['conf']}%**")
    else:
        st.write("Veuillez d'abord analyser un match dans l'onglet 1.")

with tab2:
    st.dataframe(pd.DataFrame.from_dict(engine.data["teams"], orient='index').sort_values("pts", ascending=False))

import streamlit as st
import pandas as pd
import json
import os
import easyocr
from difflib import get_close_matches

# --- CONFIGURATION DE L'APPLICATION ---
st.set_page_config(page_title="Oracle Football Predictor", layout="wide")

class OracleEngine:
    def __init__(self):
        self.db_path = 'oracle_database.json'
        self.teams_list = [
            "London Reds", "Manchester Blue", "Liverpool", "Newcastle", 
            "Brentford", "Sunderland", "Everton", "A. Villa", "Burnley", "Leeds"
        ] # Ajoute les 20 noms exacts ici
        self.data = self.load_db()

    def load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f: return json.load(f)
        return {"teams": {}, "history": []}

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def get_team_stats(self, name):
        # Correction automatique du nom via Fuzzy Matching
        match = get_close_matches(name, self.teams_list, n=1, cutoff=0.6)
        clean_name = match[0] if match else name
        
        if clean_name not in self.data["teams"]:
            self.data["teams"][clean_name] = {
                "att": 0.5, "def": 0.5, "pts": 0, "rank": 10, "streak": []
            }
        return clean_name, self.data["teams"][clean_name]

    def predict(self, home_raw, away_raw, cotes, day):
        h_name, h_stats = self.get_team_stats(home_raw)
        a_name, a_stats = self.get_team_stats(away_raw)
        
        # Logique de calcul
        p1, px, p2 = 1/cotes[0], 1/cotes[1], 1/cotes[2]
        
        # Bonus MSS / Fatigue
        if day >= 34 and h_stats["rank"] >= 17: p1 += 0.15
        if len(h_stats["streak"]) >= 3 and h_stats["streak"][-3:].count("W") == 3: p1 -= 0.10
        
        # Décision
        res = "1" if p1 > p2 else "2"
        conf = max(p1, p2) / (p1 + px + p2)
        return h_name, a_name, res, round(conf*100, 1)

# --- INTERFACE STREAMLIT ---
st.title("🔮 Oracle Football Predictor Pro")
engine = OracleEngine()

tab1, tab2, tab3 = st.tabs(["🎯 Pronostics", "📊 Classement", "⚙️ Configuration"])

with tab1:
    st.header("Analyse de Match")
    col1, col2 = st.columns(2)
    
    with col1:
        img_file = st.file_uploader("Importer capture (Calendrier)", type=['jpg', 'png', 'jpeg'])
        if img_file:
            st.image(img_file, caption="Scan en cours...", width=300)
            # Ici l'OCR s'active
            reader = easyocr.Reader(['en'])
            result = reader.readtext(img_file.read(), detail=0)
            st.write("Mots détectés :", result)

    with col2:
        st.subheader("Entrée Manuelle / Validation")
        h = st.selectbox("Équipe Domicile", engine.teams_list)
        a = st.selectbox("Équipe Extérieur", engine.teams_list)
        c1 = st.number_input("Cote 1", value=1.50)
        cx = st.number_input("Cote X", value=3.40)
        c2 = st.number_input("Cote 2", value=5.00)
        day = st.slider("Journée", 1, 38, 36)
        
        if st.button("Lancer l'Oracle"):
            h_n, a_n, res, conf = engine.predict(h, a, [c1, cx, c2], day)
            st.success(f"Résultat prédit : {res}")
            st.metric("Indice de Confiance", f"{conf}%")

with tab2:
    st.header("Classement de la Ligue")
    df = pd.DataFrame.from_dict(engine.data["teams"], orient='index')
    if not df.empty:
        st.table(df.sort_values(by="pts", ascending=False))

with tab3:
    if st.button("Réinitialiser la Base de Données"):
        engine.data = {"teams": {}, "history": []}
        engine.save_db()
        st.warning("Données effacées.")

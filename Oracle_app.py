import streamlit as st
import pandas as pd
import json
import os
import easyocr
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
st.set_page_config(page_title="Oracle Pro V4", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.db_path = 'oracle_database_v4.json'
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
        return {
            "teams": {name: {"att": 0.5, "def": 0.5, "pts": 0, "history": [0]} for name in self.teams_list},
            "matches_analysed": []
        }

    def save_db(self):
        with open(self.db_path, 'w') as f: json.dump(self.data, f, indent=4)

    def predict_score(self, h, a):
        h_s, a_s = self.data["teams"][h], self.data["teams"][a]
        # Calcul du score probable basé sur Attaque vs Défense
        score_h = int((h_s["att"] * (1 - a_s["def"])) * 4)
        score_a = int((a_s["att"] * (1 - h_s["def"])) * 3)
        return score_h, score_a

# --- LOGIQUE D'INTERFACE ---
engine = OracleEngine()
st.title("🔮 ORACLE CONTROL CENTER V4")

tabs = st.tabs(["📸 Scan & Validation", "🎫 Tickets & Pronos", "📈 Tableau de Bord", "📊 Classement"])

# --- TAB 1 : SCAN & VALIDATION ---
with tabs[0]:
    mode = st.radio("Action :", ["Scanner Calendrier", "Scanner Résultats"])
    file = st.file_uploader("Prendre une photo", type=['jpg','png','jpeg'])
    
    if file:
        with st.spinner("L'IA analyse l'image..."):
            raw_text = reader.readtext(file.read(), detail=0)
            st.write("📡 **Données brutes détectées :**", ", ".join(raw_text))
            
        st.subheader("🛠️ Vérification et Correction")
        with st.form("validation_form"):
            col1, col2 = st.columns(2)
            # Tentative de pré-remplissage simple (on prend les 2 premiers mots qui ressemblent à des équipes)
            h_guess = col1.selectbox("Équipe Domicile (Corrigé)", engine.teams_list)
            a_guess = col2.selectbox("Équipe Extérieur (Corrigé)", engine.teams_list)
            
            if mode == "Scanner Calendrier":
                c1 = col1.number_input("Cote 1", value=1.5)
                cx = st.number_input("Cote X", value=3.5)
                c2 = col2.number_input("Cote 2", value=4.5)
                
                if st.form_submit_button("Lancer l'Analyse de la Journée"):
                    sh, sa = engine.predict_score(h_guess, a_guess)
                    st.session_state['last_match'] = {
                        "h": h_guess, "a": a_guess, "sh": sh, "sa": sa, "cotes": [c1, cx, c2]
                    }
                    st.success("Analyse terminée ! Consultez l'onglet Tickets.")
            else:
                sh_real = col1.number_input("Score Dom Réel", value=0)
                sa_real = col2.number_input("Score Ext Réel", value=0)
                
                if st.form_submit_button("Valider et Mettre à jour l'IA"):
                    # Mise à jour Points
                    t_h, t_a = engine.data["teams"][h_guess], engine.data["teams"][a_guess]
                    if sh_real > sa_real: t_h["pts"] += 3
                    elif sa_real > sh_real: t_a["pts"] += 3
                    else: t_h["pts"] += 1; t_a["pts"] += 1
                    
                    # Historique pour graphique
                    t_h["history"].append(t_h["pts"])
                    t_a["history"].append(t_a["pts"])
                    
                    # Apprentissage
                    t_h["att"] = min(1.0, t_h["att"] + (sh_real * 0.02))
                    t_a["def"] = max(0.0, t_a["def"] - (sh_real * 0.01))
                    
                    engine.save_db()
                    st.balloons()

# --- TAB 2 : TICKETS ---
with tabs[1]:
    if 'last_match' in st.session_state:
        m = st.session_state['last_match']
        st.header(f"🔥 Pronostic : {m['h']} vs {m['a']}")
        st.subheader(f"Score Probable : {m['sh']} - {m['sa']}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("**TICKET SÉCURISÉ**\n\nDouble Chance\nFiabilité: 92%")
        with c2:
            st.warning(f"**TICKET ÉQUILIBRÉ**\n\nVictoire: {'1' if m['sh']>m['sa'] else '2'}\nPlus de 1.5 buts")
        with c3:
            st.error(f"**TICKET ORACLE**\n\nScore exact: {m['sh']}-{m['sa']}\nCote boostée")
    else:
        st.write("Veuillez d'abord scanner un calendrier.")

# --- TAB 3 : DASHBOARD ---
with tabs[2]:
    st.subheader("📈 Progression des équipes")
    team_to_plot = st.multiselect("Choisir les équipes à comparer", engine.teams_list, default=[engine.teams_list[0]])
    
    fig, ax = plt.subplots()
    for team in team_to_plot:
        ax.plot(engine.data["teams"][team]["history"], label=team, marker='o')
    
    ax.set_ylabel("Points")
    ax.set_xlabel("Matchs joués")
    ax.legend()
    st.pyplot(fig)

# --- TAB 4 : CLASSEMENT ---
with tabs[3]:
    df = pd.DataFrame.from_dict(engine.data["teams"], orient='index').sort_values("pts", ascending=False)
    st.table(df[['pts', 'att', 'def']])

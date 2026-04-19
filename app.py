import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Gym Tracker Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- DATABASE SCHEDE ---
SCHEDE = {
    "PUSH (Spinta)": ["Panca Piana", "Spinte Inclinata", "Shoulder Press", "Alzate Laterali", "Dip", "Pushdown", "Farmer's Walk", "Plank"],
    "PULL (Trazione)": ["Lat Machine", "Rematore Manubrio", "Pulley Basso", "Face Pull", "Iperestensioni", "Curl Bilanciere", "Hammer Curl", "Wrist Curl"],
    "LEGS (Gambe)": ["Squat/Pressa", "Affondi", "Leg Extension", "Leg Curl", "Calf Raise", "Bird-Dog", "Crunch Inverso", "Russian Twist"]
}

# --- CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Carica lo storico dal foglio "Allenamenti"
        return conn.read(worksheet="Allenamenti", ttl="0")
    except:
        # Se il foglio è vuoto o non esiste, crea un DF di base
        return pd.DataFrame(columns=["Data", "Scheda", "Esercizio", "Serie", "Peso", "Ripetizioni"])

# --- SIDEBAR: NAVIGAZIONE E TIMER ---
with st.sidebar:
    st.title("Settings & Tools")
    menu = st.radio("Navigazione", ["Allenamento", "📊 Riepilogo Progressi"])
    
    st.divider()
    
    # Widget Timer di Recupero
    st.header("⏱️ Timer Recupero")
    tempo_recupero = st.number_input("Secondi di riposo:", value=90, step=15)
    if st.button("🚀 Avvia Timer"):
        placeholder = st.empty()
        for i in range(tempo_recupero, 0, -1):
            placeholder.metric("Recupero...", f"{i}s")
            time.sleep(1)
        placeholder.success("🔥 Vai con la prossima!")
        st.balloons()

# --- LOGICA PRINCIPALE ---
if menu == "Allenamento":
    st.title("🏋️‍♂️ Sessione di Allenamento")
    
    scheda_scelta = st.selectbox("Seleziona scheda:", list(SCHEDE.keys()))
    esercizi = SCHEDE[scheda_scelta]
    
    data_oggi = st.date_input("Data", datetime.now())

    # Recupero storico per pre-compilazione
    history = load_data()
    data_setup = []
    
    for es in esercizi:
        # Filtra l'ultimo allenamento per questo esercizio
        ultimo_es = history[history["Esercizio"] == es].sort_values(by="Data", ascending=False).head(4)
        
        row = {"Esercizio": es}
        for i in range(1, 5):
            valore_precedente = ultimo_es[ultimo_es["Serie"] == i]
            if not valore_precedente.empty:
                row[f"S{i}_Kg"] = float(valore_precedente.iloc[0]["Peso"])
                row[f"S{i}_Reps"] = int(valore_precedente.iloc[0]["Ripetizioni"])
            else:
                row[f"S{i}_Kg"] = 0.0
                row[f"S{i}_Reps"] = 0
        data_setup.append(row)
    
    df_input = pd.DataFrame(data_setup)

    st.write("### Tabella Allenamento")
    st.caption("Scorri lateralmente ➡️ (Esercizio è bloccato a sinistra)")
    
    # Configurazione colonne con Colori (Emoji) e Pinning
    col_config = {
        "Esercizio": st.column_config.Column(
            "🏋️ Esercizio", 
            disabled=True, 
            pinned=True, 
            width="medium"
        ),
        "S1_Kg": st.column_config.NumberColumn("🟢 S1 Kg", format="%.1f", width="small"),
        "S1_Reps": st.column_config.NumberColumn("🟢 S1 Rep", width="small"),
        
        "

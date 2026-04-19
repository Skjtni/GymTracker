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
        return conn.read(worksheet="Allenamenti", ttl="0")
    except:
        return pd.DataFrame(columns=["Data", "Scheda", "Esercizio", "Serie", "Peso", "Ripetizioni"])

# --- SIDEBAR: NAVIGAZIONE E TIMER ---
with st.sidebar:
    st.title("Settings & Tools")
    menu = st.radio("Navigazione", ["Allenamento", "📊 Riepilogo Progressi"])
    
    st.divider()
    st.header("⏱️ Timer Recupero")
    tempo_recupero = st.number_input("Secondi di riposo:", value=90, step=15)
    if st.button("🚀 Avvia Timer"):
        placeholder = st.empty()
        for i in range(int(tempo_recupero), 0, -1):
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

    history = load_data()
    data_setup = []
    
    for es in esercizi:
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
    st.caption("Scorri lateralmente ➡️ (Esercizio bloccato a sinistra)")
    
    # Configurazione colonne (Corretto per evitare SyntaxError)
    col_config = {
        "Esercizio": st.column_config.Column("🏋️ Esercizio", disabled=True, pinned=True, width="medium"),
        "S1_Kg": st.column_config.NumberColumn("🟢 S1 Kg", format="%.1f", width="small"),
        "S1_Reps": st.column_config.NumberColumn("🟢 S1 Rep", width="small"),
        "S2_Kg": st.column_config.NumberColumn("🟡 S2 Kg", format="%.1f", width="small"),
        "S2_Reps": st.column_config.NumberColumn("🟡 S2 Rep", width="small"),
        "S3_Kg": st.column_config.NumberColumn("🟠 S3 Kg", format="%.1f", width="small"),
        "S3_Reps": st.column_config.NumberColumn("🟠 S3 Rep", width="small"),
        "S4_Kg": st.column_config.NumberColumn("🔴 S4 Kg", format="%.1f", width="small"),
        "S4_Reps": st.column_config.NumberColumn("🔴 S4 Rep", width="small"),
    }

    edited_df = st.data_editor(
        df_input, 
        hide_index=True, 
        use_container_width=True,
        column_config=col_config
    )

    if st.button("✅ Salva Allenamento", use_container_width=True):
        new_records = []
        for _, row in edited_df.iterrows():
            for i in range(1, 5):
                kg = row[f"S{i}_Kg"]
                reps = row[f"S{i}_Reps"]
                if reps > 0:
                    new_records.append({
                        "Data": data_oggi.strftime("%Y-%m-%d"),
                        "Scheda": scheda_scelta,
                        "Esercizio": row["Esercizio"],
                        "Serie": i,
                        "Peso": kg,
                        "Ripetizioni": reps
                    })
        
        if new_records:
            updated_history = pd.concat([history, pd.DataFrame(new_records)], ignore_index=True)
            conn.update(worksheet="Allenamenti", data=updated_history)
            st.success("Dati salvati!")
            st.balloons()
        else:
            st.error("Inserisci almeno un dato!")

elif menu == "📊 Riepilogo Progressi":
    st.title("📊 Analisi Performance")
    history = load_data()
    
    if not history.empty:
        es_grafico = st.selectbox("Analizza esercizio:", history["Esercizio"].unique())
        df_es = history[history["Esercizio"] == es_grafico].copy()
        df_es["Data"] = pd.to_datetime(df_es["Data"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Massimale Stimato (1RM)")
            df_es["1RM"] = df_es.apply(lambda x: x["Peso"] * (36 / (37 - x["Ripetizioni"])) if x["Ripetizioni"] < 37 and x["Ripetizioni"] > 1 else x["Peso"], axis=1)
            max_1rm = df_es.groupby("Data")["1RM"].max()
            st.line_chart(max_1rm)
        with col2:
            st.subheader("Volume Totale")
            df_es["Volume"] = df_es["Peso"] * df_es["Ripetizioni"]
            vol_per_data = df_es.groupby("Data")["Volume"].sum()
            st.bar_chart(vol_per_data)
            
        st.divider()
        st.dataframe(df_es.sort_values(by="Data", ascending=False), use_container_width=True)
    else:
        st.info("Nessun dato presente.")

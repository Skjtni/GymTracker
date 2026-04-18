import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configurazione Pagina
st.set_page_config(page_title="Gym Tracker Pro", layout="wide")

# --- DATABASE SCHEDE ---
SCHEDE = {
    "PUSH (Spinta)": ["Panca Piana", "Spinte Inclinata", "Shoulder Press", "Alzate Laterali", "Dip", "Pushdown", "Farmer's Walk", "Plank"],
    "PULL (Trazione)": ["Lat Machine", "Rematore Manubrio", "Pulley Basso", "Face Pull", "Iperestensioni", "Curl Bilanciere", "Hammer Curl", "Wrist Curl"],
    "LEGS (Gambe)": ["Squat/Pressa", "Affondi", "Leg Extension", "Leg Curl", "Calf Raise", "Bird-Dog", "Crunch Inverso", "Russian Twist"]
}

# Connessione Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(worksheet="Allenamenti", ttl="0")
    except:
        return pd.DataFrame(columns=["Data", "Scheda", "Esercizio", "Serie", "Peso", "Ripetizioni"])

# --- INTERFACCIA ---
st.title("🏋️‍♂️ My Gym Diary")
menu = st.sidebar.radio("Navigazione", ["Allenamento", "📊 Riepilogo Progressi"])

if menu == "Allenamento":
    scheda_scelta = st.selectbox("Cosa alleniamo oggi?", list(SCHEDE.keys()))
    esercizi = SCHEDE[scheda_scelta]
    
    st.subheader(f"Scheda Selezionata: {scheda_scelta}")
    data_oggi = st.date_input("Data sessione", datetime.now())

    # Recupero ultimi dati per pre-compilazione
    history = load_data()
    data_setup = []
    
    for es in esercizi:
        # Cerchiamo l'ultima volta che hai fatto questo esercizio
        ultimo_es = history[history["Esercizio"] == es].sort_values(by="Data", ascending=False).head(4)
        
        row = {"Esercizio": es}
        for i in range(1, 5):
            # Prova a recuperare il peso/rep dell'ultima volta per la serie i-esima
            valore_precedente = ultimo_es[ultimo_es["Serie"] == i]
            if not valore_precedente.empty:
                row[f"S{i}_Kg"] = float(valore_precedente.iloc[0]["Peso"])
                row[f"S{i}_Reps"] = int(valore_precedente.iloc[0]["Ripetizioni"])
            else:
                row[f"S{i}_Kg"] = 0.0
                row[f"S{i}_Reps"] = 0
        data_setup.append(row)
    
    df_input = pd.DataFrame(data_setup)

    st.info("I valori precompilati sono quelli dell'ultima sessione. Aggiornali con i nuovi progressi!")
    
    edited_df = st.data_editor(
        df_input, 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Esercizio": st.column_config.Column(disabled=True, width="medium"),
            "S1_Kg": st.column_config.NumberColumn("S1 Kg", format="%.1f"),
            "S1_Reps": st.column_config.NumberColumn("S1 Rep/m/s"),
            "S2_Kg": st.column_config.NumberColumn("S2 Kg", format="%.1f"),
            "S2_Reps": st.column_config.NumberColumn("S2 Rep/m/s"),
            "S3_Kg": st.column_config.NumberColumn("S3 Kg", format="%.1f"),
            "S3_Reps": st.column_config.NumberColumn("S3 Rep/m/s"),
            "S4_Kg": st.column_config.NumberColumn("S4 Kg", format="%.1f"),
            "S4_Reps": st.column_config.NumberColumn("S4 Rep/m/s"),
        }
    )

    if st.button("💾 Salva Allenamento"):
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
            st.success("Dati inviati a Google Sheets!")
            st.balloons()
        else:
            st.error("Nessun dato inserito.")

elif menu == "📊 Riepilogo Progressi":
    st.header("Analisi Performance")
    history = load_data()
    
    if not history.empty:
        es_grafico = st.selectbox("Scegli esercizio:", history["Esercizio"].unique())
        df_es = history[history["Esercizio"] == es_grafico].copy()
        df_es["Data"] = pd.to_datetime(df_es["Data"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Massimale Stimato (1RM)")
            # Formula Brzycki: Peso * (36 / (37 - Reps))
            df_es["1RM"] = df_es.apply(lambda x: x["Peso"] * (36 / (37 - x["Ripetizioni"])) if x["Ripetizioni"] < 37 and x["Ripetizioni"] > 1 else x["Peso"], axis=1)
            max_1rm = df_es.groupby("Data")["1RM"].max()
            st.line_chart(max_1rm)
            st.caption("Il 1RM è calcolato per esercizi con reps > 1. Per isometrici/metri mostra il peso massimo.")

        with col2:
            st.subheader("Volume Totale")
            df_es["Volume"] = df_es["Peso"] * df_es["Ripetizioni"]
            vol_per_data = df_es.groupby("Data")["Volume"].sum()
            st.bar_chart(vol_per_data)
            st.caption("Volume = Peso x Ripetizioni (o metri/secondi)")
            
        st.divider()
        st.subheader("Storico Completo")
        st.dataframe(df_es.sort_values(by="Data", ascending=False), use_container_width=True)
    else:
        st.info("Inizia ad allenarti per vedere i grafici!")

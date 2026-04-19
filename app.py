import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gym Tracker Dynamic", layout="wide")

# --- CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl="0")
    except:
        return pd.DataFrame()

# --- CARICAMENTO CONFIGURAZIONI ---
df_storico = get_data("Allenamenti")
df_config = get_data("Config_Schede")

# Lista di tutti gli esercizi mai fatti (per il menu a tendina)
tutti_esercizi_storici = []
if not df_storico.empty:
    tutti_esercizi_storici = sorted(df_storico["Esercizio"].unique().tolist())

# --- SIDEBAR ---
with st.sidebar:
    st.title("Gym Settings")
    menu = st.radio("Navigazione", ["Allenamento", "📊 Riepilogo Progressi"])
    st.divider()
    st.header("⏱️ Timer")
    tempo = st.number_input("Secondi:", value=90, step=15)
    if st.button("🚀 Start Timer"):
        p = st.empty()
        for i in range(int(tempo), 0, -1):
            p.metric("Recupero...", f"{i}s")
            time.sleep(1)
        p.success("🔥 Vai!")
        st.balloons()

# --- LOGICA ALLENAMENTO ---
if menu == "Allenamento":
    st.title("🏋️‍♂️ Sessione Live")
    
    if df_config.empty:
        st.error("ERRORE: Non ho trovato il foglio 'Config_Schede' o è vuoto.")
        st.stop()

    lista_schede = df_config["Scheda"].unique().tolist()
    scheda_scelta = st.selectbox("Seleziona Scheda:", lista_schede)
    
    # Filtriamo gli esercizi previsti per quella scheda
    esercizi_previsti = df_config[df_config["Scheda"] == scheda_scelta]["Esercizio"].tolist()
    
    data_oggi = st.date_input("Data", datetime.now())

    # Prepariamo i dati per la tabella
    data_setup = []
    for es in esercizi_previsti:
        # Cerchiamo l'ultima volta (per pre-compilazione)
        row = {"Esercizio": es}
        if not df_storico.empty:
            ultimo = df_storico[df_storico["Esercizio"] == es].sort_values(by="Data", ascending=False).head(4)
            for i in range(1, 5):
                val = ultimo[ultimo["Serie"] == i]
                row[f"S{i}_Kg"] = float(val.iloc[0]["Peso"]) if not val.empty else 0.0
                row[f"S{i}_R"] = int(val.iloc[0]["Ripetizioni"]) if not val.empty else 0
        else:
            for i in range(1, 5):
                row[f"S{i}_Kg"], row[f"S{i}_R"] = 0.0, 0
        data_setup.append(row)
    
    df_input = pd.DataFrame(data_setup)

    # UNIONE: Esercizi della scheda + esercizi storici (per evitare duplicati con nomi diversi)
    opzioni_esercizi = sorted(list(set(esercizi_previsti + tutti_esercizi_storici)))

    st.write("### 📝 Diario di oggi")
    
    col_config = {
        "Esercizio": st.column_config.SelectboxColumn(
            "🏋️ Esercizio", 
            options=opzioni_esercizi, # <--- MENU A TENDINA
            required=True,
            width="medium"
        ),
        "S1_Kg": st.column_config.NumberColumn("🟢Kg", format="%.1f", width="small"),
        "S1_R": st.column_config.NumberColumn("🟢R", width="small"),
        "S2_Kg": st.column_config.NumberColumn("🟡Kg", format="%.1f", width="small"),
        "S2_R": st.column_config.NumberColumn("🟡R", width="small"),
        "S3_Kg": st.column_config.NumberColumn("🟠Kg", format="%.1f", width="small"),
        "S3_R": st.column_config.NumberColumn("🟠R", width="small"),
        "S4_Kg": st.column_config.NumberColumn("🔴Kg", format="%.1f", width="small"),
        "S4_R": st.column_config.NumberColumn("🔴R", width="small"),
    }

    edited_df = st.data_editor(df_input, hide_index=True, use_container_width=True, column_config=col_config, num_rows="dynamic")

    if st.button("✅ SALVA SESSIONE", use_container_width=True, type="primary"):
        new_recs = []
        for _, r in edited_df.iterrows():
            for i in range(1, 5):
                if r[f"S{i}_R"] > 0:
                    new_recs.append({
                        "Data": data_oggi.strftime("%Y-%m-%d"),
                        "Scheda": scheda_scelta,
                        "Esercizio": r["Esercizio"],
                        "Serie": i,
                        "Peso": r[f"S{i}_Kg"],
                        "Ripetizioni": r[f"S{i}_R"]
                    })
        
        if new_recs:
            updated = pd.concat([df_storico, pd.DataFrame(new_recs)], ignore_index=True)
            conn.update(worksheet="Allenamenti", data=updated)
            st.success("Dati inviati!")
            st.balloons()

elif menu == "📊 Riepilogo Progressi":
    st.title("📊 Analisi")
    if not df_storico.empty:
        es_sel = st.selectbox("Esercizio:", sorted(df_storico["Esercizio"].unique()))
        df_es = df_storico[df_storico["Esercizio"] == es_sel].copy()
        df_es["Data"] = pd.to_datetime(df_es["Data"])
        
        # 1RM
        df_es["1RM"] = df_es.apply(lambda x: x["Peso"] * (36 / (37 - x["Ripetizioni"])) if x["Ripetizioni"] < 37 and x["Ripetizioni"] > 1 else x["Peso"], axis=1)
        st.line_chart(df_es.groupby("Data")["1RM"].max())
        
        # Volume
        df_es["Volume"] = df_es["Peso"] * df_es["Ripetizioni"]
        st.bar_chart(df_es.groupby("Data")["Volume"].sum())
        
        st.dataframe(df_es.sort_values(by="Data", ascending=False), use_container_width=True)
    else:
        st.info("Storico vuoto.")

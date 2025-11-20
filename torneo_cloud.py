import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# --- CONFIGURAZIONE ---
ADMIN_PASSWORD = "CorteDiFrancia"
PLAYERS_DEFAULT = ["Infame", "Cammellaccio", "Pierino", "Nicolino"]


# --- CONNESSIONE A GOOGLE SHEETS ---
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_url = st.secrets["private_sheet_url"]
    sheet = client.open_by_url(sheet_url).sheet1
    return sheet


# --- FUNZIONI LOAD/SAVE ---
def load_data():
    try:
        sheet = get_google_sheet()
        raw_data = sheet.acell('A1').value
        if not raw_data:
            return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}
        data = json.loads(raw_data)
        for d in data["giornate"].values():
            if "absent" not in d:
                d["absent"] = [False] * 4
        return data
    except Exception as e:
        st.error(f"Errore Database: {e}")
        return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}


def save_data(data):
    try:
        sheet = get_google_sheet()
        json_str = json.dumps(data)
        sheet.update_acell('A1', json_str)
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")


# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="🏆 Trofeo della Mole", page_icon="🏆", layout="wide")

if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'db' not in st.session_state: st.session_state.db = load_data()

# Ricarica manuale
if st.sidebar.button("🔄 Aggiorna Dati"):
    st.session_state.db = load_data()
    st.rerun()

data = st.session_state.db
players = data["config"]["players"]

# --- HEADER ---
st.title("🏆 Campionato Gran Premio di Torino - Circuito Corso Francia")
st.subheader("📍 Torino | Cloud Edition ☁️")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔐 Area Admin")
    if not st.session_state.is_admin:
        pwd = st.text_input("Password", type="password")
        if pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()
    else:
        st.success("Admin Connesso")
        if st.button("Logout"):
            st.session_state.is_admin = False
            st.rerun()

    st.markdown("---")
    st.header("📅 Calendario")

    if st.session_state.is_admin:
        if st.button("➕ Nuova Giornata", type="primary"):
            existing_nums = [int(k.split(" ")[1]) for k in data["giornate"].keys()]
            next_num = max(existing_nums) + 1 if existing_nums else 1
            new_day_key = f"Giornata {next_num}"

            data["giornate"][new_day_key] = {
                "races": {f"Gara {i + 1}": [0] * 4 for i in range(12)},
                "ko": [0] * 4, "basket": [0] * 4, "darts": [0] * 4, "absent": [False] * 4
            }
            save_data(data)
            st.toast(f"{new_day_key} Creata!", icon="✅")
            st.rerun()

    giornate_sorted = sorted(list(data["giornate"].keys()), key=lambda x: int(x.split(" ")[1]))

    if not giornate_sorted:
        st.warning("Nessuna giornata.")
        selected_day = None
    else:
        selected_day = st.selectbox("Visualizza:", giornate_sorted, index=len(giornate_sorted) - 1)

        if st.session_state.is_admin:
            st.markdown("---")
            st.subheader("🚫 Gestione Assenze")
            day_data_ref = data["giornate"][selected_day]
            updated_absent = False
            for i, player in enumerate(players):
                is_absent = st.checkbox(f"{player} Assente", value=day_data_ref["absent"][i],
                                        key=f"abs_{selected_day}_{i}")
                if is_absent != day_data_ref["absent"][i]:
                    day_data_ref["absent"][i] = is_absent
                    if is_absent:
                        day_data_ref["ko"][i] = 0;
                        day_data_ref["basket"][i] = 0;
                        day_data_ref["darts"][i] = 0
                        for r in range(12): day_data_ref["races"][f"Gara {r + 1}"][i] = 0
                    updated_absent = True
            if updated_absent: save_data(data); st.rerun()

        if st.session_state.is_admin:
            with st.expander("🗑️ Elimina Giornata"):
                if st.button("Conferma Eliminazione"):
                    del data["giornate"][selected_day]
                    new_dict = {}
                    rem_keys = sorted(data["giornate"].keys(), key=lambda x: int(x.split(" ")[1]))
                    for idx, k in enumerate(rem_keys): new_dict[f"Giornata {idx + 1}"] = data["giornate"][k]
                    data["giornate"] = new_dict;
                    save_data(data);
                    st.rerun()

# --- LOGICA ---
POINTS_MAP = {"1° Posto": 10, "2° Posto": 7, "3° Posto": 4, "4° Posto": 2, "Nessuno/0": 0}
REV_POINTS_MAP = {10: "1° Posto", 7: "2° Posto", 4: "3° Posto", 2: "4° Posto", 0: "Nessuno/0"}

if selected_day is None: st.stop()
day_data = data["giornate"][selected_day]
absent_flags = day_data["absent"]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["🏎️ GARE", "🎯 SKILL", "🥇 GIORNATA", "🌍 GENERALE", "📈 STATISTICHE", "📜 REGOLAMENTO"])

# TAB 1: GARE
with tab1:
    st.header(f"Risultati - {selected_day}")
    if st.session_state.is_admin:
        race_num = st.selectbox("Seleziona Gara:", [f"Gara {i + 1}" for i in range(12)])
        cols = st.columns(4)
        current_vals = day_data["races"][race_num]
        updated = False
        for i, player in enumerate(players):
            with cols[i]:
                disabled = absent_flags[i]
                label = f"{player} (ASSENTE)" if disabled else player
                current_label = REV_POINTS_MAP
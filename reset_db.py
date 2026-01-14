import json
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURA QUI I DATI DA SCRIVERE ---
DUMMY_DATA = {
  "config": {"players": ["Infame", "Cammellaccio", "Pierino", "Nicolino"]},
  "giornate": {
    "Giornata 1": {
      "races": {"Gara 1": [10, 7, 4, 2], "Gara 2": [7, 10, 2, 4], "Gara 3": [4, 2, 10, 7], "Gara 4": [2, 4, 7, 10], "Gara 5": [10, 2, 7, 4], "Gara 6": [7, 4, 2, 10], "Gara 7": [10, 7, 4, 2], "Gara 8": [4, 10, 2, 7], "Gara 9": [2, 7, 10, 4], "Gara 10": [7, 2, 4, 10], "Gara 11": [10, 4, 7, 2], "Gara 12": [4, 7, 2, 10]},
      "ko": [3, 5, 1, 2], "basket": [12, 18, 5, 14], "darts": [6, 8, 2, 10], "absent": [False, False, False, False]
    },
    "Giornata 2": {
      "races": {"Gara 1": [2, 4, 10, 7], "Gara 2": [4, 2, 7, 10], "Gara 3": [7, 10, 2, 4], "Gara 4": [10, 7, 4, 2], "Gara 5": [2, 10, 7, 4], "Gara 6": [4, 7, 10, 2], "Gara 7": [7, 2, 4, 10], "Gara 8": [10, 4, 2, 7], "Gara 9": [2, 7, 10, 4], "Gara 10": [4, 10, 7, 2], "Gara 11": [7, 2, 4, 10], "Gara 12": [10, 4, 2, 7]},
      "ko": [1, 2, 6, 4], "basket": [15, 10, 18, 8], "darts": [4, 6, 10, 2], "absent": [False, False, False, False]
    },
    "Giornata 3": {
      "races": {"Gara 1": [10, 7, 0, 4], "Gara 2": [7, 4, 0, 10], "Gara 3": [4, 10, 0, 7], "Gara 4": [10, 4, 0, 7], "Gara 5": [7, 10, 0, 4], "Gara 6": [4, 7, 0, 10], "Gara 7": [10, 4, 0, 7], "Gara 8": [7, 10, 0, 4], "Gara 9": [4, 7, 0, 10], "Gara 10": [10, 4, 0, 7], "Gara 11": [7, 10, 0, 4], "Gara 12": [4, 7, 0, 10]},
      "ko": [5, 3, 0, 6], "basket": [19, 14, 0, 16], "darts": [8, 10, 0, 8], "absent": [False, False, True, False]
    }
  }
}

# --- CONNESSIONE ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# Assumendo che tu stia eseguendo questo localmente e abbia accesso ai secrets tramite .streamlit/secrets.toml
# Se non funziona, puoi incollare qui il dizionario delle credenziali manualmente
creds_dict = dict(st.secrets["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(st.secrets["private_sheet_url"]).sheet1

# --- SCRITTURA ---
print("Scrittura in corso...")
json_str = json.dumps(DUMMY_DATA)
sheet.update_acell('A1', json_str)
print("✅ FATTO! Database ripopolato correttamente.")
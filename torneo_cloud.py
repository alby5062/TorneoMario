import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# --- CONFIGURAZIONE ---
ADMIN_PASSWORD = "mario"
PLAYERS_DEFAULT = ["Giocatore 1", "Giocatore 2", "Giocatore 3", "Giocatore 4"]


# --- CONNESSIONE A GOOGLE SHEETS ---
def get_google_sheet():
    # Definiamo lo scope
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # Recuperiamo le credenziali dai Secrets di Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    client = gspread.authorize(creds)

    # APRE IL FOGLIO TRAMITE URL (Salvatelo nei secrets o mettilo qui se il repo è privato)
    # Consiglio: Metti l'URL nei secrets come st.secrets["sheet_url"]
    sheet_url = st.secrets["private_sheet_url"]
    sheet = client.open_by_url(sheet_url).sheet1
    return sheet


# --- NUOVE FUNZIONI LOAD/SAVE ---
def load_data():
    try:
        sheet = get_google_sheet()
        # Legge tutto il contenuto della cella A1
        raw_data = sheet.acell('A1').value

        if not raw_data:
            # Se la cella è vuota, inizializza
            return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}

        data = json.loads(raw_data)

        # Migration fix per vecchi dati
        for d in data["giornate"].values():
            if "absent" not in d:
                d["absent"] = [False] * 4
        return data

    except Exception as e:
        st.error(f"Errore connessione Database: {e}")
        # Ritorna struttura vuota per non rompere l'app, ma avvisa
        return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}


def save_data(data):
    try:
        sheet = get_google_sheet()
        # Converte tutto il dizionario in una stringa JSON
        json_str = json.dumps(data)
        # Scrive tutto nella cella A1
        sheet.update_acell('A1', json_str)
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")


# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Campionato Corso Francia", page_icon="🏆", layout="wide")

# Inizializzazione stato
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

if 'db' not in st.session_state:
    st.session_state.db = load_data()

# Pulsante ricarica dati manuale (utile nel cloud)
if st.sidebar.button("🔄 Aggiorna Dati dal Cloud"):
    st.session_state.db = load_data()
    st.rerun()

data = st.session_state.db
players = data["config"]["players"]

# --- HEADER ---
st.title("🏆 Campionato Gran Premio Corso Francia")
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
                "ko": [0] * 4,
                "basket": [0] * 4,
                "darts": [0] * 4,
                "absent": [False] * 4
            }
            save_data(data)  # Salva su Google Sheets
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
            if updated_absent:
                save_data(data)
                st.rerun()

        if st.session_state.is_admin:
            with st.expander("🗑️ Elimina Giornata"):
                if st.button("Conferma Eliminazione"):
                    del data["giornate"][selected_day]
                    new_dict = {}
                    rem_keys = sorted(data["giornate"].keys(), key=lambda x: int(x.split(" ")[1]))
                    for idx, k in enumerate(rem_keys):
                        new_dict[f"Giornata {idx + 1}"] = data["giornate"][k]
                    data["giornate"] = new_dict
                    save_data(data)
                    st.rerun()

# --- LOGICA ---
POINTS_MAP = {"1° Posto": 10, "2° Posto": 7, "3° Posto": 4, "4° Posto": 2, "Nessuno/0": 0}
REV_POINTS_MAP = {10: "1° Posto", 7: "2° Posto", 4: "3° Posto", 2: "4° Posto", 0: "Nessuno/0"}

if selected_day is None: st.stop()
day_data = data["giornate"][selected_day]
absent_flags = day_data["absent"]

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏎️ GARE", "🎯 SKILL", "🥇 GIORNATA", "🌍 GENERALE", "📈 STATISTICHE"])

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
                current_label = REV_POINTS_MAP.get(current_vals[i], "Nessuno/0")
                val = st.selectbox(label, options=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"],
                                   index=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"].index(
                                       current_label),
                                   key=f"r_{race_num}_{i}", disabled=disabled)
                if not disabled:
                    new_score = POINTS_MAP[val]
                    if new_score != current_vals[i]:
                        day_data["races"][race_num][i] = new_score
                        updated = True
        if updated: save_data(data)
    summary = {"Gara": [f"Gara {i + 1}" for i in range(12)]}
    for i, player in enumerate(players):
        col_name = f"{player} (A)" if absent_flags[i] else player
        summary[col_name] = [REV_POINTS_MAP.get(day_data["races"][f"Gara {r + 1}"][i], "-") for r in range(12)]
    st.dataframe(pd.DataFrame(summary), use_container_width=True, height=400)

# TAB 2: SKILL
with tab2:
    st.header("Skill & Bonus")
    if st.session_state.is_admin:
        updated_sk = False
        c1, c2, c3 = st.columns(3)
        with c1:
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    v = st.number_input(f"KO {p}", value=day_data["ko"][i], key=f"ko_{i}")
                    if v != day_data["ko"][i]: day_data["ko"][i] = v; updated_sk = True
        with c2:
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    v = st.number_input(f"Basket {p}", max_value=9, value=day_data["basket"][i], key=f"bsk_{i}")
                    if v != day_data["basket"][i]: day_data["basket"][i] = v; updated_sk = True
        with c3:
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    v = st.number_input(f"Darts {p}", max_value=12, value=day_data["darts"][i], key=f"drt_{i}")
                    if v != day_data["darts"][i]: day_data["darts"][i] = v; updated_sk = True
        if updated_sk: save_data(data)
    sk_disp = []
    for i, p in enumerate(players):
        status = "ASSENTE" if absent_flags[i] else "Presente"
        sk_disp.append({"Giocatore": p, "Stato": status, "KO": day_data["ko"][i], "Basket": day_data["basket"][i],
                        "Darts": day_data["darts"][i]})
    st.dataframe(pd.DataFrame(sk_disp), use_container_width=True)

# TAB 3: GIORNATA
with tab3:
    d_stats = []
    for i, p in enumerate(players):
        if not absent_flags[i]:
            mk8 = sum(day_data["races"][f"Gara {r + 1}"][i] for r in range(12))
            skill = day_data["basket"][i] + day_data["darts"][i]
            d_stats.append({"Giocatore": p, "MK8": mk8, "Skill": skill, "KO": day_data["ko"][i], "TOTALE": mk8 + skill})
    if d_stats:
        df_d = pd.DataFrame(d_stats).sort_values(by=["TOTALE", "KO"], ascending=False).reset_index(drop=True)
        df_d.index += 1
        st.dataframe(df_d, use_container_width=True)
        st.success(f"🏆 Vincitore Giornata: **{df_d.iloc[0]['Giocatore']}**")
    else:
        st.info("Nessun giocatore presente.")

# TAB 4: GENERALE
with tab4:
    st.header("🌍 CLASSIFICA GENERALE")
    gen_stats = {p: {"Totale": 0, "KO": 0, "Presenze": 0} for p in players}
    for g_data in data["giornate"].values():
        g_absent = g_data.get("absent", [False] * 4)
        for i, p in enumerate(players):
            if not g_absent[i]:
                mk8 = sum(g_data["races"][f"Gara {r + 1}"][i] for r in range(12))
                skill = g_data["basket"][i] + g_data["darts"][i]
                ko = g_data["ko"][i]
                gen_stats[p]["Presenze"] += 1
                gen_stats[p]["Totale"] += (mk8 + skill)
                gen_stats[p]["KO"] += ko
    final_list = []
    for p, s in gen_stats.items():
        pg = s["Presenze"]
        media = round(s["Totale"] / pg, 2) if pg > 0 else 0.0
        final_list.append(
            {"Giocatore": p, "PG": pg, "Totale Punti": s["Totale"], "MEDIA PUNTI": media, "Totale KO": s["KO"]})
    df_gen = pd.DataFrame(final_list).sort_values(by=["MEDIA PUNTI", "Totale KO"], ascending=False).reset_index(
        drop=True)
    df_gen.index += 1
    st.dataframe(
        df_gen.style.format({"MEDIA PUNTI": "{:.2f}"}).background_gradient(subset=["MEDIA PUNTI"], cmap="Greens"),
        use_container_width=True, height=250)
    if not df_gen.empty:
        st.markdown(f"### 👑 Leader: <span style='color:#e0bc00'>{df_gen.iloc[0]['Giocatore']}</span>",
                    unsafe_allow_html=True)

# TAB 5: GRAFICI
with tab5:
    st.header("📈 Analytics")
    if len(data["giornate"]) > 0:
        history_rows = []
        cum_points = {p: 0 for p in players}
        cum_games = {p: 0 for p in players}

        for day_idx, day_key in enumerate(giornate_sorted):
            d_data = data["giornate"][day_key]
            d_absent = d_data.get("absent", [False] * 4)
            x_axis = day_idx + 1
            for i, p in enumerate(players):
                if not d_absent[i]:
                    points_today = sum(d_data["races"][f"Gara {r + 1}"][i] for r in range(12)) + d_data["basket"][i] + \
                                   d_data["darts"][i]
                    cum_points[p] += points_today;
                    cum_games[p] += 1
                current_avg = cum_points[p] / cum_games[p] if cum_games[p] > 0 else 0
                history_rows.append({"Giornata": f"G{x_axis}", "Giocatore": p, "Punti Totali": cum_points[p],
                                     "Media Punti": round(current_avg, 2),
                                     "Stato": "Assente" if d_absent[i] else "Presente"})

        df_hist = pd.DataFrame(history_rows)
        fig_avg = px.line(df_hist, x="Giornata", y="Media Punti", color="Giocatore", markers=True, symbol="Giocatore",
                          hover_data=["Stato"], title="Andamento Media Punti")
        st.plotly_chart(fig_avg, use_container_width=True)

        st.markdown("---")
        fig_tot = px.line(df_hist, x="Giornata", y="Punti Totali", color="Giocatore", markers=True,
                          title="Punti Totali Accumulati")
        st.plotly_chart(fig_tot, use_container_width=True)
    else:
        st.info("Dati insufficienti.")
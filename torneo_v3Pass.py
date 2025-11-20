import streamlit as st
import pandas as pd
import json
import os

# --- CONFIGURAZIONE SICUREZZA ---
# Modifica questa password con quella che vuoi usare sul tuo iPad
ADMIN_PASSWORD = "mario"

# --- CONFIGURAZIONE FILE E PERSISTENZA ---
FILE_DATI = "dati_campionato.json"
PLAYERS_DEFAULT = ["Giocatore 1", "Giocatore 2", "Giocatore 3", "Giocatore 4"]


# Funzione per caricare i dati
def load_data():
    if os.path.exists(FILE_DATI):
        with open(FILE_DATI, "r") as f:
            return json.load(f)
    else:
        return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}


# Funzione per salvare i dati
def save_data(data):
    with open(FILE_DATI, "w") as f:
        json.dump(data, f, indent=4)


# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Campionato Corso Francia", page_icon="🏆", layout="wide")

# Inizializzazione stato Admin
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Caricamento dati
if 'db' not in st.session_state:
    st.session_state.db = load_data()

data = st.session_state.db
players = data["config"]["players"]

# --- TITOLO ---
st.title("🏆 Campionato Gran Premio Corso Francia")
st.subheader("📍 Torino | Classifica Ufficiale")

# --- SIDEBAR: LOGIN & GESTIONE ---
with st.sidebar:
    st.header("🔐 Accesso Admin")

    # Logica Login
    if not st.session_state.is_admin:
        pwd = st.text_input("Inserisci Password Admin", type="password")
        if pwd == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()
        elif pwd:
            st.error("Password errata")

        st.info("👀 Modalità Spettatore Attiva")
    else:
        st.success("✅ Admin Loggato (iPad Mode)")
        if st.button("Esci (Logout)"):
            st.session_state.is_admin = False
            st.rerun()

    st.markdown("---")
    st.header("📅 Calendario")

    # --- SEZIONE ADMIN: CREAZIONE/MODIFICA ---
    if st.session_state.is_admin:
        with st.expander("✏️ Modifica Nomi Giocatori"):
            for i in range(4):
                new_name = st.text_input(f"Nome {i + 1}", players[i], key=f"p_name_{i}")
                if new_name != players[i]:
                    data["config"]["players"][i] = new_name
                    save_data(data)
                    st.rerun()
            players = data["config"]["players"]

        if st.button("➕ Inizia Nuova Giornata", type="primary"):
            existing_nums = [int(k.split(" ")[1]) for k in data["giornate"].keys()]
            next_num = max(existing_nums) + 1 if existing_nums else 1
            new_day_key = f"Giornata {next_num}"

            data["giornate"][new_day_key] = {
                "races": {f"Gara {i + 1}": [0] * 4 for i in range(12)},
                "ko": [0] * 4,
                "basket": [0] * 4,
                "darts": [0] * 4
            }
            save_data(data)
            st.toast(f"{new_day_key} Creata!", icon="✅")
            st.rerun()

    # --- SELEZIONE GIORNATA (Per tutti) ---
    giornate_unsorted = list(data["giornate"].keys())
    giornate_sorted = sorted(giornate_unsorted, key=lambda x: int(x.split(" ")[1]))

    if not giornate_sorted:
        st.warning("Nessuna giornata presente.")
        selected_day = None
    else:
        selected_day = st.selectbox("Visualizza Giornata:", giornate_sorted, index=len(giornate_sorted) - 1)

        # Tasto elimina solo per Admin
        if st.session_state.is_admin:
            st.markdown("---")
            with st.expander("🗑️ Elimina Giornata (Admin)", expanded=False):
                st.warning(f"Eliminare {selected_day}?")
                if st.button("Sì, ELIMINA", type="secondary"):
                    del data["giornate"][selected_day]
                    # Rinumerazione
                    new_giornate_dict = {}
                    remaining_keys = sorted(data["giornate"].keys(), key=lambda x: int(x.split(" ")[1]))
                    for index, old_key in enumerate(remaining_keys):
                        new_key = f"Giornata {index + 1}"
                        new_giornate_dict[new_key] = data["giornate"][old_key]
                    data["giornate"] = new_giornate_dict
                    save_data(data)
                    st.rerun()

# --- LOGICA DATI ---
POINTS_MAP = {"1° Posto": 10, "2° Posto": 7, "3° Posto": 4, "4° Posto": 2, "Nessuno/0": 0}
REV_POINTS_MAP = {10: "1° Posto", 7: "2° Posto", 4: "3° Posto", 2: "4° Posto", 0: "Nessuno/0"}

if selected_day is None:
    if not st.session_state.is_admin:
        st.info("Il torneo non è ancora iniziato. Attendi l'Admin.")
    st.stop()

day_data = data["giornate"][selected_day]

# --- INTERFACCIA TAB ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["🏎️ RISULTATI GARE", "🎯 SKILL & KO", "🥇 Classifica GIORNATA", "🌍 Classifica GENERALE"])

# TAB 1: GARE
with tab1:
    st.header(f"Risultati - {selected_day}")

    if st.session_state.is_admin:
        # --- VISTA ADMIN: INPUT ---
        race_num = st.selectbox("Seleziona Gara da Modificare:", [f"Gara {i + 1}" for i in range(12)])
        st.caption("🔒 Modalità Modifica Attiva")

        cols = st.columns(4)
        current_vals = day_data["races"][race_num]
        updated = False
        for i, player in enumerate(players):
            with cols[i]:
                current_label = REV_POINTS_MAP.get(current_vals[i], "Nessuno/0")
                val = st.selectbox(f"{player}",
                                   options=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"],
                                   index=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"].index(
                                       current_label),
                                   key=f"{selected_day}_{race_num}_{i}")
                new_score = POINTS_MAP[val]
                if new_score != current_vals[i]:
                    day_data["races"][race_num][i] = new_score
                    updated = True
        if updated:
            save_data(data)

        # Anteprima tabella completa per Admin
        st.divider()
        st.subheader("Riepilogo Gare Inserite")

    # --- VISTA COMUNE (Admin + Ospiti): TABELLA ---
    # Creiamo una tabella riassuntiva bella da vedere
    summary_data = {"Gara": [f"Gara {i + 1}" for i in range(12)]}
    for i, player in enumerate(players):
        summary_data[player] = [REV_POINTS_MAP.get(day_data["races"][f"Gara {r + 1}"][i], "-") for r in range(12)]

    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, height=460)

# TAB 2: SKILL E KO
with tab2:
    st.header(f"Bonus e Skill - {selected_day}")

    if st.session_state.is_admin:
        # --- VISTA ADMIN: INPUT ---
        updated_skill = False
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("💥 KO")
            for i, player in enumerate(players):
                val = st.number_input(f"KO {player}", min_value=0, value=day_data["ko"][i],
                                      key=f"ko_{selected_day}_{i}")
                if val != day_data["ko"][i]:
                    day_data["ko"][i] = val
                    updated_skill = True
        with c2:
            st.subheader("🏀 Basket")
            for i, player in enumerate(players):
                val = st.number_input(f"Bskt {player}", min_value=0, max_value=9, value=day_data["basket"][i],
                                      key=f"bsk_{selected_day}_{i}")
                if val != day_data["basket"][i]:
                    day_data["basket"][i] = val
                    updated_skill = True
        with c3:
            st.subheader("🎯 Darts")
            for i, player in enumerate(players):
                val = st.number_input(f"Darts {player}", min_value=0, max_value=12, value=day_data["darts"][i],
                                      key=f"drt_{selected_day}_{i}")
                if val != day_data["darts"][i]:
                    day_data["darts"][i] = val
                    updated_skill = True
        if updated_skill:
            save_data(data)
    else:
        # --- VISTA OSPITE: SOLO LETTURA ---
        skill_display = []
        for i, player in enumerate(players):
            skill_display.append({
                "Giocatore": player,
                "💥 KO Points": day_data["ko"][i],
                "🏀 Basket": day_data["basket"][i],
                "🎯 Darts": day_data["darts"][i]
            })
        st.dataframe(pd.DataFrame(skill_display), use_container_width=True)

# TAB 3: CLASSIFICA DI GIORNATA (Uguale per tutti)
with tab3:
    st.header(f"Classifica Parziale: {selected_day}")
    daily_stats = []
    for i, player in enumerate(players):
        mk8_sum = sum(day_data["races"][f"Gara {r + 1}"][i] for r in range(12))
        skill_sum = day_data["basket"][i] + day_data["darts"][i]
        ko_sum = day_data["ko"][i]
        daily_stats.append({
            "Giocatore": player,
            "Punti MK8": mk8_sum,
            "Skill": skill_sum,
            "Punti KO": ko_sum,
            "TOTALE GIORNATA": mk8_sum + skill_sum
        })

    df_day = pd.DataFrame(daily_stats).sort_values(by=["TOTALE GIORNATA", "Punti KO"], ascending=False).reset_index(
        drop=True)
    df_day.index += 1
    st.dataframe(df_day, use_container_width=True)
    if not df_day.empty:
        st.success(f"🏆 Leader provvisorio: **{df_day.iloc[0]['Giocatore']}**")

# TAB 4: CLASSIFICA GENERALE (Uguale per tutti)
with tab4:
    st.header("🌍 CLASSIFICA GENERALE CAMPIONATO")
    general_stats = {p: {"MK8": 0, "Skill": 0, "KO": 0, "Totale": 0} for p in players}

    for g_name, g_data in data["giornate"].items():
        for i, player in enumerate(players):
            mk8 = sum(g_data["races"][f"Gara {r + 1}"][i] for r in range(12))
            skill = g_data["basket"][i] + g_data["darts"][i]
            ko = g_data["ko"][i]
            general_stats[player]["MK8"] += mk8
            general_stats[player]["Skill"] += skill
            general_stats[player]["KO"] += ko
            general_stats[player]["Totale"] += (mk8 + skill)

    gen_list = []
    for p in players:
        s = general_stats[p]
        gen_list.append({
            "Giocatore": p,
            "Totale MK8": s["MK8"],
            "Totale Skill": s["Skill"],
            "Totale KO": s["KO"],
            "PUNTEGGIO TOTALE": s["Totale"]
        })

    df_gen = pd.DataFrame(gen_list).sort_values(by=["PUNTEGGIO TOTALE", "Totale KO"], ascending=False).reset_index(
        drop=True)
    df_gen.index += 1

    st.dataframe(df_gen, use_container_width=True, height=200)

    if not df_gen.empty:
        st.markdown(f"### 👑 CAMPIONE: <span style='color:#e0bc00'>{df_gen.iloc[0]['Giocatore']}</span>",
                    unsafe_allow_html=True)
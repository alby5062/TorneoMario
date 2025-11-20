import streamlit as st
import pandas as pd
import json
import os

# --- CONFIGURAZIONE FILE E PERSISTENZA ---
FILE_DATI = "dati_campionato.json"
PLAYERS_DEFAULT = ["Giocatore 1", "Giocatore 2", "Giocatore 3", "Giocatore 4"]


# Funzione per caricare i dati
def load_data():
    if os.path.exists(FILE_DATI):
        with open(FILE_DATI, "r") as f:
            return json.load(f)
    else:
        # Struttura iniziale vuota
        return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}


# Funzione per salvare i dati
def save_data(data):
    with open(FILE_DATI, "w") as f:
        json.dump(data, f, indent=4)


# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Campionato Corso Francia", page_icon="🏆", layout="wide")

# Carichiamo i dati all'avvio
if 'db' not in st.session_state:
    st.session_state.db = load_data()

data = st.session_state.db
players = data["config"]["players"]

# --- TITOLO ---
st.title("🏆 Campionato Gran Premio Corso Francia")
st.subheader("📍 Torino | Classifica Generale e di Giornata")

# --- SIDEBAR: GESTIONE GIORNATE ---
with st.sidebar:
    st.header("📅 Gestione Calendario")

    # Gestione Nomi Giocatori
    with st.expander("✏️ Modifica Nomi Giocatori"):
        for i in range(4):
            new_name = st.text_input(f"Nome {i + 1}", players[i], key=f"p_name_{i}")
            if new_name != players[i]:
                data["config"]["players"][i] = new_name
                save_data(data)
                st.rerun()
        players = data["config"]["players"]  # Aggiorna variabile locale

    st.markdown("---")

    # CREA NUOVA GIORNATA
    if st.button("➕ Inizia Nuova Giornata", type="primary"):
        # Trova il prossimo numero disponibile
        existing_nums = [int(k.split(" ")[1]) for k in data["giornate"].keys()]
        next_num = max(existing_nums) + 1 if existing_nums else 1
        new_day_key = f"Giornata {next_num}"

        # Struttura dati per una singola giornata
        data["giornate"][new_day_key] = {
            "races": {f"Gara {i + 1}": [0] * 4 for i in range(12)},
            "ko": [0] * 4,
            "basket": [0] * 4,
            "darts": [0] * 4
        }
        save_data(data)
        st.toast(f"{new_day_key} Creata con successo!", icon="✅")
        st.rerun()

    # SELEZIONA O ELIMINA GIORNATA
    # Ordiniamo le giornate per numero
    giornate_unsorted = list(data["giornate"].keys())
    giornate_sorted = sorted(giornate_unsorted, key=lambda x: int(x.split(" ")[1]))

    if not giornate_sorted:
        st.warning("Nessuna giornata presente.")
        selected_day = None
    else:
        # Seleziona l'ultima giornata per default
        selected_day = st.selectbox("Seleziona Giornata da gestire:", giornate_sorted, index=len(giornate_sorted) - 1)
        st.markdown(f"Stai modificando: **{selected_day}**")

        st.markdown("---")

        # --- ZONA PERICOLOSA: ELIMINAZIONE ---
        with st.expander("🗑️ Elimina Giornata", expanded=False):
            st.warning(f"Vuoi davvero eliminare {selected_day}?")
            if st.button("Sì, ELIMINA", type="secondary"):
                # 1. Elimina la giornata
                del data["giornate"][selected_day]

                # 2. Rinumerazione Automatica
                new_giornate_dict = {}
                remaining_keys = sorted(data["giornate"].keys(), key=lambda x: int(x.split(" ")[1]))

                for index, old_key in enumerate(remaining_keys):
                    new_key = f"Giornata {index + 1}"
                    new_giornate_dict[new_key] = data["giornate"][old_key]

                data["giornate"] = new_giornate_dict
                save_data(data)
                st.rerun()

# --- LOGICA PUNTEGGI ---
POINTS_MAP = {"1° Posto": 10, "2° Posto": 7, "3° Posto": 4, "4° Posto": 2, "Nessuno/0": 0}
REV_POINTS_MAP = {10: "1° Posto", 7: "2° Posto", 4: "3° Posto", 2: "4° Posto", 0: "Nessuno/0"}

# Se non ci sono giornate, stop qui
if selected_day is None:
    st.info("👈 Crea una nuova giornata dal menu a sinistra per iniziare.")
    st.stop()

day_data = data["giornate"][selected_day]

# --- INTERFACCIA PRINCIPALE ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["🏎️ GARE (Giornata)", "🎯 SKILL & KO (Giornata)", "🥇 Classifica GIORNATA", "🌍 Classifica GENERALE"])

# TAB 1: INPUT GARE
with tab1:
    st.header(f"Inserimento Risultati - {selected_day}")

    race_num = st.selectbox("Seleziona Gara:", [f"Gara {i + 1}" for i in range(12)])
    st.caption("Salvataggio automatico ad ogni modifica.")

    cols = st.columns(4)
    current_vals = day_data["races"][race_num]

    updated = False
    for i, player in enumerate(players):
        with cols[i]:
            current_label = REV_POINTS_MAP.get(current_vals[i], "Nessuno/0")
            val = st.selectbox(f"{player}",
                               options=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"],
                               index=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"].index(current_label),
                               key=f"{selected_day}_{race_num}_{i}")

            new_score = POINTS_MAP[val]
            if new_score != current_vals[i]:
                day_data["races"][race_num][i] = new_score
                updated = True

    if updated:
        save_data(data)

# TAB 2: SKILL E KO
with tab2:
    st.header(f"Bonus e Skill Challenge - {selected_day}")
    updated_skill = False

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("💥 Punti K.O.")
        for i, player in enumerate(players):
            val = st.number_input(f"KO {player}", min_value=0, value=day_data["ko"][i], key=f"ko_{selected_day}_{i}")
            if val != day_data["ko"][i]:
                day_data["ko"][i] = val
                updated_skill = True

    with c2:
        st.subheader("🏀 Canestro (Max 9)")
        for i, player in enumerate(players):
            val = st.number_input(f"Basket {player}", min_value=0, max_value=9, value=day_data["basket"][i],
                                  key=f"bsk_{selected_day}_{i}")
            if val != day_data["basket"][i]:
                day_data["basket"][i] = val
                updated_skill = True

    with c3:
        st.subheader("🎯 Freccette (Max 12)")
        for i, player in enumerate(players):
            val = st.number_input(f"Darts {player}", min_value=0, max_value=12, value=day_data["darts"][i],
                                  key=f"drt_{selected_day}_{i}")
            if val != day_data["darts"][i]:
                day_data["darts"][i] = val
                updated_skill = True

    if updated_skill:
        save_data(data)

# TAB 3: CLASSIFICA DI GIORNATA
with tab3:
    st.header(f"Classifica Parziale: {selected_day}")

    daily_stats = []
    for i, player in enumerate(players):
        mk8_sum = sum(day_data["races"][f"Gara {r + 1}"][i] for r in range(12))
        skill_sum = day_data["basket"][i] + day_data["darts"][i]
        ko_sum = day_data["ko"][i]
        total = mk8_sum + skill_sum

        daily_stats.append({
            "Giocatore": player,
            "Punti MK8": mk8_sum,
            "Skill": skill_sum,
            "Punti KO": ko_sum,
            "TOTALE GIORNATA": total
        })

    df_day = pd.DataFrame(daily_stats)
    df_day = df_day.sort_values(by=["TOTALE GIORNATA", "Punti KO"], ascending=False).reset_index(drop=True)
    df_day.index += 1
    st.dataframe(df_day, use_container_width=True)

    if not df_day.empty:
        st.success(f"🏆 Vincitore di {selected_day}: **{df_day.iloc[0]['Giocatore']}**")

# TAB 4: CLASSIFICA GENERALE (CAMPIONATO)
with tab4:
    st.header("🌍 CLASSIFICA GENERALE CAMPIONATO")
    # FIX: Usiamo len(data["giornate"]) invece della variabile lista non definita
    st.markdown(f"Totale giornate giocate: **{len(data['giornate'])}**")

    general_stats = {p: {"MK8": 0, "Skill": 0, "KO": 0, "Totale": 0} for p in players}

    # Aggregazione dati
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

    df_gen = pd.DataFrame(gen_list)
    df_gen = df_gen.sort_values(by=["PUNTEGGIO TOTALE", "Totale KO"], ascending=False).reset_index(drop=True)
    df_gen.index += 1

    st.dataframe(df_gen, use_container_width=True, height=200)

    if not df_gen.empty:
        leader = df_gen.iloc[0]['Giocatore']
        gap = 0
        if len(df_gen) > 1:
            gap = df_gen.iloc[0]['PUNTEGGIO TOTALE'] - df_gen.iloc[1]['PUNTEGGIO TOTALE']

        st.balloons()
        st.markdown(f"### 👑 CAMPIONE ATTUALE: <span style='color:#e0bc00'>{leader}</span>", unsafe_allow_html=True)
        if gap > 0:
            st.info(f"Vantaggio sul secondo classificato: **{gap} punti**")
        else:
            st.warning("Pareggio in vetta!")
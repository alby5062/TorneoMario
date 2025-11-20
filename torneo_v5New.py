import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

# --- CONFIGURAZIONE SICUREZZA ---
ADMIN_PASSWORD = "CorteDiFrancia"

# --- CONFIGURAZIONE FILE ---
FILE_DATI = "dati_campionato.json"
PLAYERS_DEFAULT = ["Infame", "Cammellaccio", "Pierino", "Nicolino"]


# --- FUNZIONI GESTIONE DATI ---
def load_data():
    if os.path.exists(FILE_DATI):
        with open(FILE_DATI, "r") as f:
            data = json.load(f)
            # MIGRATION FIX: Assicura compatibilità
            for d in data["giornate"].values():
                if "absent" not in d:
                    d["absent"] = [False] * 4
            return data
    else:
        return {"config": {"players": PLAYERS_DEFAULT}, "giornate": {}}


def save_data(data):
    with open(FILE_DATI, "w") as f:
        json.dump(data, f, indent=4)


# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="🏆 Trofeo della Mole", page_icon="🏆", layout="wide")

# Inizializzazione stato
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

if 'db' not in st.session_state:
    st.session_state.db = load_data()

data = st.session_state.db
players = data["config"]["players"]

# --- HEADER ---
st.title("🏆 Campionato Gran Premio di Torino - Circuito Corso Francia")
st.subheader("📍 Torino | Classifica Basata su MEDIA PUNTI")

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
                        day_data_ref["ko"][i] = 0
                        day_data_ref["basket"][i] = 0
                        day_data_ref["darts"][i] = 0
                        for r in range(12):
                            day_data_ref["races"][f"Gara {r + 1}"][i] = 0
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

if selected_day is None:
    st.stop()

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
    st.header("🌍 CLASSIFICA GENERALE (Per Media)")
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

# TAB 5: GRAFICI AVANZATI (PLOTLY)
with tab5:
    st.header("📈 Analisi Andamento Campionato")

    if len(data["giornate"]) > 0:
        # --- PREPARAZIONE DATI PER PLOTLY ---
        # Creiamo un dataset "lungo" che è facile da graficare
        # Struttura: Giornata | Giocatore | TotaleProgressivo | MediaProgressiva

        history_rows = []

        # Dizionari per tenere i totali accumulati
        cum_points = {p: 0 for p in players}
        cum_games = {p: 0 for p in players}

        # Ordine cronologico
        for day_idx, day_key in enumerate(giornate_sorted):
            d_data = data["giornate"][day_key]
            d_absent = d_data.get("absent", [False] * 4)

            # Numero della giornata per l'asse X (es. 1, 2, 3...)
            x_axis = day_idx + 1

            for i, p in enumerate(players):
                if not d_absent[i]:
                    # Calcoli se presente
                    daily_mk8 = sum(d_data["races"][f"Gara {r + 1}"][i] for r in range(12))
                    daily_skill = d_data["basket"][i] + d_data["darts"][i]
                    points_today = daily_mk8 + daily_skill

                    cum_points[p] += points_today
                    cum_games[p] += 1

                # Calcolo media attuale (evita divisione per zero)
                current_avg = cum_points[p] / cum_games[p] if cum_games[p] > 0 else 0

                history_rows.append({
                    "Giornata": f"G{x_axis}",  # Etichetta asse X
                    "NumeroGiornata": x_axis,  # Per ordinamento
                    "Giocatore": p,
                    "Punti Totali": cum_points[p],
                    "Media Punti": round(current_avg, 2),
                    "Stato": "Assente" if d_absent[i] else "Presente"
                })

        df_hist = pd.DataFrame(history_rows)

        # --- GRAFICO 1: ANDAMENTO MEDIA PUNTI (Il più importante) ---
        st.subheader("📊 Andamento Media Punti (Decisivo per la Vittoria)")
        st.caption("Questo grafico mostra la 'forma' del giocatore. Chi sta salendo e chi sta scendendo.")

        fig_avg = px.line(
            df_hist,
            x="Giornata",
            y="Media Punti",
            color="Giocatore",
            markers=True,  # Aggiunge i pallini
            symbol="Giocatore",  # Simboli diversi per ogni giocatore (quadrato, cerchio...)
            hover_data=["Stato"],  # Mostra se era assente nel tooltip
            title="Evoluzione della Media Punti nel Tempo"
        )
        fig_avg.update_layout(xaxis_title=None, hovermode="x unified")  # Migliora il tooltip
        st.plotly_chart(fig_avg, use_container_width=True)

        st.markdown("---")

        # --- GRAFICO 2: PUNTI TOTALI (CUMULATIVI) ---
        st.subheader("🏁 La Corsa ai Punti (Totale Accumulato)")
        st.caption("Chi ha fatto più punti in assoluto (influenzato dalle presenze).")

        fig_tot = px.line(
            df_hist,
            x="Giornata",
            y="Punti Totali",
            color="Giocatore",
            markers=True,
            line_shape="spline",  # Rende le linee un po' curve e morbide
            title="Crescita del Punteggio Totale"
        )
        fig_tot.update_layout(xaxis_title=None, hovermode="x unified")
        st.plotly_chart(fig_tot, use_container_width=True)

        # --- GRAFICO 3: SKILL BREAKDOWN (Barre Orizzontali) ---
        st.markdown("---")
        st.subheader("🎯 Specializzazioni")

        # Ricalcoliamo i totali skill
        skill_stats = []
        for p in players:
            tot_ko = 0
            tot_bsk = 0
            tot_drt = 0
            for g_data in data["giornate"].values():
                idx = players.index(p)
                tot_ko += g_data["ko"][idx]
                tot_bsk += g_data["basket"][idx]
                tot_drt += g_data["darts"][idx]

            skill_stats.append({"Giocatore": p, "Tipo": "K.O.", "Punti": tot_ko})
            skill_stats.append({"Giocatore": p, "Tipo": "Basket", "Punti": tot_bsk})
            skill_stats.append({"Giocatore": p, "Tipo": "Freccette", "Punti": tot_drt})

        df_skills = pd.DataFrame(skill_stats)

        fig_skill = px.bar(
            df_skills,
            x="Punti",
            y="Giocatore",
            color="Tipo",
            orientation='h',  # Barre orizzontali
            title="Chi fa punti e come?",
            text_auto=True  # Scrive i numeri sulle barre
        )
        st.plotly_chart(fig_skill, use_container_width=True)

    else:
        st.info("Non ci sono ancora dati sufficienti per generare i grafici.")
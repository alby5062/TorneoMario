import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

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
st.set_page_config(page_title="🏆GP Torino", page_icon="🏆", layout="wide")

if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'db' not in st.session_state: st.session_state.db = load_data()

# Ricarica manuale
if st.sidebar.button("🔄 Aggiorna Dati"):
    st.session_state.db = load_data()
    st.rerun()

data = st.session_state.db
players = data["config"]["players"]

# --- HEADER ---
st.title("🏆 Gran Premio di Torino - Trofeo della Mole")
st.subheader("📍 Circuito Corso Francia, Torino | Cloud Edition ☁️")

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

# --- LOGICA PUNTEGGI AGGIORNATA ---
POINTS_MAP = {"1° Posto": 4, "2° Posto": 3, "3° Posto": 2, "4° Posto": 1, "Nessuno/0": 0}
REV_POINTS_MAP = {4: "1° Posto", 3: "2° Posto", 2: "3° Posto", 1: "4° Posto", 0: "Nessuno/0"}

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
                current_label = REV_POINTS_MAP.get(current_vals[i], "Nessuno/0")
                val = st.selectbox(label, options=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"],
                                   index=["1° Posto", "2° Posto", "3° Posto", "4° Posto", "Nessuno/0"].index(
                                       current_label),
                                   key=f"r_{race_num}_{i}", disabled=disabled)
                if not disabled:
                    new_score = POINTS_MAP[val]
                    if new_score != current_vals[i]: day_data["races"][race_num][i] = new_score; updated = True
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
                    v = st.number_input(f"Basket {p}", max_value=20, value=day_data["basket"][i], key=f"bsk_{i}")
                    if v != day_data["basket"][i]: day_data["basket"][i] = v; updated_sk = True
        with c3:
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    v = st.number_input(f"Darts {p}", max_value=10, value=day_data["darts"][i], key=f"drt_{i}")
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
    st.header("📱 Statistiche Rapide")

    if len(data["giornate"]) > 0:
        # --- 1. LE "FIGURINE" ---
        st.subheader("🔥 Forma Attuale")
        cols = st.columns(2)

        for p in players:
            tot = 0;
            count = 0
            prev_tot = 0;
            prev_count = 0
            days_list = giornate_sorted

            for d in days_list:
                d_data = data["giornate"][d]
                if not d_data.get("absent", [False] * 4)[players.index(p)]:
                    p_pts = sum(d_data["races"][f"Gara {r + 1}"][players.index(p)] for r in range(12)) + \
                            d_data["basket"][players.index(p)] + d_data["darts"][players.index(p)]
                    tot += p_pts;
                    count += 1

            for d in days_list[:-1]:
                d_data = data["giornate"][d]
                if not d_data.get("absent", [False] * 4)[players.index(p)]:
                    p_pts = sum(d_data["races"][f"Gara {r + 1}"][players.index(p)] for r in range(12)) + \
                            d_data["basket"][players.index(p)] + d_data["darts"][players.index(p)]
                    prev_tot += p_pts;
                    prev_count += 1

            curr_avg = tot / count if count > 0 else 0
            prev_avg = prev_tot / prev_count if prev_count > 0 else 0
            diff = curr_avg - prev_avg if prev_count > 0 else 0

            with cols[players.index(p) % 2]:
                st.metric(label=p, value=f"{curr_avg:.2f}", delta=f"{diff:.2f}", delta_color="normal")

        st.markdown("---")

        # --- 2. GRAFICO LINEE ---
        st.subheader("📈 La Scalata")

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
                history_rows.append({"Giornata": f"G{x_axis}", "Giocatore": p, "Media": round(current_avg, 2)})

        df_hist = pd.DataFrame(history_rows)
        fig_line = px.line(df_hist, x="Giornata", y="Media", color="Giocatore", markers=True, symbol="Giocatore")
        fig_line.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=20, b=20), xaxis_title=None, yaxis_title=None, showlegend=True
        )
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")

        # --- 3. GRAFICO RADAR (VITTORIE/BASKET/DARTS) ---
        st.subheader("🕹️ Stile di Gioco")

        style_totals = {p: {"Wins": 0, "Basket": 0, "Darts": 0} for p in players}

        for g_data in data["giornate"].values():
            for i, p in enumerate(players):
                style_totals[p]["Basket"] += g_data["basket"][i]
                style_totals[p]["Darts"] += g_data["darts"][i]

                # Conta le vittorie (ORA VALGONO 4 PUNTI)
                wins_today = 0
                for race_scores in g_data["races"].values():
                    if race_scores[i] == 4:  # <-- AGGIORNATO PER IL NUOVO PUNTEGGIO
                        wins_today += 1
                style_totals[p]["Wins"] += wins_today

        categories = ['Vittorie (1° Posti)', 'Canestri', 'Freccette']
        selected_player_radar = st.selectbox("Analizza Giocatore:", players)

        vals = [
            style_totals[selected_player_radar]["Wins"],
            style_totals[selected_player_radar]["Basket"],
            style_totals[selected_player_radar]["Darts"]
        ]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=vals, theta=categories, fill='toself', name=selected_player_radar, line_color='#e0bc00'
        ))

        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(max(vals, default=5), 5)])),
            showlegend=False, margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    else:
        st.info("Dati insufficienti.")

# TAB 6: REGOLAMENTO
with tab6:
    st.markdown("# 📜 Regolamento Ufficiale")
    st.markdown("### Gran Premio di Torino – 🏆 Trofeo della Mole")

    st.markdown("---")
    st.subheader("1. Struttura del Campionato")
    st.markdown("""
    * Il torneo è strutturato a **Giornate**.
    * Ogni Giornata prevede **12 Gare** di Mario Kart 8 + **Skill Challenge**.
    * La classifica non si azzera, ma si accumula nel tempo.
    """)

    st.subheader("2. Impostazioni di Gara")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Impostazioni gioco:**")
        st.markdown("- Cilindrata: **150cc**\n- Oggetti: **Estremi**\n- CPU: **Nessuna**\n- Piste: **Casuali**")
    with c2:
        st.markdown("**Punteggi Gara (Short):**")
        st.markdown(
            "| Pos | Punti |\n|---|---|\n| 🥇 1° | **4** |\n| 🥈 2° | **3** |\n| 🥉 3° | **2** |\n| 💩 4° | **1** |")

    st.subheader("3. 🏀🎯 La Resa dei Conti - Skill Challenge")
    st.markdown("""
    * **🏀 Canestro (Max 20pt):** 10 tiri. (Semplice: **1pt**, Speciale: **2pt**)
    * **🎯 Freccette (Max 10pt):** 6 lanci. (Punteggi a fasce)
    """)

    st.divider()
    st.subheader("4. ⚖️ Il Calcolo della Classifica (MEDIA PUNTI)")
    st.latex(r"\text{Media Punti} = \frac{\text{Totale Punti Accumulati}}{\text{Numero di Giornate Giocate}}")

    st.divider()
    st.subheader("5. 📈 Statistiche")
    st.markdown("**Forma Attuale (Delta):**")
    st.latex(r"\text{Delta} = \text{Media Oggi} - \text{Media Ieri}")
    col_info1, col_info2 = st.columns(2)
    with col_info1: st.success("**🟢 Verde (+):** Miglioramento")
    with col_info2: st.error("**🔴 Rosso (-):** Peggioramento")
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
                "basket": [0] * 4, "darts": [0] * 4, "absent": [False] * 4
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

# --- LOGICA PUNTEGGI ---
POINTS_MAP = {"1° Posto": 12, "2° Posto": 9, "3° Posto": 6, "4° Posto": 3, "Nessuno/0": 0}
REV_POINTS_MAP = {12: "1° Posto", 9: "2° Posto", 6: "3° Posto", 3: "4° Posto", 0: "Nessuno/0"}
# SKILL POINTS (Can map rank to points directly or reuse POINTS_MAP if keys match needed logic)
SKILL_POINTS = {1: 12, 2: 9, 3: 6, 4: 3}

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
    st.info("Punteggi: 1°=12, 2°=9, 3°=6, 4°=3. Bonus = +5 punti.")
    
    if st.session_state.is_admin:
        updated_sk = False
        c1, c2 = st.columns(2)
        
        # BASKET
        with c1:
            st.subheader("🏀 Basket")
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    # Determine current rank/bonus from stored score if possible, or default to 4th/NoBonus
                    # Since we store TOTAL points, we can't easily reverse engineer without stored state.
                    # We will just show inputs to overwrite.
                    st.markdown(f"**{p}**")
                    col_rank, col_bonus = st.columns([2, 1])
                    with col_rank:
                        rank_bsk = st.selectbox(f"Posizione {p}", options=[1, 2, 3, 4], key=f"rank_bsk_{i}")
                    with col_bonus:
                        bonus_bsk = st.checkbox(f"Bonus (>=20pt)", key=f"bonus_bsk_{i}")
                    
                    calc_score = SKILL_POINTS[rank_bsk] + (5 if bonus_bsk else 0)
                    # We only update if it looks like a NEW interaction or we trust the user inputs match current state.
                    # Problem: on refresh, selectbox resets to default (index 0 -> 1st place) if we don't bind 'value' or 'index'.
                    # But we don't store rank/bonus separately. 
                    # DECISION: Just let the user overwrite. It shows "1" by default. 
                    # Better: display current points next to it.
                    st.caption(f"Salverà: {calc_score} pt (Attuale: {day_data['basket'][i]})")
                    
                    # We need a button to "Apply" or just apply if changed? 
                    # Since we can't reconstruct state, let's add a "Salva" button per section or global?
                    # Auto-update might be annoying if it resets to 12 pts immediately.
                    
        # DARTS
        with c2:
            st.subheader("🎯 Freccette")
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    st.markdown(f"**{p}**")
                    col_rank_d, col_bonus_d = st.columns([2, 1])
                    with col_rank_d:
                        rank_drt = st.selectbox(f"Posizione {p}", options=[1, 2, 3, 4], key=f"rank_drt_{i}")
                    with col_bonus_d:
                        bonus_drt = st.checkbox(f"Bonus (<=3 Rnd)", key=f"bonus_drt_{i}")
                    
                    calc_score_d = SKILL_POINTS[rank_drt] + (5 if bonus_drt else 0)
                    st.caption(f"Salverà: {calc_score_d} pt (Attuale: {day_data['darts'][i]})")

        if st.button("💾 Salva Risultati Skill"):
            # Apply Basket
            for i, p in enumerate(players):
                if not absent_flags[i]:
                    # Retrieving values from session state using keys
                    r_b = st.session_state[f"rank_bsk_{i}"]
                    b_b = st.session_state[f"bonus_bsk_{i}"]
                    day_data["basket"][i] = SKILL_POINTS[r_b] + (5 if b_b else 0)
                    
                    r_d = st.session_state[f"rank_drt_{i}"]
                    b_d = st.session_state[f"bonus_drt_{i}"]
                    day_data["darts"][i] = SKILL_POINTS[r_d] + (5 if b_d else 0)
            
            save_data(data)
            st.success("Salvataggio completato!")
            st.rerun()

    sk_disp = []
    for i, p in enumerate(players):
        status = "ASSENTE" if absent_flags[i] else "Presente"
        sk_disp.append(
            {"Giocatore": p, "Stato": status, "Basket (Pt)": day_data["basket"][i], "Darts (Pt)": day_data["darts"][i]})
    st.dataframe(pd.DataFrame(sk_disp), use_container_width=True)

# TAB 3: GIORNATA
with tab3:
    d_stats = []
    perfect_score_player = None

    for i, p in enumerate(players):
        if not absent_flags[i]:
            race_points = [day_data["races"][f"Gara {r + 1}"][i] for r in range(12)]
            mk8_sum = sum(race_points)
            skill = day_data["basket"][i] + day_data["darts"][i]

            bonus_grand_slam = 0
            if race_points.count(12) == 12:
                bonus_grand_slam = 10
                perfect_score_player = p

            total = mk8_sum + skill + bonus_grand_slam

            d_stats.append({
                "Giocatore": p,
                "MK8": mk8_sum,
                "Skill": skill,
                "Bonus 12/12": f"+{bonus_grand_slam}" if bonus_grand_slam > 0 else "-",
                "TOTALE": total
            })

    if d_stats:
        df_d = pd.DataFrame(d_stats).sort_values(by=["TOTALE"], ascending=False).reset_index(drop=True)
        df_d.index += 1
        st.dataframe(df_d, use_container_width=True)

        if perfect_score_player:
            st.balloons()
            st.markdown(f"## 🤯 INCREDIBILE! {perfect_score_player} HA FATTO 12 SU 12! (+10 PUNTI)")

        st.success(f"🏆 Vincitore Giornata: **{df_d.iloc[0]['Giocatore']}**")
    else:
        st.info("Nessun giocatore presente.")

# TAB 4: GENERALE
with tab4:
    st.header("🌍 CLASSIFICA GENERALE")
    gen_stats = {p: {"Totale": 0, "Presenze": 0} for p in players}
    for g_data in data["giornate"].values():
        g_absent = g_data.get("absent", [False] * 4)
        for i, p in enumerate(players):
            if not g_absent[i]:
                race_points = [g_data["races"][f"Gara {r + 1}"][i] for r in range(12)]
                mk8 = sum(race_points)
                grand_slam = 10 if race_points.count(12) == 12 else 0
                skill = g_data["basket"][i] + g_data["darts"][i]

                gen_stats[p]["Presenze"] += 1
                gen_stats[p]["Totale"] += (mk8 + skill + grand_slam)

    final_list = []
    for p, s in gen_stats.items():
        pg = s["Presenze"]
        media = round(s["Totale"] / pg, 2) if pg > 0 else 0.0
        final_list.append(
            {"Giocatore": p, "PG": pg, "Totale Punti": s["Totale"], "MEDIA PUNTI": media})

    df_gen = pd.DataFrame(final_list).sort_values(by=["MEDIA PUNTI", "Totale Punti"], ascending=False).reset_index(
        drop=True)
    df_gen.index += 1
    st.dataframe(
        df_gen.style.format({"MEDIA PUNTI": "{:.2f}"}).background_gradient(subset=["MEDIA PUNTI"], cmap="Greens"),
        use_container_width=True, height=250)
    if not df_gen.empty:
        st.markdown(f"### 👑 Leader: <span style='color:#e0bc00'>{df_gen.iloc[0]['Giocatore']}</span>",
                    unsafe_allow_html=True)

# TAB 5: STATISTICHE
with tab5:
    st.header("📱 Statistiche Rapide")

    if len(data["giornate"]) > 0:
        # --- 1. LE "FIGURINE" (Forma ultime 3 gare) ---
        st.subheader("🔥 Forma Attuale (Ultime 3 Presenze)")
        cols = st.columns(2)

        for p in players:
            scores_history = []
            for d in giornate_sorted:
                d_data = data["giornate"][d]
                idx = players.index(p)
                if not d_data.get("absent", [False] * 4)[idx]:
                    r_pts = [d_data["races"][f"Gara {r + 1}"][idx] for r in range(12)]
                    bonus = 10 if r_pts.count(12) == 12 else 0
                    day_total = sum(r_pts) + d_data["basket"][idx] + d_data["darts"][idx] + bonus
                    scores_history.append(day_total)

            if not scores_history:
                curr_form = 0;
                diff = 0
            else:
                last_3_games = scores_history[-3:]
                curr_form = sum(last_3_games) / len(last_3_games)

                if len(scores_history) > 1:
                    prev_3_games = scores_history[:-1][-3:]
                    prev_form = sum(prev_3_games) / len(prev_3_games)
                    diff = curr_form - prev_form
                else:
                    diff = 0

            with cols[players.index(p) % 2]:
                st.metric(label=p, value=f"{curr_form:.1f}", delta=f"{diff:.1f}", delta_color="normal")

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
                    r_pts = [d_data["races"][f"Gara {r + 1}"][i] for r in range(12)]
                    bonus = 10 if r_pts.count(12) == 12 else 0
                    points_today = sum(r_pts) + d_data["basket"][i] + d_data["darts"][i] + bonus

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

        # --- 3. GRAFICO RADAR (NORMALIZZATO IN %) ---
        st.subheader("🕹️ Stile di Gioco (Efficienza %)")
        st.caption("Confronto proporzionale: quanto sei vicino alla perfezione in ogni categoria?")

        # Inizializziamo i contatori per i totali reali e i massimi possibili
        # "Wins": 12 possibili per giornata
        # "Basket": 30 possibili per giornata
        # "Darts": 10 possibili per giornata

        style_stats = {p: {
            "Wins_Actual": 0, "Wins_Max": 0,
            "Basket_Actual": 0, "Basket_Max": 0,
            "Darts_Actual": 0, "Darts_Max": 0
        } for p in players}

        for g_data in data["giornate"].values():
            for i, p in enumerate(players):
                # Se il giocatore era presente, incrementiamo i suoi contatori e i massimi possibili
                if not g_data.get("absent", [False] * 4)[i]:
                    # Basket
                    style_stats[p]["Basket_Actual"] += g_data["basket"][i]
                    style_stats[p]["Basket_Max"] += 17  # Max giornaliero basket (12 + 5)

                    # Darts
                    style_stats[p]["Darts_Actual"] += g_data["darts"][i]
                    style_stats[p]["Darts_Max"] += 17  # Max giornaliero darts (12 + 5)

                    # Wins (Conta i primi posti)
                    wins_today = 0
                    for race_scores in g_data["races"].values():
                        if race_scores[i] == 12:
                            wins_today += 1
                    style_stats[p]["Wins_Actual"] += wins_today
                    style_stats[p]["Wins_Max"] += 12  # Max vittorie possibili (12 gare)

        categories = ['Vittorie (1°)', 'Canestri', 'Freccette']
        selected_player_radar = st.selectbox("Analizza Giocatore:", players)

        # Calcolo percentuali (Gestione divisione per zero se uno non ha mai giocato)
        stats = style_stats[selected_player_radar]

        perc_wins = (stats["Wins_Actual"] / stats["Wins_Max"] * 100) if stats["Wins_Max"] > 0 else 0
        perc_basket = (stats["Basket_Actual"] / stats["Basket_Max"] * 100) if stats["Basket_Max"] > 0 else 0
        perc_darts = (stats["Darts_Actual"] / stats["Darts_Max"] * 100) if stats["Darts_Max"] > 0 else 0

        vals_perc = [perc_wins, perc_basket, perc_darts]

        # Per il tooltip mostriamo anche i valori veri
        hover_text = [
            f"{stats['Wins_Actual']} su {stats['Wins_Max']} possibili",
            f"{stats['Basket_Actual']} su {stats['Basket_Max']} possibili",
            f"{stats['Darts_Actual']} su {stats['Darts_Max']} possibili"
        ]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=vals_perc,
            theta=categories,
            fill='toself',
            name=selected_player_radar,
            line_color='#e0bc00',
            text=hover_text,
            hovertemplate="%{theta}: %{r:.1f}%<br>(%{text})<extra></extra>"
        ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],  # Scala fissa 0-100%
                    ticksuffix="%"
                )
            ),
            showlegend=False,
            margin=dict(l=40, r=40, t=20, b=20)
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
        st.markdown("**Punteggi Gara (F1 Style):**")
        st.markdown(
            "| Pos | Punti |\n|---|---|\n| 🥇 1° | **12** |\n| 🥈 2° | **9** |\n| 🥉 3° | **6** |\n| 💩 4° | **3** |")

    st.markdown("#### 🌟 Grand Slam (Perfect Score)")
    st.warning(
        "Se un giocatore vince **tutte e 12 le gare** (fa sempre 1°) nella stessa giornata, ottiene un **Bonus di +10 Punti**!")

    st.subheader("3. 🏀🎯 La Resa dei Conti - Skill Challenge")
    st.markdown("""
        Al termine delle gare, si svolgono le prove fisiche.
        Non si sommano i punti fatti, ma si stila una **Classifica** (12-9-6-3 punti).
        
        ### 🏀 Basket (5 Tiri Speciali)
        * Ogni giocatore ha **5 tiri speciali**.
        * **Bonus (+5 pt Classifica):** Se realizzi **>= 20 punti** reali.
        * **Spareggio:** 5 tiri extra.
        
        ### 🎯 Freccette (101 -> 0)
        * Si parte da **101** e si scende a **0 esatto**.
        * **Regola "Fine Round":** Se uno chiude, gli altri finiscono il giro (possibili pareggi).
        * **Bonus (+5 pt Classifica):** Se chiudi in **<= 3 round**.
        * **Spareggio:** Partita veloce **51 -> 0**.
        """)

    st.divider()
    st.subheader("4. ⚖️ Il Calcolo della Classifica (MEDIA PUNTI)")
    st.info("""
        Per garantire equità in caso di assenze, vince chi ha la **MEDIA PUNTI** più alta, non il totale assoluto.
        """)
    st.latex(r"\text{Media Punti} = \frac{\text{Totale Punti Accumulati}}{\text{Numero di Giornate Giocate}}")
    st.markdown("""
        * **Assenze:** Se un giocatore è assente, quella giornata non conta per la sua media (non viene penalizzato).
        * **Pareggi:** In caso di parità di media, vince chi ha fatto più **Punti Totali**.
        """)

    st.divider()
    st.subheader("5. 📈 Statistiche: La Forma Attuale")
    st.markdown("""
        Il numero nella card "Forma Attuale" utilizza il metodo della **Finestra Mobile (Sliding Window)** sulle ultime 3 presenze.
        """)

    st.markdown("### 🧮 Esempio Pratico")
    st.markdown("Immagina di aver fatto questi punteggi nelle tue ultime 4 serate:")
    st.code("Giornata 1: 80 pt\nGiornata 2: 90 pt\nGiornata 3: 90 pt\nGiornata 4 (Oggi): 120 pt (Seratona!)")

    st.markdown("**1. Calcolo Media Ieri (G1+G2+G3):**")
    st.latex(r"\text{Media Ieri} = \frac{80 + 90 + 90}{3} = \mathbf{86.6}")

    st.markdown("**2. Calcolo Media Oggi (G2+G3+G4):**")
    st.latex(r"\text{Media Oggi} = \frac{90 + 90 + 120}{3} = \mathbf{100.0}")

    st.markdown("**3. Il Delta (La Freccina):**")
    st.latex(r"\text{Delta} = 100.0 - 86.6 = \mathbf{+13.4} \quad (\text{Verde})")

    st.success("""
    **Interpretazione:**
    La logica è: **"La nuova partita (G4) è riuscita ad alzare la mia media recente sostituendo la partita più vecchia (G1)?"**

    * Se la gara di oggi è migliore di quella di 4 volte fa (che esce dal conteggio), la tua forma sale.
    * Se è peggiore, la tua forma scende.
    """)
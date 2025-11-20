import streamlit as st
import pandas as pd

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GP Corso Francia", page_icon="🏎️", layout="wide")

# --- TITOLO E ATMOSFERA ---
st.title("🏎️ Gran Premio di Torino - Circuito Corso Francia")
st.subheader("📍 Corso Francia 2 bis | 🏆 Trofeo della Mole")
st.markdown("---")

# --- LISTA GIOCATORI ---
# Modifica qui i nomi se vuoi che siano fissi, o lasciali così
if 'players' not in st.session_state:
    st.session_state.players = ["Giocatore 1", "Giocatore 2", "Giocatore 3", "Giocatore 4"]

# --- SISTEMA DI PUNTEGGIO ---
POINTS_MAP = {"1° Posto": 10, "2° Posto": 7, "3° Posto": 4, "4° Posto": 2}

# --- INIZIALIZZAZIONE DATI ---
if 'race_results' not in st.session_state:
    # Crea una struttura vuota per 12 gare
    st.session_state.race_results = {f"Gara {i + 1}": [None] * 4 for i in range(12)}

if 'ko_points' not in st.session_state:
    st.session_state.ko_points = [0] * 4

if 'skill_points' not in st.session_state:
    st.session_state.basket = [0] * 4
    st.session_state.darts = [0] * 4

# --- SIDEBAR: GESTIONE NOMI ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    for i in range(4):
        st.session_state.players[i] = st.text_input(f"Nome Giocatore {i + 1}", st.session_state.players[i])

    st.markdown("---")
    st.markdown("**Regole Punti MK8:**")
    st.code("1°: 10pt | 2°: 7pt\n3°: 4pt  | 4°: 2pt")

# --- TABS PRINCIPALI ---
tab1, tab2, tab3 = st.tabs(["🏁 Inserimento Gare", "🏀🎯 Skill Challenge", "📊 CLASSIFICA FINALE"])

# TAB 1: INSERIMENTO RISULTATI GARE
with tab1:
    st.header("Inserimento Risultati Mario Kart")

    # Griglia per inserire i dati
    cols = st.columns(4)

    # Seleziona la gara da modificare
    race_num = st.selectbox("Seleziona Gara:", [f"Gara {i + 1}" for i in range(12)])

    st.info(f"Inserisci i piazzamenti per {race_num}")

    current_results = st.session_state.race_results[race_num]

    inputs = []
    for i, player in enumerate(st.session_state.players):
        val = st.selectbox(f"Posizione {player}",
                           options=["Seleziona...", "1° Posto", "2° Posto", "3° Posto", "4° Posto"],
                           key=f"{race_num}_{i}")

        # Salva il risultato nello stato
        if val != "Seleziona...":
            st.session_state.race_results[race_num][i] = POINTS_MAP[val]
        else:
            st.session_state.race_results[race_num][i] = 0

    st.markdown("---")
    st.subheader("💥 Bonus K.O.")
    st.caption("Aggiungi qui i punti KO totali accumulati (usati per gli spareggi)")
    for i, player in enumerate(st.session_state.players):
        st.session_state.ko_points[i] = st.number_input(f"KO Points: {player}", min_value=0,
                                                        value=st.session_state.ko_points[i], step=1)

# TAB 2: SKILL CHALLENGE
with tab2:
    st.header("La Gara del Giudizio (Post-Gara 12)")
    st.markdown("Inserisci i punti ottenuti col canestro e le freccette.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🏀 Canestro (Max 9)")
        for i, player in enumerate(st.session_state.players):
            st.session_state.basket[i] = st.number_input(f"Basket Punti: {player}", min_value=0, max_value=9,
                                                         value=st.session_state.basket[i])

    with c2:
        st.subheader("🎯 Freccette (Max 12)")
        for i, player in enumerate(st.session_state.players):
            st.session_state.darts[i] = st.number_input(f"Freccette Punti: {player}", min_value=0, max_value=12,
                                                        value=st.session_state.darts[i])

# TAB 3: CLASSIFICA E TABELLA
with tab3:
    st.header("🏆 Classifica Generale")

    # Calcolo Totali
    data = []
    for i, player in enumerate(st.session_state.players):
        mk8_total = sum([st.session_state.race_results[f"Gara {r + 1}"][i] or 0 for r in range(12)])
        skill_total = st.session_state.basket[i] + st.session_state.darts[i]
        final_score = mk8_total + skill_total

        data.append({
            "Giocatore": player,
            "Punti MK8": mk8_total,
            "Skill Punti": skill_total,
            "Punti KO (Spareggio)": st.session_state.ko_points[i],
            "TOTALE": final_score
        })

    df = pd.DataFrame(data)

    # Ordina per Totale decrescente, poi per KO Points decrescente
    df = df.sort_values(by=["TOTALE", "Punti KO (Spareggio)"], ascending=False).reset_index(drop=True)
    df.index += 1  # Parte da 1 invece che da 0

    # Mostra la tabella con stile
    st.dataframe(df, use_container_width=True)

    # Podio visuale
    if len(df) > 0:
        winner = df.iloc[0]['Giocatore']
        st.success(f"🥇 Attualmente in testa: **{winner}**")

    # Tabella dettagliata gare (Opzionale)
    with st.expander("Vedi dettaglio punteggi gara per gara"):
        detail_data = {}
        detail_data["Giocatore"] = st.session_state.players
        for r in range(12):
            detail_data[f"Gara {r + 1}"] = [st.session_state.race_results[f"Gara {r + 1}"][i] or 0 for i in range(4)]
        st.table(pd.DataFrame(detail_data))
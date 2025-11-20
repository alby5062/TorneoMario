import json
import random

# --- CONFIGURAZIONE ---
FILENAME = "dati_campionato.json"
NUM_GIORNATE = 6  # Simuliamo 6 serate di gioco
PLAYERS = ["Infame", "Cammellaccio", "Pierino", "Nicolino"]  # Nomi di esempio

# Punteggi possibili in una gara singola
SCORES_AVAILABLE = [10, 7, 4, 2]

data = {
    "config": {"players": PLAYERS},
    "giornate": {}
}

print(f"Generazione dati per {NUM_GIORNATE} giornate in corso...")

for day in range(1, NUM_GIORNATE + 1):
    day_key = f"Giornata {day}"

    # 1. Simuliamo le assenze (10% di probabilità che qualcuno manchi)
    absent = [False] * 4
    present_indices = []

    for i in range(4):
        if random.random() < 0.1:  # 10% di probabilità di assenza
            absent[i] = True
        else:
            present_indices.append(i)

    # Se per caso mancano tutti (raro), forziamo almeno 2 presenti
    if len(present_indices) < 2:
        absent = [False] * 4
        present_indices = [0, 1, 2, 3]

    # 2. Generiamo le 12 Gare
    races = {}
    for r in range(1, 13):
        race_scores = [0] * 4

        # Mischiamo i punteggi disponibili in base a quanti sono presenti
        # Se ci sono 3 giocatori, usiamo [10, 7, 4]
        current_scores = SCORES_AVAILABLE[:len(present_indices)]
        random.shuffle(current_scores)

        # Assegniamo i punteggi ai presenti
        for idx, p_idx in enumerate(present_indices):
            race_scores[p_idx] = current_scores[idx]

        races[f"Gara {r}"] = race_scores

    # 3. Generiamo Skill e KO casuali
    ko = [0] * 4
    basket = [0] * 4
    darts = [0] * 4

    for i in present_indices:
        ko[i] = random.randint(0, 8)  # Tra 0 e 8 KO a serata
        basket[i] = random.randint(0, 9)  # Max 9
        darts[i] = random.randint(0, 12)  # Max 12

    # 4. Salviamo la giornata
    data["giornate"][day_key] = {
        "races": races,
        "ko": ko,
        "basket": basket,
        "darts": darts,
        "absent": absent
    }

# Scrittura su file
with open(FILENAME, "w") as f:
    json.dump(data, f, indent=4)

print(f"✅ Fatto! File '{FILENAME}' creato con successo.")
print("Ora avvia 'streamlit run torneo_v5.py' e goditi i grafici!")
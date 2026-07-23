"""
build_full_table.py

Unisce in un'unica tabella tutti i dati sulle 162 partite infinite:
rank, sequenza (configurazione), gruppo di ciclo (1-15), lunghezza del ciclo
in turni e in trick, e lunghezza del transitorio -- pronta per essere
mostrata ed esportata dal sito.

Uso:
    python3 build_full_table.py
"""

import re
import json
from straccia_common import build_table, unrank

COUNTS = [28, 4, 4, 4]


def parse_unique_cycles(path):
    """Ritorna dict: rank -> (group_index, cycle_length_turns, transient_turns)"""
    rank_to_group = {}
    current_group = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            m_group = re.match(r'gruppo (\d+): lunghezza=(\d+) membri=(\d+)', line)
            if m_group:
                current_group = int(m_group.group(1))
                continue
            m_rank = re.match(r'rank=(\d+) primo_turno=(\d+) lunghezza_ciclo=(\d+)', line)
            if m_rank:
                rank = int(m_rank.group(1))
                transient = int(m_rank.group(2))
                cyc_len = int(m_rank.group(3))
                rank_to_group[rank] = (current_group, cyc_len, transient)
    return rank_to_group


def parse_tricks_report(path):
    """Ritorna dict: rank -> (esito, turni, trick)"""
    out = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                rank = int(parts[0])
            except ValueError:
                continue
            esito = parts[1]
            try:
                turni = int(parts[2])
                trick = int(parts[3])
            except ValueError:
                continue
            out[rank] = (esito, turni, trick)
    return out


def main():
    print("Parsing dei file dati...")
    groups = parse_unique_cycles("unique_cycles.txt")
    tricks_data = parse_tricks_report("confirm_cycle_report_with_tricks.txt")

    print("Costruzione tabella multinomiale...")
    table, dims = build_table(COUNTS)
    half = sum(COUNTS) // 2

    # Ordina i 15 gruppi per dimensione decrescente (coerente con la visualizzazione)
    # e assegna un numero "umano" 1..15 invece dell'indice grezzo 0..14
    group_sizes = {}
    for rank, (g, cyc_len, transient) in groups.items():
        group_sizes.setdefault(g, []).append(rank)
    sorted_group_ids = sorted(group_sizes.keys(), key=lambda g: -len(group_sizes[g]))
    group_id_to_human = {g: i + 1 for i, g in enumerate(sorted_group_ids)}

    rows = []
    for rank, (g, cyc_len_turns, transient) in groups.items():
        seq = unrank(table, dims, rank, COUNTS)
        seq_str = "".join(map(str, seq))
        esito, cyc_len_turns_check, cyc_len_tricks = tricks_data.get(rank, (None, None, None))
        # cyc_len_turns_check e' la STESSA misura di cyc_len_turns (calcolata da
        # uno script indipendente) -- le teniamo entrambe solo come verifica
        # incrociata interna, non le esponiamo come due colonne separate nella
        # tabella finale.
        assert cyc_len_turns_check == cyc_len_turns, \
            f"rank {rank}: discrepanza turni {cyc_len_turns} vs {cyc_len_turns_check}"
        rows.append({
            "rank": rank,
            "sequence": seq_str,
            "group": group_id_to_human[g],
            "cycle_length_turns": cyc_len_turns,
            "cycle_length_tricks": cyc_len_tricks,
            "transient_turns": transient,
        })

    rows.sort(key=lambda r: (r["group"], r["rank"]))

    with open("full_162_table.json", "w") as f:
        json.dump(rows, f, separators=(",", ":"))

    with open("full_162_table.csv", "w") as f:
        f.write("rank,sequenza,gruppo_ciclo,lunghezza_ciclo_turni,lunghezza_ciclo_trick,transitorio_turni\n")
        for r in rows:
            f.write(f"{r['rank']},{r['sequence']},{r['group']},{r['cycle_length_turns']},"
                    f"{r['cycle_length_tricks']},{r['transient_turns']}\n")

    print(f"Righe totali (cicli infiniti): {len(rows)}")
    print("Scritto full_162_table.json e full_162_table.csv")

    # --- Secondo dataset: partite finite lunghe (>= 4500 turni) ---
    print("\nCostruzione del dataset delle partite finite lunghe...")
    long_rows = []
    for rank, (esito, turni, trick) in tricks_data.items():
        if esito == "TERMINATA" and turni >= 4500:
            seq = unrank(table, dims, rank, COUNTS)
            seq_str = "".join(map(str, seq))
            long_rows.append({
                "rank": rank,
                "sequence": seq_str,
                "turns": turni,
                "tricks": trick,
            })
    long_rows.sort(key=lambda r: -r["turns"])

    with open("long_games_table.json", "w") as f:
        json.dump(long_rows, f, separators=(",", ":"))

    with open("long_games_table.csv", "w") as f:
        f.write("rank,sequenza,turni,trick\n")
        for r in long_rows:
            f.write(f"{r['rank']},{r['sequence']},{r['turns']},{r['tricks']}\n")

    print(f"Righe totali (partite finite lunghe, >=4500 turni): {len(long_rows)}")
    print("Scritto long_games_table.json e long_games_table.csv")


if __name__ == "__main__":
    main()

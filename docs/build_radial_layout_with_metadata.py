"""
build_radial_layout_with_metadata.py

Versione unificata che ricalcola in un solo passaggio (per garantire
coerenza degli identificativi dei nodi):

  1. la traiettoria completa di ciascuna delle 162 partite infinite
  2. il grafo deduplicato (stato -> id) con gli archi
  3. il layout radiale (cicli come cerchi veri, transitori come raggi)
  4. per ciascun nodo: la configurazione leggibile dello stato (mano A,
     mano B, mazzetto, leader) e l'elenco dei rank che vi passano

Uso:
    python3 build_radial_layout_with_metadata.py hits_40_report_all.txt
"""

import sys
import math
import json
from collections import deque, defaultdict
from straccia_common import build_table, unrank

COUNTS = [28, 4, 4, 4]


def simulate_full_trajectory(deal_a, deal_b, max_turns=2_000_000):
    """Rigioca l'intera partita dal turno 0, restituendo la sequenza completa
    di stati (uno per round) fino alla chiusura del ciclo."""
    hands = [deque(deal_a), deque(deal_b)]
    pile = deque()
    leader = 0
    turn = 0
    seen_at = {}
    trajectory = []

    while hands[0] and hands[1] and turn < max_turns:
        state = (tuple(hands[0]), tuple(hands[1]), tuple(pile), leader)
        if state in seen_at:
            return ("cycle", trajectory, seen_at[state])
        seen_at[state] = len(trajectory)
        trajectory.append(state)

        attacker, defender = leader, 1 - leader
        v = hands[attacker].popleft()
        pile.append(v)
        turn += 1

        if not hands[defender]:
            return ("terminated", trajectory, None)

        if v == 0:
            leader = defender
            continue

        pending = v
        while pending > 0:
            if not hands[defender]:
                break
            rv = hands[defender].popleft()
            pile.append(rv)
            turn += 1
            pending -= 1
            if rv != 0:
                attacker, defender = defender, attacker
                pending = rv

        if not hands[defender]:
            return ("terminated", trajectory, None)

        while pile:
            hands[attacker].append(pile.popleft())
        leader = attacker

    return ("inconclusive", trajectory, None)


def parse_report(path):
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                rank = int(parts[0])
            except ValueError:
                continue
            rows.append((rank, parts[1]))
    return rows


def state_repr(state):
    hand_a, hand_b, pile, leader = state
    a = "".join(str(c) for c in hand_a)
    b = "".join(str(c) for c in hand_b)
    p = "".join(str(c) for c in pile)
    return f"A:{a}  B:{b}  P:{p}  L:{leader}"


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 build_radial_layout_with_metadata.py hits_40_report_all.txt")
        sys.exit(1)

    rows = parse_report(sys.argv[1])
    infiniti = [rank for rank, esito in rows if esito == "INFINITO"]
    print(f"Partite infinite da tracciare: {len(infiniti)}")

    print("Costruzione tabella multinomiale...")
    table, dims = build_table(COUNTS)
    half = sum(COUNTS) // 2

    state_to_id = {}
    id_to_state = {}
    edges = set()
    node_in_cycle = {}
    node_ranks = defaultdict(set)
    node_is_initial_deal = {}
    rank_paths = {}

    def get_id(state):
        if state not in state_to_id:
            new_id = len(state_to_id)
            state_to_id[state] = new_id
            id_to_state[new_id] = state
        return state_to_id[state]

    for idx, rank in enumerate(infiniti):
        deck = unrank(table, dims, rank, COUNTS)
        kind, trajectory, first_idx = simulate_full_trajectory(deck[:half], deck[half:])
        if kind != "cycle":
            print(f"  ATTENZIONE: rank {rank} non ha chiuso un ciclo ({kind})")
            continue

        ids = [get_id(s) for s in trajectory]
        rank_paths[rank] = ids

        for i, node_id in enumerate(ids):
            node_ranks[node_id].add(rank)
            in_cyc = i >= first_idx
            node_in_cycle[node_id] = node_in_cycle.get(node_id, False) or in_cyc

        for i in range(len(ids) - 1):
            edges.add((ids[i], ids[i + 1]))
        edges.add((ids[-1], ids[first_idx]))

        if (idx + 1) % 20 == 0:
            print(f"  ...{idx + 1}/{len(infiniti)} tracciati (nodi finora: {len(state_to_id)})")

    print(f"\nNodi totali: {len(state_to_id)}  Archi totali: {len(edges)}")

    # Un nodo e' una "configurazione di partenza" se e' il turno 0 (il mazzo
    # iniziale, prima di giocare qualunque carta) di ALMENO uno dei rank
    # tracciati. La maggior parte delle volte questo nodo NON e' nel ciclo
    # (il transitorio ha lunghezza > 0), ma in alcuni casi il mazzo iniziale
    # e' gia' esso stesso dentro il ciclo fin dal turno 0 (transitorio di
    # lunghezza zero) -- entrambi i casi vanno distinti da uno stato
    # raggiunto solo giocando (mai il turno 0 di nessun rank tracciato).
    initial_nodes = set(path[0] for path in rank_paths.values())
    print(f"Nodi che sono 'turno 0' di almeno un rank: {len(initial_nodes)}")

    # --- Componenti (cicli) e ordine sequenziale ---
    forward = {}
    for a, b in edges:
        forward[a] = b

    cycle_nodes = set(n for n, v in node_in_cycle.items() if v)
    visited = set()
    components = []
    for start in cycle_nodes:
        if start in visited:
            continue
        ring = [start]
        visited.add(start)
        cur = forward[start]
        while cur != start:
            ring.append(cur)
            visited.add(cur)
            cur = forward[cur]
        components.append(ring)
    components.sort(key=lambda r: -len(r))
    print(f"Componenti (cicli) trovate: {len(components)}")

    # --- Passi al ciclo + componente di appartenenza (BFS a ritroso) ---
    reverse = defaultdict(list)
    for a, b in edges:
        reverse[b].append(a)

    node_to_component = {}
    for ci, ring in enumerate(components):
        for n in ring:
            node_to_component[n] = ci

    steps = {n: 0 for n in node_to_component}
    queue = deque(node_to_component.keys())
    while queue:
        cur = queue.popleft()
        for pred in reverse.get(cur, []):
            if pred not in steps:
                steps[pred] = steps[cur] + 1
                node_to_component[pred] = node_to_component[cur]
                queue.append(pred)

    # --- Raggruppa le partite per componente ---
    games_by_component = defaultdict(list)
    for rank, path in rank_paths.items():
        entry_node = next((n for n in path if node_in_cycle.get(n, False)), None)
        if entry_node is None:
            continue
        games_by_component[node_to_component[entry_node]].append((rank, path, entry_node))

    # --- Rinumerazione "umana" (1-15), riusando la numerazione GIA'
    # stabilita in full_162_table.json (dati.html), non ricalcolata qui da
    # zero -- ci sono pareggi nel conteggio partite (sei coppie da 2, sei
    # singoli da 1) il cui ordine relativo non e' definito univocamente dal
    # solo conteggio; ricalcolarlo in questo script rischierebbe di dare un
    # numero diverso allo stesso ciclo rispetto a quello mostrato nella
    # tabella dati, per un puro dettaglio di ordine di elaborazione.
    with open("full_162_table.json") as f:
        official_rows = json.load(f)
    rank_to_official_group = {row["rank"]: row["group"] for row in official_rows}

    ci_to_human = {}
    for ci, members in games_by_component.items():
        # basta un solo rank di questa componente per conoscere il suo
        # numero ufficiale di ciclo (e' lo stesso per tutti i membri)
        sample_rank = members[0][0]
        ci_to_human[ci] = rank_to_official_group[sample_rank]

    # --- Layout geometrico ---
    POINT_SPACING_ON_RING = 3.2
    RADIAL_SPACING = 5.5
    MIN_RING_RADIUS = 18

    node_polar = {}
    component_extents = []

    for ci, ring in enumerate(components):
        ring_len = len(ring)
        ring_radius = max(MIN_RING_RADIUS, ring_len * POINT_SPACING_ON_RING / (2 * math.pi))
        ring_angle = {}
        for i, node in enumerate(ring):
            angle = 2 * math.pi * i / ring_len
            ring_angle[node] = angle
            node_polar[node] = (angle, ring_radius)

        games = games_by_component.get(ci, [])
        games.sort(key=lambda gme: ring_angle[gme[2]])
        n_games = len(games)
        max_steps_here = 0

        for gi, (rank, path, entry_node) in enumerate(games):
            leaf_angle = 2 * math.pi * gi / max(n_games, 1)
            for node in path:
                if node_in_cycle.get(node, False):
                    continue
                if node in node_polar:
                    continue
                s = steps[node]
                max_steps_here = max(max_steps_here, s)
                node_polar[node] = (leaf_angle, ring_radius + s * RADIAL_SPACING)

        component_extents.append(ring_radius + max_steps_here * RADIAL_SPACING + 20)

    # --- Disposizione delle componenti nel piano (spirale, senza sovrapposizioni) ---
    centers = []
    for i, extent in enumerate(component_extents):
        if i == 0:
            centers.append((0.0, 0.0))
            continue
        angle, dist, placed = 0.0, 0.0, False
        tries = 0
        while not placed and tries < 6000:
            x = dist * math.cos(angle)
            y = dist * math.sin(angle)
            ok = True
            for j, (px, py) in enumerate(centers):
                min_dist = component_extents[j] + extent + 15
                if (px - x) ** 2 + (py - y) ** 2 < min_dist ** 2:
                    ok = False
                    break
            if ok:
                centers.append((x, y))
                placed = True
            angle += 0.3
            dist += 4
            tries += 1
        if not placed:
            centers.append((dist, 0.0))

    # --- Coordinate cartesiane finali + metadati per nodo ---
    final_nodes = {}
    for node, (angle, radius) in node_polar.items():
        ci = node_to_component[node]
        ccx, ccy = centers[ci]
        x = ccx + radius * math.cos(angle)
        y = ccy + radius * math.sin(angle)
        ranks_here = sorted(node_ranks[node])
        final_nodes[node] = {
            "x": round(x, 2),
            "y": round(y, 2),
            "in_cycle": node_in_cycle.get(node, False),
            "is_initial": node in initial_nodes,
            "component": ci_to_human[ci],
            "state": state_repr(id_to_state[node]),
            "ranks": ranks_here,
        }

    # Riepilogo per ciascuno dei 15 cicli (usato dal selettore nell'interfaccia
    # del grafo, per etichette tipo "Ciclo 1 -- 90 partite, 546 turni")
    cycles_summary = {}
    for row in official_rows:
        g = row["group"]
        if g not in cycles_summary:
            cycles_summary[g] = {
                "game_count": 0,
                "cycle_length_turns": row["cycle_length_turns"],
                "cycle_length_tricks": row["cycle_length_tricks"],
            }
        cycles_summary[g]["game_count"] += 1

    output = {
        "nodes": final_nodes,
        "edges": list(edges),
        # Mappa ESPLICITA rank -> id del nodo che rappresenta il SUO PROPRIO
        # turno 0 -- necessaria perche' il flag is_initial su un nodo, da solo,
        # non basta a distinguere "questo nodo e' il turno-0 di QUESTO rank"
        # da "questo nodo e' il turno-0 di un rank diverso, ma la partita
        # attuale ci transita comunque piu' avanti nella sua traiettoria"
        # (capita per i nodi che sono sia is_initial sia dentro il ciclo
        # condiviso: la loro lista 'ranks' contiene per forza tutte le
        # partite del ciclo, non solo quella il cui turno-0 coincide con
        # questo stato specifico).
        "rank_to_own_initial_node": {str(rank): path[0] for rank, path in rank_paths.items()},
        "cycles_summary": cycles_summary,
    }
    with open("radial_layout_with_metadata.json", "w") as f:
        json.dump(output, f, separators=(",", ":"))

    import os
    print(f"\nScritto radial_layout_with_metadata.json "
          f"({os.path.getsize('radial_layout_with_metadata.json'):,} byte)")


if __name__ == "__main__":
    main()

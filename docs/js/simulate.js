// simulate.js
//
// Simulazione della partita con rilevamento di cicli, porting diretto della
// logica gia' validata in confirm_cycle.py. A differenza della versione
// usata per l'analisi massiva (che scartava la cronologia per risparmiare
// memoria), qui conserviamo OGNI stato intermedio (history), perche' il
// sito deve poterli mostrare uno per uno all'utente.
//
// Regole confermate: divisione a blocchi (prima meta' -> giocatore 0,
// seconda meta' -> giocatore 1), reinserimento del mazzetto vinto in ordine
// FIFO, leader iniziale = giocatore della prima meta'.

function stateKey(handA, handB, pile, leader) {
    return handA.join(',') + '|' + handB.join(',') + '|' + pile.join(',') + '|' + leader;
}

// Esegue l'intera simulazione, conservando DUE cronologie parallele:
//   - history:      uno snapshot per ogni ROUND (la carta del leader + l'eventuale
//                    intera catena di risposte, registrati come un unico salto)
//   - turnHistory:  uno snapshot per ogni SINGOLA CARTA giocata, inclusa ciascuna
//                    carta dentro una catena di risposte -- utile per capire nel
//                    dettaglio catene lunghe con piu' scambi di ruolo
//
// In entrambe, il campo 'leader' indica chi sta per giocare in quello
// specifico snapshot (per i round e' chi guida il round; per i singoli
// turni puo' cambiare piu' volte all'interno di una stessa catena).
//
// Ritorna:
//   { kind: 'cycle', firstTurn, curTurn, cycleLengthTurns, firstIdx, history, turnHistory }
//   { kind: 'terminated', turn, history, turnHistory }
//   { kind: 'inconclusive', turn, history, turnHistory }
function simulateFull(dealA, dealB, maxTurns = 2000000) {
    let hands = [dealA.slice(), dealB.slice()];
    let pile = [];
    let leader = 0;
    let turn = 0;
    const seen = new Map();
    const history = [];
    const turnHistory = [];

    function snapshot(arr, activePlayer) {
        arr.push({
            turn: turn,
            handA: hands[0].slice(),
            handB: hands[1].slice(),
            pile: pile.slice(),
            leader: activePlayer,
        });
    }

    while (hands[0].length > 0 && hands[1].length > 0 && turn < maxTurns) {
        const key = stateKey(hands[0], hands[1], pile, leader);
        if (seen.has(key)) {
            const firstIdx = seen.get(key);
            return {
                kind: 'cycle',
                firstTurn: history[firstIdx].turn,
                curTurn: turn,
                cycleLengthTurns: turn - history[firstIdx].turn,
                firstIdx: firstIdx,
                history: history,
                turnHistory: turnHistory,
            };
        }
        seen.set(key, history.length);
        snapshot(history, leader);

        let attacker = leader, defender = 1 - leader;

        snapshot(turnHistory, attacker);  // prima che il leader giochi la sua carta
        const v = hands[attacker].shift();
        pile.push(v);
        turn++;

        if (hands[defender].length === 0) {
            while (pile.length > 0) hands[attacker].push(pile.shift());
            snapshot(history, attacker);
            snapshot(turnHistory, attacker);
            return { kind: 'terminated', turn: turn, history: history, turnHistory: turnHistory };
        }

        if (v === 0) {
            leader = defender;
            continue;
        }

        let pending = v;
        while (pending > 0) {
            if (hands[defender].length === 0) break;
            snapshot(turnHistory, defender);  // prima che il difensore risponda con questa carta
            const rv = hands[defender].shift();
            pile.push(rv);
            turn++;
            pending--;
            if (rv !== 0) {
                const tmp = attacker; attacker = defender; defender = tmp;
                pending = rv;
            }
        }

        if (hands[defender].length === 0) {
            while (pile.length > 0) hands[attacker].push(pile.shift());
            snapshot(history, attacker);
            snapshot(turnHistory, attacker);
            return { kind: 'terminated', turn: turn, history: history, turnHistory: turnHistory };
        }

        while (pile.length > 0) {
            hands[attacker].push(pile.shift());
        }
        leader = attacker;
    }

    if (hands[0].length === 0 || hands[1].length === 0) {
        return { kind: 'terminated', turn: turn, history: history, turnHistory: turnHistory };
    }
    return { kind: 'inconclusive', turn: turn, history: history, turnHistory: turnHistory };
}

if (typeof module !== 'undefined') {
    module.exports = { simulateFull, stateKey };
}
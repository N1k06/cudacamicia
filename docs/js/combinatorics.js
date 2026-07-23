// combinatorics.js
//
// Unranking/ranking per composizioni del mazzo (default: 28,4,4,4 = Straccia
// Camicia da 40 carte). A differenza della versione Python (che usa
// math.factorial, sicuro con interi arbitrari), qui costruiamo la tabella
// multinomiale con una RICORRENZA additiva (stile triangolo di Pascal),
// evitando di calcolare mai un fattoriale grezzo -- ogni valore della
// tabella resta sempre ben sotto 2^53 (il limite di precisione esatta per
// i Number di JavaScript), quindi non serve BigInt.
//
// M(c0,c1,c2,c3) = M(c0-1,c1,c2,c3) + M(c0,c1-1,c2,c3)
//                + M(c0,c1,c2-1,c3) + M(c0,c1,c2,c3-1)
// (con M(0,0,0,0) = 1, e termini omessi se l'indice sarebbe negativo)

function buildTable(counts) {
    const dims = counts.map(c => c + 1);
    const size = dims[0] * dims[1] * dims[2] * dims[3];
    const table = new Array(size).fill(0);

    const idx = (c0, c1, c2, c3) => ((c0 * dims[1] + c1) * dims[2] + c2) * dims[3] + c3;

    table[idx(0, 0, 0, 0)] = 1;
    for (let c0 = 0; c0 <= counts[0]; c0++) {
        for (let c1 = 0; c1 <= counts[1]; c1++) {
            for (let c2 = 0; c2 <= counts[2]; c2++) {
                for (let c3 = 0; c3 <= counts[3]; c3++) {
                    if (c0 === 0 && c1 === 0 && c2 === 0 && c3 === 0) continue;
                    let total = 0;
                    if (c0 > 0) total += table[idx(c0 - 1, c1, c2, c3)];
                    if (c1 > 0) total += table[idx(c0, c1 - 1, c2, c3)];
                    if (c2 > 0) total += table[idx(c0, c1, c2 - 1, c3)];
                    if (c3 > 0) total += table[idx(c0, c1, c2, c3 - 1)];
                    table[idx(c0, c1, c2, c3)] = total;
                }
            }
        }
    }
    return { table, dims };
}

function tblLookup(table, dims, c0, c1, c2, c3) {
    return table[((c0 * dims[1] + c1) * dims[2] + c2) * dims[3] + c3];
}

function totalConfigurations(table, dims, counts) {
    return tblLookup(table, dims, counts[0], counts[1], counts[2], counts[3]);
}

// rank -> sequenza di simboli (0..3)
function unrank(table, dims, rank, counts) {
    const c = counts.slice();
    const n = counts.reduce((a, b) => a + b, 0);
    const out = [];
    for (let pos = 0; pos < n; pos++) {
        for (let sym = 0; sym < 4; sym++) {
            if (c[sym] === 0) continue;
            c[sym]--;
            const perms = tblLookup(table, dims, c[0], c[1], c[2], c[3]);
            if (rank < perms) {
                out.push(sym);
                break;
            }
            rank -= perms;
            c[sym]++;
        }
    }
    return out;
}

// sequenza di simboli -> rank (operazione inversa)
function rankOf(table, dims, seq, counts) {
    const c = counts.slice();
    let rank = 0;
    for (const symActual of seq) {
        for (let sym = 0; sym < symActual; sym++) {
            if (c[sym] === 0) continue;
            c[sym]--;
            rank += tblLookup(table, dims, c[0], c[1], c[2], c[3]);
            c[sym]++;
        }
        c[symActual]--;
    }
    return rank;
}

if (typeof module !== 'undefined') {
    module.exports = { buildTable, tblLookup, totalConfigurations, unrank, rankOf };
}

// app.js — wiring dell'interfaccia del simulatore

const COUNTS = [28, 4, 4, 4];
const { table, dims } = buildTable(COUNTS);
const TOTAL = totalConfigurations(table, dims, COUNTS);
const HALF = COUNTS.reduce((a, b) => a + b, 0) / 2;

const seqInput = document.getElementById('seq-input');
const rankInput = document.getElementById('rank-input');
const seqError = document.getElementById('seq-error');
const rankError = document.getElementById('rank-error');
const simulateBtn = document.getElementById('simulate-btn');
const simStatus = document.getElementById('sim-status');

const resultPanel = document.getElementById('result-panel');
const outcomeBanner = document.getElementById('outcome-banner');
const turnLabel = document.getElementById('turn-label');
const handARow = document.getElementById('hand-a-row');
const handBRow = document.getElementById('hand-b-row');
const pileRow = document.getElementById('pile-row');
const pileEmptyNote = document.getElementById('pile-empty-note');
const leaderABadge = document.getElementById('leader-a-badge');
const leaderBBadge = document.getElementById('leader-b-badge');
const cycleMarker = document.getElementById('cycle-marker');

const btnFirst = document.getElementById('btn-first');
const btnPrev = document.getElementById('btn-prev');
const btnPlay = document.getElementById('btn-play');
const btnNext = document.getElementById('btn-next');
const btnLast = document.getElementById('btn-last');
const btnCycleStart = document.getElementById('btn-cycle-start');
const slider = document.getElementById('position-slider');
const positionReadout = document.getElementById('position-readout');

let currentResult = null;
let playTimer = null;

// --- Validazione e sincronizzazione sequenza <-> rank ---

function validateSequence(str) {
    if (str.length !== 40) return `Servono esattamente 40 cifre (attuali: ${str.length})`;
    if (!/^[0-3]{40}$/.test(str)) return 'Sono ammesse solo le cifre 0, 1, 2, 3';
    const counts = [0, 0, 0, 0];
    for (const ch of str) counts[parseInt(ch, 10)]++;
    if (counts[0] !== COUNTS[0] || counts[1] !== COUNTS[1] || counts[2] !== COUNTS[2] || counts[3] !== COUNTS[3]) {
        return `Composizione non valida: servono ${COUNTS[0]} zeri, ${COUNTS[1]} uno, ${COUNTS[2]} due, ${COUNTS[3]} tre ` +
               `(trovati: ${counts[0]}, ${counts[1]}, ${counts[2]}, ${counts[3]})`;
    }
    return null;
}

function setSequence(seqArrOrStr, skipRankUpdate) {
    const str = Array.isArray(seqArrOrStr) ? seqArrOrStr.join('') : seqArrOrStr;
    seqInput.value = str;
    seqError.textContent = '';
    if (!skipRankUpdate) {
        const seq = str.split('').map(Number);
        const rank = rankOf(table, dims, seq, COUNTS);
        rankInput.value = String(rank);
        rankError.textContent = '';
    }
}

seqInput.addEventListener('input', () => {
    const str = seqInput.value.trim();
    if (str.length === 0) { seqError.textContent = ''; return; }
    const err = validateSequence(str);
    if (err) {
        seqError.textContent = str.length === 40 ? err : '';
        return;
    }
    seqError.textContent = '';
    const seq = str.split('').map(Number);
    const rank = rankOf(table, dims, seq, COUNTS);
    rankInput.value = String(rank);
    rankError.textContent = '';
});

rankInput.addEventListener('input', () => {
    const raw = rankInput.value.trim().replace(/[.\s]/g, '');
    if (raw.length === 0) { rankError.textContent = ''; return; }
    if (!/^\d+$/.test(raw)) { rankError.textContent = 'Inserisci solo cifre'; return; }
    const rank = Number(raw);
    if (rank < 0 || rank >= TOTAL) {
        rankError.textContent = `Il rank deve essere tra 0 e ${TOTAL - 1}`;
        return;
    }
    rankError.textContent = '';
    const seq = unrank(table, dims, rank, COUNTS);
    seqInput.value = seq.join('');
    seqError.textContent = '';
});

// --- Esempi rapidi ---

document.querySelectorAll('[data-example]').forEach(btn => {
    btn.addEventListener('click', () => {
        const ex = btn.getAttribute('data-example');
        let rank;
        if (ex === 'random') {
            rank = Math.floor(Math.random() * TOTAL);
        } else {
            rank = Number(ex);
        }
        rankInput.value = String(rank);
        rankInput.dispatchEvent(new Event('input'));
    });
});

// --- Simulazione ---

simulateBtn.addEventListener('click', () => {
    const str = seqInput.value.trim();
    const err = validateSequence(str);
    if (err) {
        seqError.textContent = err;
        simStatus.textContent = '';
        return;
    }
    const seq = str.split('').map(Number);
    const dealA = seq.slice(0, HALF);
    const dealB = seq.slice(HALF);

    simStatus.textContent = 'Simulazione in corso…';
    stopPlayback();

    // Lasciamo respirare l'interfaccia prima di un calcolo potenzialmente
    // pesante (partite fino a qualche migliaio di turni sono comunque
    // rapidissime, ma un timeout evita che il pulsante sembri "bloccato").
    setTimeout(() => {
        const result = simulateFull(dealA, dealB, 2000000);
        currentResult = result;
        simStatus.textContent = '';
        showResult(result);
    }, 10);
});

function showResult(result) {
    resultPanel.classList.add('visible');

    if (result.kind === 'cycle') {
        outcomeBanner.className = 'outcome-banner cycle';
        outcomeBanner.textContent =
            `Ciclo infinito confermato: lo stato si ripete dopo ${result.cycleLengthTurns} turni ` +
            `(primo visto al turno ${result.firstTurn}, rivisto al turno ${result.curTurn}).`;
        btnCycleStart.style.display = '';
    } else if (result.kind === 'terminated') {
        outcomeBanner.className = 'outcome-banner terminated';
        outcomeBanner.textContent = `La partita termina naturalmente dopo ${result.turn} turni.`;
        btnCycleStart.style.display = 'none';
    } else {
        outcomeBanner.className = 'outcome-banner';
        outcomeBanner.textContent = `Nessun ciclo né fine entro ${result.turn} turni (limite di sicurezza raggiunto).`;
        btnCycleStart.style.display = 'none';
    }

    slider.max = String(result.history.length - 1);
    slider.value = '0';
    renderState(0);
}

function renderState(idx) {
    const s = currentResult.history[idx];

    turnLabel.textContent = `Turno ${s.turn}`;
    renderHand(handARow, s.handA);
    renderHand(handBRow, s.handB);
    renderHand(pileRow, s.pile);
    pileEmptyNote.style.display = s.pile.length === 0 ? '' : 'none';

    leaderABadge.style.display = s.leader === 0 ? '' : 'none';
    leaderBBadge.style.display = s.leader === 1 ? '' : 'none';

    if (currentResult.kind === 'cycle' && idx === currentResult.firstIdx) {
        cycleMarker.style.display = '';
        cycleMarker.textContent = '★ Questo è lo stato che si ripeterà — inizio del ciclo.';
    } else {
        cycleMarker.style.display = 'none';
    }

    positionReadout.textContent = `${idx} / ${currentResult.history.length - 1}`;
    slider.value = String(idx);
}

function renderHand(container, cards) {
    container.innerHTML = '';
    for (const v of cards) {
        const chip = document.createElement('span');
        chip.className = 'card-chip';
        chip.setAttribute('data-v', String(v));
        chip.textContent = String(v);
        container.appendChild(chip);
    }
}

// --- Controlli di riproduzione ---

function stopPlayback() {
    if (playTimer) { clearInterval(playTimer); playTimer = null; btnPlay.textContent = '▶'; }
}

btnFirst.addEventListener('click', () => { stopPlayback(); renderState(0); });
btnLast.addEventListener('click', () => { stopPlayback(); renderState(currentResult.history.length - 1); });
btnPrev.addEventListener('click', () => {
    stopPlayback();
    const idx = Math.max(0, parseInt(slider.value, 10) - 1);
    renderState(idx);
});
btnNext.addEventListener('click', () => {
    stopPlayback();
    const idx = Math.min(currentResult.history.length - 1, parseInt(slider.value, 10) + 1);
    renderState(idx);
});
btnCycleStart.addEventListener('click', () => {
    stopPlayback();
    if (currentResult && currentResult.kind === 'cycle') renderState(currentResult.firstIdx);
});
btnPlay.addEventListener('click', () => {
    if (playTimer) { stopPlayback(); return; }
    btnPlay.textContent = '⏸';
    playTimer = setInterval(() => {
        const idx = parseInt(slider.value, 10);
        if (idx >= currentResult.history.length - 1) { stopPlayback(); return; }
        renderState(idx + 1);
    }, 120);
});
slider.addEventListener('input', () => {
    stopPlayback();
    renderState(parseInt(slider.value, 10));
});

// --- Precompila con un esempio all'avvio, per non presentare una pagina vuota ---
rankInput.value = '649797222495';
rankInput.dispatchEvent(new Event('input'));

'use strict';

const MAX_GUESSES = 5;
const WORD_LENGTH  = 5;

const RESULT_COLOR = {
  1: '#538d4e', // CORRECT
  2: '#b59f3b', // PRESENT
  3: '#3a3a3c', // ABSENT
};
const COLOR_PRIORITY = { 1: 3, 2: 2, 3: 1 };

let currentRow   = 0;
let currentInput = [];
let isAnimating  = false;
let gameOver     = false;
let hardMode     = false;
let keyStates    = {};
let lastWinGuesses = 0;

// ── Board ─────────────────────────────────────────────────────────────────

function buildBoard() {
  const board = document.getElementById('board');
  board.innerHTML = '';
  for (let r = 0; r < MAX_GUESSES; r++) {
    const row = document.createElement('div');
    row.className = 'row';
    row.id = `row-${r}`;
    for (let c = 0; c < WORD_LENGTH; c++) {
      const tile = document.createElement('div');
      tile.className = 'tile';
      tile.id = `tile-${r}-${c}`;
      row.appendChild(tile);
    }
    board.appendChild(row);
  }
}

function getTile(r, c) {
  return document.getElementById(`tile-${r}-${c}`);
}

function setTileInstant(tile, letter, result) {
  tile.textContent = letter;
  if (result) {
    tile.dataset.state         = String(result);
    tile.style.backgroundColor = RESULT_COLOR[result] || '';
    tile.style.borderColor     = RESULT_COLOR[result] || '';
  } else if (letter) {
    tile.dataset.state = 'tbd';
    tile.style.borderColor = '#565758';
  }
}

// ── Fireworks ─────────────────────────────────────────────────────────────

function launchFireworks(duration = 3200) {
  const canvas = document.getElementById('fireworks');
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.style.display = 'block';
  const ctx = canvas.getContext('2d');

  const particles = [];

  function spawnBurst(x, y, count = 70) {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 7 + 2;
      // All white / near-white palette
      const shade = Math.floor(Math.random() * 40 + 215);
      const color = `rgb(${shade},${shade},${shade})`;
      particles.push({
        x, y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1,
        alpha: 1,
        decay: Math.random() * 0.012 + 0.012,
        size:  Math.random() * 4 + 1.5,
        color,
        // some particles are small streaks (elongated)
        streak: Math.random() < 0.35,
      });
    }
  }

  const cx = canvas.width  / 2;
  const cy = canvas.height / 2;

  // Immediate burst at center
  spawnBurst(cx, cy * 0.45, 90);

  // Periodic extra bursts
  const burstInterval = setInterval(() => {
    const x = cx + (Math.random() - 0.5) * canvas.width  * 0.55;
    const y = cy * 0.15 + Math.random() * cy * 0.55;
    spawnBurst(x, y, 55);
  }, 450);

  const deadline = performance.now() + duration;

  function animate(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x  += p.vx;
      p.y  += p.vy;
      p.vy += 0.18; // gravity
      p.vx *= 0.98; // air resistance
      p.alpha -= p.decay;

      if (p.alpha <= 0) { particles.splice(i, 1); continue; }

      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle   = p.color;

      if (p.streak) {
        // draw a small line in direction of travel
        ctx.strokeStyle = p.color;
        ctx.lineWidth   = p.size * 0.6;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x - p.vx * 2.5, p.y - p.vy * 2.5);
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    if (now < deadline) {
      requestAnimationFrame(animate);
    } else {
      clearInterval(burstInterval);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvas.style.display = 'none';
    }
  }

  requestAnimationFrame(animate);
  // Stop spawning new bursts near the end
  setTimeout(() => clearInterval(burstInterval), duration - 300);
}

// ── Win celebration ───────────────────────────────────────────────────────

function showWinCelebration(msg) {
  const overlay = document.getElementById('win-overlay');
  document.getElementById('win-message').textContent = msg;
  overlay.classList.remove('hidden');
  launchFireworks(3200);
  setTimeout(() => {
    overlay.classList.add('hidden');
    showStatsModal();
  }, 3200);
}

// ── Answer modal (loss) ───────────────────────────────────────────────────

function showAnswerModal(word) {
  document.getElementById('answer-word').textContent = word.toUpperCase();
  document.getElementById('answer-modal').classList.remove('hidden');
}

// ── State restore ─────────────────────────────────────────────────────────

async function loadState() {
  let data;
  try {
    const res = await fetch('/state');
    data = await res.json();
  } catch {
    showToast('Could not connect to server', 'error');
    return;
  }

  hardMode = data.hard_mode;
  document.getElementById('hard-mode-toggle').checked = hardMode;
  gameOver  = data.game_over;
  keyStates = {};

  for (let r = 0; r < data.guesses.length; r++) {
    const g = data.guesses[r];
    for (let c = 0; c < WORD_LENGTH; c++) {
      setTileInstant(getTile(r, c), g.word[c].toUpperCase(), g.results[c]);
    }
    currentRow = r + 1;
  }

  if (data.key_states) {
    for (const [letter, result] of Object.entries(data.key_states)) {
      keyStates[letter] = Number(result);
    }
  }

  // On restore just show a simple toast — no fireworks for already-finished games
  if (data.game_over) {
    lastWinGuesses = data.won ? data.guesses.length : 0;
    if (data.won) {
      showToast(winMessage(data.guesses.length), 'win');
    } else if (data.target_word) {
      showToast(data.target_word.toUpperCase(), 'answer', false);
    }
  }
}

// ── Input ─────────────────────────────────────────────────────────────────

function addLetter(letter) {
  if (isAnimating || gameOver || currentInput.length >= WORD_LENGTH) return;
  const tile = getTile(currentRow, currentInput.length);
  tile.textContent    = letter.toUpperCase();
  tile.dataset.state  = 'tbd';
  tile.style.borderColor = '#565758';
  tile.style.transform = 'scale(1.12)';
  setTimeout(() => { tile.style.transform = ''; }, 80);
  currentInput.push(letter.toLowerCase());
}

function deleteLetter() {
  if (isAnimating || gameOver || currentInput.length === 0) return;
  currentInput.pop();
  const tile = getTile(currentRow, currentInput.length);
  tile.textContent       = '';
  tile.dataset.state     = '';
  tile.style.borderColor = '';
  tile.style.transform   = '';
}

async function submitGuess() {
  if (isAnimating || gameOver) return;
  if (currentInput.length < WORD_LENGTH) {
    shakeRow(currentRow);
    showToast('Not enough letters', 'error');
    return;
  }

  const word = currentInput.join('');
  let data;
  try {
    const res = await fetch('/guess', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ word }),
    });
    data = await res.json();
  } catch {
    showToast('Network error', 'error');
    return;
  }

  if (!data.accepted) {
    shakeRow(currentRow);
    showToast(data.error, 'error');
    return;
  }

  isAnimating = true;
  await animateRow(currentRow, word, data.results);
  applyKeyboardColors(word, data.results);

  currentRow++;
  currentInput = [];
  gameOver     = data.game_over;
  isAnimating  = false;

  if (data.game_over) {
    if (data.won) {
      lastWinGuesses = currentRow;
      // Short pause after last tile flips, then fireworks + big message
      setTimeout(() => showWinCelebration(winMessage(currentRow)), 300);
    } else {
      lastWinGuesses = 0;
      // Show "The word was" modal, then stats when user clicks
      setTimeout(() => showAnswerModal(data.target_word), 400);
    }
  }
}

// ── Tile flip animation ───────────────────────────────────────────────────

function animateRow(row, word, results) {
  const HALF    = 150;
  const STAGGER = 300;

  return new Promise(resolve => {
    let done = 0;
    for (let c = 0; c < WORD_LENGTH; c++) {
      const tile   = getTile(row, c);
      const result = results[c];

      setTimeout(() => {
        tile.style.transition = `transform ${HALF}ms ease`;
        tile.style.transform  = 'scaleY(0)';

        setTimeout(() => {
          tile.style.backgroundColor = RESULT_COLOR[result] || '';
          tile.style.borderColor     = RESULT_COLOR[result] || '';
          tile.dataset.state         = String(result);
          tile.style.transform       = 'scaleY(1)';
          done++;
          if (done === WORD_LENGTH) setTimeout(resolve, HALF);
        }, HALF);
      }, c * STAGGER);
    }
  });
}

function shakeRow(row) {
  const el = document.getElementById(`row-${row}`);
  el.classList.add('shake');
  setTimeout(() => el.classList.remove('shake'), 600);
}

// ── Keyboard colour state ─────────────────────────────────────────────────

function applyKeyboardColors(word, results) {
  for (let i = 0; i < WORD_LENGTH; i++) {
    const letter = word[i];
    const result = results[i];
    const prev   = keyStates[letter];
    if (prev === undefined || COLOR_PRIORITY[result] > COLOR_PRIORITY[prev]) {
      keyStates[letter] = result;
    }
  }
}

// ── Toasts ────────────────────────────────────────────────────────────────

function showToast(msg, type = '', autoRemove = true) {
  const area = document.getElementById('toast-area');
  area.querySelectorAll(`.toast.${type || 'plain'}`).forEach(t => t.remove());

  const toast = document.createElement('div');
  toast.className = 'toast' + (type ? ` ${type}` : ' plain');
  toast.textContent = msg;
  area.appendChild(toast);

  if (autoRemove) setTimeout(() => toast.remove(), 2000);
}

function winMessage(guessCount) {
  return ['Genius!', 'Magnificent!', 'Impressive!', 'Splendid!', 'Great!'][
    Math.min(guessCount - 1, 4)
  ];
}

// ── Stats modal ───────────────────────────────────────────────────────────

async function showStatsModal() {
  let s;
  try {
    const res = await fetch('/stats');
    s = await res.json();
  } catch {
    showToast('Could not load stats', 'error');
    return;
  }

  document.getElementById('stat-played').textContent     = s.games_played;
  document.getElementById('stat-win-pct').textContent    = Math.round(s.win_percentage);
  document.getElementById('stat-streak').textContent     = s.current_streak;
  document.getElementById('stat-max-streak').textContent = s.max_streak;

  const dist   = document.getElementById('distribution');
  dist.innerHTML = '';
  const maxVal = Math.max(1, ...Object.values(s.guess_distribution).map(Number));

  for (let i = 1; i <= MAX_GUESSES; i++) {
    const count = Number(s.guess_distribution[String(i)] || 0);
    const pct   = Math.round((count / maxVal) * 100);
    const hl    = gameOver && lastWinGuesses === i;

    const row = document.createElement('div');
    row.className = 'dist-row';
    row.innerHTML = `
      <span class="dist-num">${i}</span>
      <div class="dist-bar-wrap">
        <div class="dist-bar${hl ? ' highlight' : ''}" style="width:${Math.max(4, pct)}%">${count}</div>
      </div>`;
    dist.appendChild(row);
  }

  document.getElementById('stats-modal').classList.remove('hidden');
}

// ── New game ──────────────────────────────────────────────────────────────

async function startNewGame(mode) {
  await fetch('/new-game', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ mode, hard_mode: hardMode }),
  });
  closeModal('stats-modal');
  closeModal('settings-modal');
  closeModal('answer-modal');
  resetBoard();
}

function resetBoard() {
  currentRow     = 0;
  currentInput   = [];
  isAnimating    = false;
  gameOver       = false;
  keyStates      = {};
  lastWinGuesses = 0;
  buildBoard();
  document.getElementById('toast-area').innerHTML = '';
  document.getElementById('win-overlay').classList.add('hidden');
  loadState();
}

// ── Settings ──────────────────────────────────────────────────────────────

function handleHardModeToggle(checked) {
  if (currentRow > 0) {
    showToast('Hard mode can only be changed at the start', 'error');
    document.getElementById('hard-mode-toggle').checked = !checked;
    return;
  }
  hardMode = checked;
  fetch('/new-game', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ mode: 'daily', hard_mode: hardMode }),
  });
}

// ── Modals ────────────────────────────────────────────────────────────────

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

// ── Event wiring ──────────────────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === 'Enter')          submitGuess();
  else if (e.key === 'Backspace') deleteLetter();
  else if (/^[a-zA-Z]$/.test(e.key)) addLetter(e.key);
});

document.getElementById('stats-btn')
  .addEventListener('click', showStatsModal);
document.getElementById('stats-close')
  .addEventListener('click', () => closeModal('stats-modal'));
document.getElementById('stats-close-btn')
  .addEventListener('click', () => closeModal('stats-modal'));

document.getElementById('settings-btn')
  .addEventListener('click', () => document.getElementById('settings-modal').classList.remove('hidden'));
document.getElementById('settings-close')
  .addEventListener('click', () => closeModal('settings-modal'));
document.getElementById('settings-close-btn')
  .addEventListener('click', () => closeModal('settings-modal'));

document.getElementById('new-game-random')
  .addEventListener('click', () => startNewGame('random'));
document.getElementById('new-game-daily')
  .addEventListener('click', () => startNewGame('daily'));

document.getElementById('hard-mode-toggle')
  .addEventListener('change', (e) => handleHardModeToggle(e.target.checked));

// Answer modal → stats
document.getElementById('answer-stats-btn')
  .addEventListener('click', () => {
    closeModal('answer-modal');
    showStatsModal();
  });

// Close modal by clicking backdrop
document.querySelectorAll('.modal').forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });
});

// ── Init ──────────────────────────────────────────────────────────────────

buildBoard();
loadState();

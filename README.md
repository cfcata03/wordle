# 🟩 Wordle Clone

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Dependencies](https://img.shields.io/badge/Dependencies-none-brightgreen)

> A feature-complete desktop Wordle clone built with Python and Tkinter — no external dependencies required.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Demo](#-demo)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Running Tests](#-running-tests)
- [Contributing](#-contributing)

---

## 🧩 Overview

This is a faithful recreation of the popular word-guessing game Wordle, built entirely with Python's standard library. The game features a dark-themed graphical interface with animated tile reveals, an on-screen keyboard, persistent statistics, and a hard mode — all without installing a single external package.

Each day a new word is automatically selected (deterministic by date), or you can start a random game at any time.

---

## ✨ Features

- **🎨 Dark-themed GUI** — clean tile grid and on-screen QWERTY keyboard matching Wordle's aesthetic
- **🔁 Tile flip animation** — tiles animate as they reveal their colors after each guess
- **⌨️ Dual input** — type on your physical keyboard or click the on-screen keys
- **📊 Statistics tracking** — win rate, current streak, max streak, and guess distribution saved locally between sessions
- **💪 Hard mode** — revealed hints (green and yellow letters) must be used in all subsequent guesses
- **📅 Daily word** — the same word for every day (deterministic by date), plus a random mode
- **🚫 Zero dependencies** — uses only Python 3.8+ standard library (`tkinter`, `json`, `datetime`)

---

## 🎬 Demo

```
Guess 1:  C R A N E   →  ⬛ 🟨 🟩 ⬛ 🟩
Guess 2:  S H A R E   →  ⬛ ⬛ 🟩 🟩 🟩
Guess 3:  G R A R E   →  ⬛ 🟩 🟩 🟩 🟩
Guess 4:  B R A R E   →  🟩 🟩 🟩 🟩 🟩

Magnificent! The word was BRARE.
```

**Statistics after game:**

```
Played   Win %   Current Streak   Max Streak
  12      83         4               7

Guess Distribution:
1 |                   0
2 | ████              2
3 | ████████████████  8
4 | ████              2
```

---

## 🛠 Installation

No installation required beyond Python itself.

**Requirements:**
- Python 3.8 or higher
- `tkinter` (bundled with standard CPython — available by default on Windows and macOS)

**Clone the repository:**

```bash
git clone https://github.com/cfcata03/wordle-clone.git
cd wordle-clone
```

**On Linux**, if tkinter is missing:

```bash
# Debian/Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

---

## 🚀 Quick Start

**Option A — Run directly (no installation):**

```bash
python run.py
```

**Option B — Install as a package, then run as a module:**

```bash
pip install -e .
python -m wordle
```

---

## ⚙️ How It Works

### Scoring Algorithm

The core of Wordle is the two-pass letter scoring algorithm, which correctly handles duplicate letters:

```
Pass 1 — Exact matches (CORRECT / green):
  For each position, if guess[i] == target[i]:
    → mark as CORRECT, consume both letters

Pass 2 — Present matches (PRESENT / yellow):
  For each remaining guess letter:
    if it exists anywhere in the remaining target letters:
      → mark as PRESENT, consume that target letter
    else:
      → mark as ABSENT (gray)
```

This ensures duplicate letters in a guess are never over-rewarded.

**Example:** target `abbey`, guess `kebab`

```
Position:  0    1    2    3    4
Guess:     k    e    b    a    b
Target:    a    b    b    e    y

Pass 1 (exact): b at pos 2 == b at pos 2  →  CORRECT
Pass 2 (present):
  k → not in [a, b, _, e, y]  →  ABSENT
  e → in [a, b, _, e, y]      →  PRESENT
  a → in [a, b, _, _, y]      →  PRESENT
  b → not in [_, b, _, _, y]  →  ABSENT  (second b already consumed)

Result:  ⬛ 🟨 🟩 🟨 ⬛
```

### Hard Mode

When hard mode is enabled, the game tracks:
- **Required positions** — letters confirmed green must appear in the same position in all future guesses
- **Required letters** — letters confirmed yellow must appear somewhere in all future guesses

Any guess violating these constraints is rejected with a descriptive error message.

### Statistics Persistence

Stats are saved to `~/.wordle_stats.json` after every game. The streak counter automatically resets if a day is skipped.

---

## 📁 Project Structure

```
wordle-clone/
├── src/
│   └── wordle/
│       ├── __init__.py       # Package entry point
│       ├── __main__.py       # Enables python -m wordle
│       ├── main.py           # App entry point
│       ├── game.py           # Core game logic & scoring algorithm
│       ├── gui.py            # Tkinter UI (tiles, keyboard, dialogs)
│       ├── stats.py          # Statistics persistence (JSON)
│       └── words.py          # Embedded word list & daily/random selection
├── tests/
│   └── test_game.py          # Unit tests for game logic and stats
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## 🧪 Running Tests

The test suite uses Python's built-in `unittest` — no test runner installation required.

```bash
# Run all tests
python -m pytest tests/

# Or with unittest directly
python -m unittest discover tests/
```

**Test coverage includes:**
- ✅ All-correct, all-absent, and mixed scoring cases
- ✅ Duplicate letter handling (the tricky edge case)
- ✅ Win and loss conditions
- ✅ Invalid / too-short word rejection
- ✅ Hard mode constraint validation
- ✅ Stats recording and streak logic

---

## 🤝 Contributing

Contributions are welcome. To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please ensure all tests pass before submitting a PR.

---

*Built with Python 3 and ❤️ — no external packages required.*

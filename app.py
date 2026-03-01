import sys
import os
import secrets

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, render_template, request, session, jsonify
from wordle.game import Game, GuessResult, LetterResult
from wordle.words import get_daily_word, get_random_word
from wordle.stats import load_stats, save_stats, record_result

app = Flask(__name__)

_SECRET_KEY_FILE = os.path.expanduser("~/.wordle_secret_key")


def _get_secret_key() -> str:
    try:
        if os.path.exists(_SECRET_KEY_FILE):
            with open(_SECRET_KEY_FILE, "r") as f:
                key = f.read().strip()
            if key:
                return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    try:
        with open(_SECRET_KEY_FILE, "w") as f:
            f.write(key)
    except OSError:
        pass
    return key


app.secret_key = os.environ.get("FLASK_SECRET_KEY") or _get_secret_key()

MAX_GUESSES = 5


# ── Serialization ────────────────────────────────────────────────────────────

def _game_to_dict(game: Game) -> dict:
    return {
        "target_word": game.target_word,
        "hard_mode": game.hard_mode,
        "max_guesses": game.max_guesses,
        "guesses": [
            {"word": g.word, "results": [r.value for r in g.results]}
            for g in game.guesses
        ],
        "game_over": game.game_over,
        "won": game.won,
        "required_positions": {str(k): v for k, v in game.required_positions.items()},
        "required_letters": list(game.required_letters),
    }


def _game_from_dict(d: dict) -> Game:
    game = Game(
        target_word=d["target_word"],
        hard_mode=d["hard_mode"],
        max_guesses=d["max_guesses"],
    )
    game.game_over = d["game_over"]
    game.won = d["won"]
    game.required_positions = {int(k): v for k, v in d["required_positions"].items()}
    game.required_letters = set(d["required_letters"])
    game.guesses = [
        GuessResult(word=g["word"], results=[LetterResult(r) for r in g["results"]])
        for g in d["guesses"]
    ]
    return game


def _ensure_game() -> dict:
    if "game" not in session:
        game = Game(target_word=get_daily_word(), max_guesses=MAX_GUESSES)
        session["game"] = _game_to_dict(game)
    return session["game"]


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    _ensure_game()
    return render_template("index.html")


@app.route("/state")
def state():
    d = _ensure_game()
    game = _game_from_dict(d)

    COLOR_PRIORITY = {1: 3, 2: 2, 3: 1}
    key_states: dict = {}
    for gr in game.guesses:
        for letter, result in zip(gr.word, gr.results):
            p = COLOR_PRIORITY.get(result.value, 0)
            if p > COLOR_PRIORITY.get(key_states.get(letter, 0), 0):
                key_states[letter] = result.value

    return jsonify({
        "guesses": d["guesses"],
        "game_over": d["game_over"],
        "won": d["won"],
        "max_guesses": d["max_guesses"],
        "hard_mode": d["hard_mode"],
        "key_states": key_states,
        "target_word": d["target_word"] if d["game_over"] else None,
    })


@app.route("/guess", methods=["POST"])
def guess():
    if "game" not in session:
        return jsonify({"accepted": False, "error": "No game in progress"}), 400

    data = request.get_json() or {}
    word = data.get("word", "").strip().lower()

    game = _game_from_dict(session["game"])
    accepted, error, result = game.submit_guess(word)

    if not accepted:
        return jsonify({"accepted": False, "error": error})

    session["game"] = _game_to_dict(game)
    session.modified = True

    if game.game_over:
        stats = load_stats()
        stats = record_result(stats, won=game.won, num_guesses=len(game.guesses))
        save_stats(stats)

    return jsonify({
        "accepted": True,
        "results": [r.value for r in result.results],
        "game_over": game.game_over,
        "won": game.won,
        "target_word": game.target_word if game.game_over else None,
    })


@app.route("/new-game", methods=["POST"])
def new_game():
    data = request.get_json() or {}
    mode = data.get("mode", "daily")
    hard_mode = bool(data.get("hard_mode", False))
    word = get_random_word() if mode == "random" else get_daily_word()
    game = Game(target_word=word, hard_mode=hard_mode, max_guesses=MAX_GUESSES)
    session["game"] = _game_to_dict(game)
    session.modified = True
    return jsonify({"ok": True, "hard_mode": hard_mode})


@app.route("/stats")
def stats_route():
    s = load_stats()
    return jsonify({
        "games_played": s.games_played,
        "games_won": s.games_won,
        "win_percentage": s.win_percentage,
        "current_streak": s.current_streak,
        "max_streak": s.max_streak,
        "guess_distribution": s.guess_distribution,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)

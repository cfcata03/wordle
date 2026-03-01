import json
import os
import datetime
from dataclasses import dataclass, field, asdict

STATS_FILE = os.path.expanduser("~/.wordle_stats.json")


@dataclass
class Stats:
    games_played: int = 0
    games_won: int = 0
    current_streak: int = 0
    max_streak: int = 0
    guess_distribution: dict = field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0}
    )
    last_played_date: str = ""

    @property
    def win_percentage(self) -> float:
        if self.games_played == 0:
            return 0.0
        return round((self.games_won / self.games_played) * 100, 1)


def load_stats() -> Stats:
    if not os.path.exists(STATS_FILE):
        return Stats()
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = Stats()
        for k, v in data.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s
    except (json.JSONDecodeError, KeyError, TypeError):
        return Stats()


def save_stats(stats: Stats) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(stats), f, indent=2)


def record_result(stats: Stats, won: bool, num_guesses: int) -> Stats:
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    stats.games_played += 1

    if won:
        stats.games_won += 1
        key = str(num_guesses)
        stats.guess_distribution[key] = stats.guess_distribution.get(key, 0) + 1
        if stats.last_played_date in ("", yesterday):
            stats.current_streak += 1
        else:
            stats.current_streak = 1
        stats.max_streak = max(stats.max_streak, stats.current_streak)
    else:
        stats.current_streak = 0

    stats.last_played_date = today
    return stats

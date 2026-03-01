from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional



class LetterResult(Enum):
    CORRECT = auto()
    PRESENT = auto()
    ABSENT = auto()
    UNKNOWN = auto()


@dataclass
class GuessResult:
    word: str
    results: list


@dataclass
class Game:
    target_word: str
    hard_mode: bool = False
    max_guesses: int = 6

    guesses: list = field(default_factory=list)
    game_over: bool = False
    won: bool = False

    # Hard mode state
    required_positions: dict = field(default_factory=dict)  # pos -> letter
    required_letters: set = field(default_factory=set)      # letters that must appear

    def submit_guess(self, word: str) -> tuple:
        """
        Returns (accepted, error_message, GuessResult | None).
        """
        word = word.lower()

        if self.game_over:
            return False, "Game is over", None

        if len(word) != 5:
            return False, "Word must be 5 letters", None

        if self.hard_mode:
            valid, error = self._validate_hard_mode(word)
            if not valid:
                return False, error, None

        results = self._score_guess(word)
        guess_result = GuessResult(word=word, results=results)
        self.guesses.append(guess_result)

        if self.hard_mode:
            self._update_hard_mode_state(guess_result)

        if word == self.target_word:
            self.won = True
            self.game_over = True
        elif len(self.guesses) >= self.max_guesses:
            self.game_over = True

        return True, "", guess_result

    def _score_guess(self, word: str) -> list:
        target = list(self.target_word)
        guess = list(word)
        results = [LetterResult.ABSENT] * 5

        # Pass 1: exact matches
        for i in range(5):
            if guess[i] == target[i]:
                results[i] = LetterResult.CORRECT
                target[i] = None
                guess[i] = None

        # Pass 2: present matches
        for i in range(5):
            if guess[i] is None:
                continue
            if guess[i] in target:
                results[i] = LetterResult.PRESENT
                target[target.index(guess[i])] = None

        return results

    def _validate_hard_mode(self, word: str) -> tuple:
        ordinals = ["1st", "2nd", "3rd", "4th", "5th"]
        for pos, letter in self.required_positions.items():
            if word[pos] != letter:
                return False, f"{ordinals[pos]} letter must be {letter.upper()}"
        for letter in self.required_letters:
            if letter not in word:
                return False, f"Guess must contain {letter.upper()}"
        return True, ""

    def _update_hard_mode_state(self, result: GuessResult) -> None:
        for i, letter_result in enumerate(result.results):
            letter = result.word[i]
            if letter_result == LetterResult.CORRECT:
                self.required_positions[i] = letter
                self.required_letters.discard(letter)
            elif letter_result == LetterResult.PRESENT:
                if i not in self.required_positions:
                    self.required_letters.add(letter)

    @property
    def current_row(self) -> int:
        return len(self.guesses)

    @property
    def guesses_remaining(self) -> int:
        return self.max_guesses - len(self.guesses)

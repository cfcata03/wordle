import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wordle.game import Game, LetterResult, GuessResult
from wordle.stats import Stats, record_result


class TestScoring(unittest.TestCase):

    def test_all_correct(self):
        g = Game("crane")
        results = g._score_guess("crane")
        self.assertEqual(results, [LetterResult.CORRECT] * 5)

    def test_all_absent(self):
        g = Game("crane")
        results = g._score_guess("jumbo")
        self.assertEqual(results, [LetterResult.ABSENT] * 5)

    def test_present_letter(self):
        g = Game("crane")
        results = g._score_guess("acorn")
        # a: present (a in crane, not pos 0)
        # c: present (c in crane, not pos 1)
        # o: absent
        # r: present (r in crane, not pos 3)
        # n: present (n in crane, not pos 4)
        self.assertEqual(results[0], LetterResult.PRESENT)  # a
        self.assertEqual(results[1], LetterResult.PRESENT)  # c
        self.assertEqual(results[2], LetterResult.ABSENT)   # o

    def test_correct_overrides_present(self):
        g = Game("abbey")
        # target: a b b e y
        # guess:  kebab -> k e b a b
        results = g._score_guess("kebab")
        self.assertEqual(results[0], LetterResult.ABSENT)   # k
        self.assertEqual(results[1], LetterResult.PRESENT)  # e (in abbey)
        self.assertEqual(results[2], LetterResult.CORRECT)  # b at pos 2
        self.assertEqual(results[3], LetterResult.PRESENT)  # a (in abbey)
        # abbey has TWO b's; one consumed by CORRECT at pos 2, so the second b
        # in guess (pos 4) still matches the remaining b at target[1] → PRESENT
        self.assertEqual(results[4], LetterResult.PRESENT)  # b (one b still in target)

    def test_duplicate_not_double_counted(self):
        # target: "speed", guess: "eerie"
        # only one 'e' should be counted from target at position 1
        g = Game("speed")
        results = g._score_guess("eerie")
        # e at pos 0: present (one e available from speed pos 1)
        # e at pos 1: present? No — speed has e at pos 1 and 2
        # Actually speed: s-p-e-e-d, eerie: e-e-r-i-e
        # Pass 1: no exact matches (e[1]!=p, e[2]!=e... wait e at pos2 == e at pos2 YES)
        # pos2: r vs e -> absent. Let me recalc:
        # eerie: e(0) e(1) r(2) i(3) e(4)
        # speed: s(0) p(1) e(2) e(3) d(4)
        # Pass1 exact: none match
        # Pass2: e[0] in [s,p,e,e,d] -> present, consume one e -> [s,p,None,e,d]
        #        e[1] in [s,p,None,e,d] -> present, consume -> [s,p,None,None,d]
        #        r[2] -> absent
        #        i[3] -> absent
        #        e[4] in [s,p,None,None,d] -> absent (no e left)
        self.assertEqual(results[0], LetterResult.PRESENT)
        self.assertEqual(results[1], LetterResult.PRESENT)
        self.assertEqual(results[2], LetterResult.ABSENT)
        self.assertEqual(results[3], LetterResult.ABSENT)
        self.assertEqual(results[4], LetterResult.ABSENT)

    def test_win(self):
        g = Game("hello")
        accepted, _, result = g.submit_guess("hello")
        self.assertTrue(accepted)
        self.assertTrue(g.won)
        self.assertTrue(g.game_over)

    def test_loss_after_six_guesses(self):
        g = Game("hello")
        for _ in range(6):
            g.submit_guess("world")
        self.assertFalse(g.won)
        self.assertTrue(g.game_over)

    def test_any_five_letter_word_accepted(self):
        g = Game("crane")
        accepted, _, result = g.submit_guess("zzzzz")
        self.assertTrue(accepted)
        self.assertIsNotNone(result)

    def test_too_short_rejected(self):
        g = Game("crane")
        accepted, error, _ = g.submit_guess("hi")
        self.assertFalse(accepted)
        self.assertIn("5", error)

    def test_no_more_guesses_after_game_over(self):
        g = Game("crane")
        g.submit_guess("crane")
        accepted, _, _ = g.submit_guess("crane")
        self.assertFalse(accepted)


class TestHardMode(unittest.TestCase):

    def test_hard_mode_correct_position_enforced(self):
        g = Game("crane", hard_mode=True)
        # guess "crake": c-r-a-k-e
        # c: correct(0), r: correct(1), a: correct(2), k: absent, e: correct(4)
        g.submit_guess("crake")
        # Next guess must have c at 0, r at 1, a at 2, e at 4
        valid, error = g._validate_hard_mode("crisp")
        # c at 0: ok, r at 1: ok, i at 2: WRONG (must be a)
        self.assertFalse(valid)
        self.assertIn("3rd", error)

    def test_hard_mode_present_letter_enforced(self):
        g = Game("crane", hard_mode=True)
        # guess "actor": a(present), c(present), t(absent), o(absent), r(present)
        g.submit_guess("actor")
        valid, error = g._validate_hard_mode("bliss")
        # bliss doesn't contain a, c, or r
        self.assertFalse(valid)

    def test_hard_mode_valid_guess_accepted(self):
        g = Game("crane", hard_mode=True)
        g.submit_guess("actor")
        # "acorn" contains a, c, r — should be valid (if in word list)
        # We test the hard mode logic directly, not word list validation
        valid, error = g._validate_hard_mode("acorn")
        self.assertTrue(valid)


class TestStats(unittest.TestCase):

    def test_initial_stats(self):
        s = Stats()
        self.assertEqual(s.games_played, 0)
        self.assertEqual(s.win_percentage, 0.0)

    def test_record_win_increments_correctly(self):
        s = Stats()
        s = record_result(s, won=True, num_guesses=3)
        self.assertEqual(s.games_played, 1)
        self.assertEqual(s.games_won, 1)
        self.assertEqual(s.current_streak, 1)
        self.assertEqual(s.max_streak, 1)
        self.assertEqual(s.guess_distribution["3"], 1)

    def test_record_loss_resets_streak(self):
        s = Stats()
        s = record_result(s, won=True, num_guesses=2)
        s = record_result(s, won=False, num_guesses=6)
        self.assertEqual(s.current_streak, 0)
        self.assertEqual(s.max_streak, 1)

    def test_win_percentage_calculation(self):
        s = Stats()
        s = record_result(s, won=True, num_guesses=1)
        s = record_result(s, won=True, num_guesses=2)
        s = record_result(s, won=False, num_guesses=6)
        self.assertAlmostEqual(s.win_percentage, 66.7, places=0)


if __name__ == "__main__":
    unittest.main()

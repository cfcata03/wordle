import tkinter as tk
import tkinter.font as tkfont

from .game import Game, LetterResult
from .stats import load_stats, save_stats, record_result
from .words import get_daily_word, get_random_word

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------
BG_COLOR           = "#121213"
TILE_EMPTY_BG      = "#121213"
TILE_EMPTY_BORDER  = "#3a3a3c"
TILE_FILLED_BORDER = "#565758"
COLOR_CORRECT      = "#538d4e"
COLOR_PRESENT      = "#b59f3b"
COLOR_ABSENT       = "#3a3a3c"
COLOR_UNKNOWN      = "#818384"
TEXT_COLOR         = "#ffffff"
MODAL_BG           = "#1a1a1b"
HEADER_BORDER      = "#3a3a3c"

FONT_TILE   = ("Helvetica", 36, "bold")
FONT_HEADER = ("Helvetica", 16, "bold")
FONT_TITLE  = ("Helvetica", 22, "bold")
FONT_LABEL  = ("Helvetica", 10)
FONT_STAT   = ("Helvetica", 26, "bold")

RESULT_COLOR_MAP = {
    LetterResult.CORRECT: COLOR_CORRECT,
    LetterResult.PRESENT: COLOR_PRESENT,
    LetterResult.ABSENT:  COLOR_ABSENT,
}

WIN_MESSAGES = ["Genius!", "Magnificent!", "Impressive!", "Splendid!", "Great!"]

TILE_SIZE   = 80
TILE_PAD    = 6
TILE_RADIUS = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rounded_points(x1, y1, x2, y2, r):
    """Polygon points for a smooth rounded rectangle."""
    return [
        x1 + r, y1,  x2 - r, y1,  x2, y1,  x2, y1 + r,
        x2, y2 - r,  x2, y2,  x2 - r, y2,  x1 + r, y2,
        x1, y2,  x1, y2 - r,  x1, y1 + r,  x1, y1,
    ]


def _darken(hex_color, factor=0.75):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def _measure_text(text, font_spec):
    """Return (width, height) of rendered text in pixels."""
    weight = font_spec[2] if len(font_spec) > 2 else "normal"
    f = tkfont.Font(family=font_spec[0], size=font_spec[1], weight=weight)
    return f.measure(text), f.metrics("linespace")


def make_button(parent, text, bg, command, font=None, min_width=0):
    """Canvas-based button with rounded corners and hover effect."""
    if font is None:
        font = FONT_LABEL
    padx, pady = 22, 9
    tw, th = _measure_text(text, font)
    w = max(tw + padx * 2, min_width)
    h = th + pady * 2
    r = h // 2  # pill shape

    cv = tk.Canvas(parent, width=w, height=h,
                   bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
    pts = _rounded_points(0, 0, w, h, r)
    rect = cv.create_polygon(pts, smooth=True, fill=bg, outline="")
    cv.create_text(w // 2, h // 2, text=text, font=font, fill=TEXT_COLOR)

    dark = _darken(bg)

    def on_click(_e):  command()
    def on_enter(_e):  cv.itemconfig(rect, fill=dark)
    def on_leave(_e):  cv.itemconfig(rect, fill=bg)

    cv.bind("<Button-1>", on_click)
    cv.bind("<Enter>",    on_enter)
    cv.bind("<Leave>",    on_leave)
    return cv


# ---------------------------------------------------------------------------
# Tile (Canvas-based, supports rounded corners + flip animation)
# ---------------------------------------------------------------------------

class Tile(tk.Canvas):
    RADIUS = TILE_RADIUS

    def __init__(self, parent):
        super().__init__(parent, width=TILE_SIZE, height=TILE_SIZE,
                         bg=BG_COLOR, highlightthickness=0)
        pad = 2
        self._pad = pad
        pts = _rounded_points(pad, pad, TILE_SIZE - pad, TILE_SIZE - pad, self.RADIUS)
        self._rect = self.create_polygon(
            pts, smooth=True,
            fill=TILE_EMPTY_BG, outline=TILE_EMPTY_BORDER, width=2,
        )
        self._text = self.create_text(
            TILE_SIZE // 2, TILE_SIZE // 2,
            text="", font=FONT_TILE, fill=TEXT_COLOR,
        )

    def set_letter(self, letter):
        self.itemconfig(self._text, text=letter)
        outline = TILE_FILLED_BORDER if letter else TILE_EMPTY_BORDER
        self.itemconfig(self._rect, outline=outline, fill=TILE_EMPTY_BG)

    def set_color(self, bg):
        self.itemconfig(self._rect, fill=bg, outline=bg)

    def squish_to(self, progress):
        """0.0 = full height, 1.0 = flat line."""
        pad = self._pad
        center = TILE_SIZE // 2
        half_h = max(1, int((center - pad) * (1 - progress)))
        y1, y2 = center - half_h, center + half_h
        r = min(self.RADIUS, half_h)
        pts = _rounded_points(pad, y1, TILE_SIZE - pad, y2, r)
        self.coords(self._rect, pts)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class WordleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wordle")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        self.hard_mode = tk.BooleanVar(value=False)
        self.stats = load_stats()

        self._start_game(get_daily_word())
        self._center_window(560, 700)

    def _center_window(self, width, height):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def _start_game(self, word):
        self.game = Game(target_word=word, hard_mode=self.hard_mode.get(), max_guesses=5)
        self.current_input = []
        self._build_ui()

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._build_header()
        self._build_board()
        self.bind("<Key>", self._on_key_press)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self):
        header = tk.Frame(self, bg=BG_COLOR)
        header.pack(fill="x", pady=(8, 0))

        settings_btn = tk.Button(
            header, text="⚙", font=("Helvetica", 16),
            bg=BG_COLOR, fg=TEXT_COLOR,
            relief="flat", bd=0, cursor="hand2",
            activebackground=BG_COLOR, activeforeground=TEXT_COLOR,
            command=self._show_settings_menu,
        )
        settings_btn.pack(side="left", padx=12)
        self._settings_btn = settings_btn

        tk.Label(header, text="Wordle", font=FONT_TITLE,
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(side="left", expand=True)

        tk.Button(
            header, text="📊", font=("Helvetica", 16),
            bg=BG_COLOR, fg=TEXT_COLOR,
            relief="flat", bd=0, cursor="hand2",
            activebackground=BG_COLOR, activeforeground=TEXT_COLOR,
            command=self._show_stats_modal,
        ).pack(side="right", padx=12)

        tk.Frame(self, bg=HEADER_BORDER, height=1).pack(fill="x", pady=(8, 0))

    # ------------------------------------------------------------------
    # Board
    # ------------------------------------------------------------------

    def _build_board(self):
        outer = tk.Frame(self, bg=BG_COLOR)
        outer.pack(pady=20)

        self.tiles = []
        for row in range(5):
            row_tiles = []
            for col in range(5):
                tile = Tile(outer)
                tile.grid(row=row, column=col, padx=TILE_PAD, pady=TILE_PAD)
                row_tiles.append(tile)
            self.tiles.append(row_tiles)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _on_key_press(self, event):
        key = event.keysym.upper()
        if key == "RETURN":
            self._submit_guess()
        elif key == "BACKSPACE":
            self._delete_letter()
        elif len(key) == 1 and key.isalpha():
            self._add_letter(key)

    def _add_letter(self, letter):
        if self.game.game_over or len(self.current_input) >= 5:
            return
        self.current_input.append(letter.upper())
        col = len(self.current_input) - 1
        self.tiles[self.game.current_row][col].set_letter(letter.upper())

    def _delete_letter(self):
        if self.game.game_over or not self.current_input:
            return
        col = len(self.current_input) - 1
        self.current_input.pop()
        self.tiles[self.game.current_row][col].set_letter("")

    def _submit_guess(self):
        if self.game.game_over:
            return
        word = "".join(self.current_input).lower()
        if len(word) < 5:
            self._show_toast("Not enough letters")
            return
        accepted, error, result = self.game.submit_guess(word)
        if not accepted:
            self._show_toast(error)
            return
        committed_row = self.game.current_row - 1
        self.current_input.clear()
        self._reveal_row(committed_row, result)

    # ------------------------------------------------------------------
    # Tile reveal animation
    # ------------------------------------------------------------------

    def _reveal_row(self, row, result):
        def reveal_tile(col):
            if col >= 5:
                self.after(200, self._check_game_over)
                return
            bg = RESULT_COLOR_MAP[result.results[col]]
            self._animate_flip(self.tiles[row][col], bg,
                               callback=lambda: reveal_tile(col + 1))
        reveal_tile(0)

    def _animate_flip(self, tile, new_bg, callback=None, steps=5):
        step_ms = 20

        def shrink(step):
            tile.squish_to(step / steps)
            if step < steps:
                tile.after(step_ms, lambda: shrink(step + 1))
            else:
                tile.set_color(new_bg)
                tile.after(step_ms, lambda: expand(0))

        def expand(step):
            tile.squish_to(1 - step / steps)
            if step < steps:
                tile.after(step_ms, lambda: expand(step + 1))
            else:
                tile.squish_to(0)
                if callback:
                    callback()

        shrink(0)

    # ------------------------------------------------------------------
    # Game over
    # ------------------------------------------------------------------

    def _check_game_over(self):
        if not self.game.game_over:
            return
        self.stats = record_result(
            self.stats,
            won=self.game.won,
            num_guesses=len(self.game.guesses),
        )
        save_stats(self.stats)

        if self.game.won:
            msg = WIN_MESSAGES[len(self.game.guesses) - 1]
            self.after(400, lambda: self._show_win_toast(msg))
        else:
            answer = self.game.target_word.upper()
            self.after(1600, lambda: self._show_answer_modal(answer))

    def _show_win_toast(self, message):
        font = ("Helvetica", 26, "bold")
        padx, pady = 28, 16
        tw, th = _measure_text(message, font)
        w, h = tw + padx * 2, th + pady * 2
        r = h // 2  # pill shape

        toast = tk.Canvas(self, width=w, height=h,
                          bg=BG_COLOR, highlightthickness=0)
        pts = _rounded_points(0, 0, w, h, r)
        toast.create_polygon(pts, smooth=True, fill=TEXT_COLOR, outline="")
        toast.create_text(w // 2, h // 2, text=message, font=font, fill="#000000")
        toast.place(relx=0.5, rely=0.5, anchor="center")
        self.after(1800, toast.destroy)
        self.after(1900, self._show_stats_modal)

    def _show_answer_modal(self, answer):
        modal = tk.Toplevel(self)
        modal.title("")
        modal.configure(bg=MODAL_BG)
        modal.resizable(False, False)
        modal.grab_set()
        modal.focus_set()

        self.update_idletasks()
        mx = self.winfo_x() + (self.winfo_width() - 280) // 2
        my = self.winfo_y() + (self.winfo_height() - 170) // 2
        modal.geometry(f"280x170+{mx}+{my}")

        tk.Label(modal, text="The word was",
                 font=FONT_LABEL, bg=MODAL_BG, fg="#aaaaaa").pack(pady=(28, 4))
        tk.Label(modal, text=answer,
                 font=("Helvetica", 32, "bold"), bg=MODAL_BG, fg=TEXT_COLOR).pack()

        make_button(modal, "See Stats", COLOR_CORRECT,
                    command=lambda: [modal.destroy(), self._show_stats_modal()],
                    min_width=110).pack(pady=(18, 0))

    # ------------------------------------------------------------------
    # Toast notification
    # ------------------------------------------------------------------

    def _show_toast(self, text, duration=1400):
        toast = tk.Label(
            self, text=text, font=FONT_HEADER,
            bg=TEXT_COLOR, fg="#000000", padx=14, pady=8, relief="flat",
        )
        toast.place(relx=0.5, y=100, anchor="center")
        self.after(duration, toast.destroy)

    # ------------------------------------------------------------------
    # Stats modal
    # ------------------------------------------------------------------

    def _show_stats_modal(self):
        modal = tk.Toplevel(self)
        modal.title("Statistics")
        modal.configure(bg=MODAL_BG)
        modal.resizable(False, False)
        modal.grab_set()
        modal.focus_set()

        self.update_idletasks()
        mx = self.winfo_x() + (self.winfo_width() - 340) // 2
        my = self.winfo_y() + (self.winfo_height() - 420) // 2
        modal.geometry(f"340x420+{mx}+{my}")

        tk.Label(modal, text="STATISTICS", font=FONT_HEADER,
                 bg=MODAL_BG, fg=TEXT_COLOR).pack(pady=(18, 8))

        stats_frame = tk.Frame(modal, bg=MODAL_BG)
        stats_frame.pack()

        items = [
            (str(self.stats.games_played),        "Played"),
            (f"{self.stats.win_percentage:.0f}",  "Win %"),
            (str(self.stats.current_streak),      "Current\nStreak"),
            (str(self.stats.max_streak),          "Max\nStreak"),
        ]
        for value, label in items:
            cell = tk.Frame(stats_frame, bg=MODAL_BG)
            cell.pack(side="left", padx=12)
            tk.Label(cell, text=value, font=FONT_STAT,
                     bg=MODAL_BG, fg=TEXT_COLOR).pack()
            tk.Label(cell, text=label, font=FONT_LABEL,
                     bg=MODAL_BG, fg=TEXT_COLOR, justify="center").pack()

        tk.Label(modal, text="GUESS DISTRIBUTION", font=FONT_LABEL,
                 bg=MODAL_BG, fg=TEXT_COLOR).pack(pady=(18, 6))

        dist_frame = tk.Frame(modal, bg=MODAL_BG)
        dist_frame.pack(fill="x", padx=30)

        max_val = max(self.stats.guess_distribution.values(), default=1) or 1
        for guess_num in range(1, 6):
            count = self.stats.guess_distribution.get(str(guess_num), 0)
            bar_width = max(24, int((count / max_val) * 180))
            row = tk.Frame(dist_frame, bg=MODAL_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=str(guess_num), font=FONT_LABEL,
                     bg=MODAL_BG, fg=TEXT_COLOR, width=2, anchor="e").pack(side="left")
            bar_color = (COLOR_CORRECT
                         if self.game.won and len(self.game.guesses) == guess_num
                         else COLOR_ABSENT)
            bar_frame = tk.Frame(row, bg=bar_color, height=22, width=bar_width)
            bar_frame.pack(side="left", padx=4)
            bar_frame.pack_propagate(False)
            tk.Label(bar_frame, text=str(count), font=FONT_LABEL,
                     bg=bar_color, fg=TEXT_COLOR, anchor="e").pack(
                         side="right", padx=4, fill="y")

        btn_frame = tk.Frame(modal, bg=MODAL_BG)
        btn_frame.pack(pady=20)

        make_button(btn_frame, "New Game", COLOR_CORRECT, min_width=100,
                    command=lambda: [modal.destroy(),
                                     self._start_game(get_random_word())]
                    ).pack(side="left", padx=8)

        make_button(btn_frame, "Close", COLOR_ABSENT, min_width=100,
                    command=modal.destroy).pack(side="left", padx=8)

    # ------------------------------------------------------------------
    # Settings menu
    # ------------------------------------------------------------------

    def _show_settings_menu(self):
        menu = tk.Menu(
            self, tearoff=0,
            bg=MODAL_BG, fg=TEXT_COLOR,
            activebackground="#3a3a3c", activeforeground=TEXT_COLOR,
            font=FONT_LABEL,
        )
        menu.add_checkbutton(label="Hard Mode", variable=self.hard_mode,
                             command=self._toggle_hard_mode)
        menu.add_separator()
        menu.add_command(label="New Game (Daily)", command=self._new_daily_game)
        menu.add_command(label="New Game (Random)",
                         command=lambda: self._start_game(get_random_word()))
        menu.add_separator()
        menu.add_command(label="Statistics", command=self._show_stats_modal)

        x = self._settings_btn.winfo_rootx()
        y = self._settings_btn.winfo_rooty() + self._settings_btn.winfo_height()
        menu.post(x, y)

    def _toggle_hard_mode(self):
        if len(self.game.guesses) > 0:
            self.hard_mode.set(not self.hard_mode.get())
            self._show_toast("Hard Mode can only be changed at the start!")
        else:
            self.game.hard_mode = self.hard_mode.get()

    def _new_daily_game(self):
        self._start_game(get_daily_word())

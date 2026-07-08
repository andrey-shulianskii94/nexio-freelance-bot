"""
splash.py — Экран загрузки Nexio.
Показывается при старте приложения, исчезает через ~2.5 секунды.
Использует Canvas для орбиты-логотипа и полосы прогресса.
"""

import tkinter as tk
import math


ACCENT   = "#6c63ff"
ACCENT2  = "#a78bfa"
BG       = "#0f0f1a"
BG2      = "#1e1e38"
BORDER   = "#2a2a45"
TEXT     = "#e2e2f0"
MUTED    = "#4a4a6e"

DURATION_MS  = 2500   # полное время показа
PROGRESS_MS  = 2200   # за сколько заполняется бар
FADE_STEPS   = 20     # шагов fade-out


class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)          # без рамки
        self.configure(bg=BG)
        self.attributes("-alpha", 0.0)       # начинаем прозрачными
        self.lift()
        self.focus_force()

        w, h = 360, 280
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build()
        self._fade_in()
        self._animate_logo(0)
        self._animate_progress()
        self.after(DURATION_MS, self._fade_out)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build(self):
        # Тонкая рамка
        outer = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(outer, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True)

        # Логотип Canvas
        self._canvas = tk.Canvas(inner, width=100, height=100,
                                 bg=BG, highlightthickness=0)
        self._canvas.pack(pady=(36, 0))
        self._draw_orbit(0.0)

        # Название
        tk.Label(inner, text="Nexio",
                 font=("Segoe UI", 26, "bold"),
                 bg=BG, fg=TEXT).pack(pady=(10, 2))

        tk.Label(inner, text="мониторинг фриланс-каналов",
                 font=("Segoe UI", 9),
                 bg=BG, fg=MUTED).pack()

        # Прогресс-бар
        prog_frame = tk.Frame(inner, bg=BG)
        prog_frame.pack(pady=(24, 0))

        bar_bg = tk.Frame(prog_frame, bg=BG2,
                          width=180, height=2)
        bar_bg.pack()
        bar_bg.pack_propagate(False)

        self._bar = tk.Frame(bar_bg, bg=ACCENT, width=0, height=2)
        self._bar.place(x=0, y=0, height=2)

        # Статус
        self._status_var = tk.StringVar(value="Инициализация...")
        tk.Label(inner, textvariable=self._status_var,
                 font=("Segoe UI", 8),
                 bg=BG, fg=MUTED).pack(pady=(8, 0))

    def _draw_orbit(self, angle: float):
        c = self._canvas
        c.delete("all")
        cx, cy = 50, 50

        # Внешнее кольцо пунктиром — имитируем dash через дуги
        r_outer = 38
        steps = 24
        for i in range(steps):
            a0 = math.radians(i * 360 / steps + angle * 0.5)
            a1 = math.radians((i + 0.55) * 360 / steps + angle * 0.5)
            x0 = cx + r_outer * math.cos(a0) - 2
            y0 = cy + r_outer * math.sin(a0) - 2
            x1 = cx + r_outer * math.cos(a1) + 2
            y1 = cy + r_outer * math.sin(a1) + 2
            c.create_arc(cx - r_outer, cy - r_outer,
                         cx + r_outer, cy + r_outer,
                         start=math.degrees(a0),
                         extent=math.degrees(a1 - a0),
                         style=tk.ARC, outline=ACCENT, width=1)

        # Среднее кольцо
        r_mid = 22
        c.create_oval(cx - r_mid, cy - r_mid,
                      cx + r_mid, cy + r_mid,
                      outline=ACCENT2, width=1)

        # Центральная точка
        c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                      fill=ACCENT, outline="")

        # Спутник на внешней орбите — вращается
        rad = math.radians(angle)
        sx = cx + r_outer * math.cos(rad)
        sy = cy + r_outer * math.sin(rad)
        c.create_oval(sx - 4, sy - 4, sx + 4, sy + 4,
                      fill=ACCENT2, outline="")

        # Маленький спутник на среднем кольце — в обратную сторону
        rad2 = math.radians(-angle * 1.5)
        sx2 = cx + r_mid * math.cos(rad2)
        sy2 = cy + r_mid * math.sin(rad2)
        c.create_oval(sx2 - 2.5, sy2 - 2.5, sx2 + 2.5, sy2 + 2.5,
                      fill=ACCENT, outline="")

    def _animate_logo(self, angle: float):
        self._draw_orbit(angle)
        self._logo_job = self.after(30, lambda: self._animate_logo(angle + 3))

    # ── Прогресс-бар ─────────────────────────────────────────────────────

    def _animate_progress(self):
        steps   = 60
        total   = PROGRESS_MS
        delay   = total // steps
        bar_w   = 180
        msgs    = [
            (0,    "Инициализация..."),
            (20,   "Загрузка настроек..."),
            (45,   "Подключение к Telegram..."),
            (80,   "Готово!"),
        ]

        def step(i):
            if i > steps:
                return
            w = int(bar_w * i / steps)
            self._bar.place(x=0, y=0, width=w, height=2)
            for pct, msg in reversed(msgs):
                if i >= pct * steps // 100:
                    self._status_var.set(msg)
                    break
            self.after(delay, lambda: step(i + 1))

        step(0)

    # ── Fade ──────────────────────────────────────────────────────────────

    def _fade_in(self):
        def step(alpha):
            if alpha >= 1.0:
                self.attributes("-alpha", 1.0)
                return
            self.attributes("-alpha", alpha)
            self.after(16, lambda: step(alpha + 0.08))
        step(0.0)

    def _fade_out(self):
        if hasattr(self, "_logo_job"):
            self.after_cancel(self._logo_job)

        def step(alpha):
            if alpha <= 0.0:
                self.destroy()
                return
            self.attributes("-alpha", alpha)
            self.after(16, lambda: step(alpha - 0.07))
        step(1.0)

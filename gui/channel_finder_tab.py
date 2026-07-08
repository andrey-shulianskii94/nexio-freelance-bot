"""
channel_finder_tab.py — Поиск Telegram-каналов.
Палитра: Telegram Desktop Dark.
Колонки: динамические, по выбранным языкам.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import asyncio
import os
import json
import re
import sys
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

load_dotenv()
API_ID   = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
MIN_MEMBERS = 100

# ─── Nexio — Violet Midnight palette ─────────────────────────────────────────
BG       = "#0f0f1a"   # основной фон
BG2      = "#0b0b14"   # шапка / топбар
PANEL    = "#16162a"   # карточки
PANEL2   = "#1e1e35"   # поля ввода / листбоксы
BORDER   = "#2a2a45"   # граница
BLUE     = "#6c63ff"   # фиолетовый — основной акцент
BLUE2    = "#5048e5"   # dim-фиолетовый
GREEN    = "#4FAE4E"   # зелёный (вступил)
GREEN2   = "#0f2a14"   # тёмно-зелёный фон (вступил)
ORANGE   = "#f97316"   # оранжевый для ES
RED      = "#ef4444"   # красный
GOLD     = "#F0B429"   # золото — итоги
TEXT     = "#e8e8f4"   # основной текст — чуть ярче
TEXT2    = "#9090b8"   # вторичный — контраст выше (был #7070a0)
MUTED    = "#3a3a5a"   # заглушённый — чуть светлее
HOVER    = "#252540"

F  = "Segoe UI"
FM = "Consolas"

# ─── Конфиг языков ───────────────────────────────────────────────────────────
LANGS = {
    "RU": dict(
        flag="🇷🇺", label="RU — Русскоязычные",
        hdr="#1a1a32", bg="#16162a", fg="#c4b8ff", hi=BLUE,
        ton=BLUE2,     toff=PANEL,
    ),
    "EN": dict(
        flag="🇬🇧", label="EN — English",
        hdr="#142820", bg="#101e18", fg="#86efac", hi=GREEN,
        ton="#0f2a14",  toff=PANEL,
    ),
    "ES": dict(
        flag="🇪🇸", label="ES — Español",
        hdr="#281808", bg="#1e1008", fg="#fdba74", hi=ORANGE,
        ton="#3d1a06",  toff=PANEL,
    ),
}

RE_CYR = re.compile(r'[а-яёА-ЯЁ]')
RE_ESP = re.compile(r'[áéíóúüñ¿¡]', re.IGNORECASE)

# Blacklist — каналы которые точно не нужны (школы, курсы, агрегаторы резюме)
# НЕ блокируем jobs/вакансии — там тоже бывают заказы
_BLACKLIST = re.compile(
    r"школа|курс[ыа]?\b|обучени|учебн|академи|bootcamp|guru\b"
    r"|work\.ru|headhunter|hh\.ru|карьер"
    r"|smm.?ru|маркетинг.?паблик"
    r"|резюме.?канал|канал.?резюме",
    re.IGNORECASE
)

# IT/фриланс каналы — принимаем всегда
_IT_CHAN = re.compile(
    r"python|javascript|js\b|react|vue|angular|flutter|kotlin|swift|golang|go\b"
    r"|django|fastapi|node|backend|frontend|fullstack|full.?stack"
    r"|devops|docker|kubernetes|k8s|linux|bash|sql|postgresql|mongodb"
    r"|разработ|develop|программ|program|coder|coding"
    r"|фрилан|freelanc|remote|удалён|удаленн"
    r"|заказ|проект|биржа|work|job|вакансий|вакансии|jobs"
    r"|tester|тестировщик|qa\b|автоматизац"
    r"|дизайн|design|ux\b|ui\b|figma"
    r"|копирайт|smm\b|маркетинг|seo\b"
    r"|it\b|ит\b|tech\b|веб|web\b|mobile|android|ios\b",
    re.IGNORECASE
)


def _is_jobboard(title, uname=""):
    """Блокируем только явно нерелевантные каналы."""
    s = (title + " " + (uname or "")).lower()
    # Если есть IT-признак — пропускаем даже если есть blacklist-слово
    if _IT_CHAN.search(s):
        return False
    return bool(_BLACKLIST.search(s))


def _detect_lang(title, text):
    s = (title + " " + text).lower()
    cyr = len(RE_CYR.findall(s))
    lat = len(re.findall(r'[a-z]', s))
    total = max(cyr + lat, 1)

    # ES-слова в title — сильный сигнал
    esp_ch = len(RE_ESP.findall(s))
    esp_w  = len(re.findall(
        r'\b(hola|busco|trabajo|proyecto|programador|desarrollador'
        r'|remoto|freelancer|necesitamos|contrato|presupuesto)\b', s))

    # Если явно испанский — приоритет над кириллицей
    if esp_ch > 3 or esp_w >= 2:
        return "ES"

    # Кириллица > 40% — русский
    if cyr / total > 0.40:
        return "RU"

    # Слабый сигнал ES при малой доле кириллицы
    if esp_ch > 1 or esp_w >= 1:
        return "ES"

    # Кириллица 25-40% + мало латиницы — тоже RU
    if cyr / total > 0.25 and lat < 30:
        return "RU"

    return "EN"


def _passes(lang, text):
    from filters.smart_filter import (
        SUBJECTS_RU, SUBJECTS_EN, SUBJECTS_ES,
        TRIGGERS_RU, TRIGGERS_EN, TRIGGERS_ES,
        FULLTIME_MARKERS, FREELANCE_MARKERS, URGENT_MARKERS,
    )
    subj = {"RU": SUBJECTS_RU + SUBJECTS_EN,
            "EN": SUBJECTS_EN,
            "ES": SUBJECTS_ES + SUBJECTS_EN}.get(lang, SUBJECTS_EN)
    trig = {"RU": TRIGGERS_RU, "EN": TRIGGERS_EN,
            "ES": TRIGGERS_ES}.get(lang, TRIGGERS_EN)

    t = re.sub(r'[^\w\s]', ' ', text.lower())
    cnt = lambda lst: sum(1 for w in lst if re.sub(r'[^\w\s]', ' ', w.lower()) in t)

    ns, nt = cnt(subj), cnt(trig)
    nf, nr = cnt(FULLTIME_MARKERS), cnt(FREELANCE_MARKERS)
    nu     = cnt(URGENT_MARKERS)

    if nf > 3 and nr == 0:
        return False, False, 0

    ok    = (ns >= 2) or (ns >= 1 and nt >= 1) or (nt >= 2)
    score = min(ns * 8 + nt * 10 + nr * 5 + nu * 5, 100)
    return ok, nu > 0, score


# ─── Хелпер: осветлить hex-цвет ─────────────────────────────────────────────
def _lighten(h, amt=0.20):
    h = h.lstrip("#")
    r,g,b_ = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return "#{:02x}{:02x}{:02x}".format(
        min(255,int(r+(255-r)*amt)),
        min(255,int(g+(255-g)*amt)),
        min(255,int(b_+(255-b_)*amt)))


# ─── Canvas-кнопка с border-radius ───────────────────────────────────────────
def _rounded_btn(parent, text, cmd, bg=PANEL, fg=TEXT, fsz=9,
                 radius=8, px=14, py=6, min_w=80, state="normal"):
    """Кнопка с настоящими закруглёнными углами через Canvas."""

    h_px = fsz * 2 + py * 2 + 4
    cv = tk.Canvas(parent, height=h_px, width=min_w,
                   bg=parent.cget("bg"), highlightthickness=0,
                   cursor="hand2" if state == "normal" else "arrow")
    cv._state  = state
    cv._base   = bg
    cv._hover  = _lighten(bg)
    cv._fg     = fg      # ← хранится в атрибуте, меняется снаружи
    cv._text   = text

    def _draw(color):
        cv.delete("all")
        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 2 or h < 2:
            return
        r = radius
        for args, kw in [
            ((0, 0, r*2, r*2),           {"start": 90,  "extent": 90}),
            ((w-r*2, 0, w, r*2),         {"start": 0,   "extent": 90}),
            ((0, h-r*2, r*2, h),         {"start": 180, "extent": 90}),
            ((w-r*2, h-r*2, w, h),       {"start": 270, "extent": 90}),
        ]:
            cv.create_arc(*args, fill=color, outline="", **kw)
        cv.create_rectangle(r, 0, w-r, h, fill=color, outline="")
        cv.create_rectangle(0, r, w, h-r, fill=color, outline="")
        cv.create_text(w//2, h//2, text=cv._text,
                       font=(F, fsz, "bold"), fill=cv._fg, anchor="center")

    cv.bind("<Configure>", lambda e: _draw(cv._base))
    cv.bind("<Enter>",     lambda e: _draw(cv._hover) if cv._state == "normal" else None)
    cv.bind("<Leave>",     lambda e: _draw(cv._base))
    cv.bind("<Button-1>",  lambda e: cmd()            if cv._state == "normal" else None)

    def set_state(s):
        cv._state = s
        cv.config(cursor="hand2" if s == "normal" else "arrow")
        _draw(cv._base)

    cv.set_state  = set_state
    cv.redraw     = lambda: _draw(cv._base)
    cv.after(10, lambda: _draw(cv._base))
    return cv


# ─── Кнопка-хелпер (обычная, для мест где Canvas не нужен) ──────────────────
def _btn(parent, text, cmd, bg=PANEL, fg=TEXT, fsz=9, w=None,
         state=tk.NORMAL, px=10, py=5):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  font=(F, fsz), relief=tk.FLAT, cursor="hand2",
                  activebackground=_lighten(bg), activeforeground=TEXT,
                  padx=px, pady=py, bd=0, state=state,
                  **({"width": w} if w else {}))
    b.bind("<Enter>", lambda e: b.config(bg=_lighten(bg)) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda e: b.config(bg=bg)           if str(b["state"]) != "disabled" else None)
    return b


def _vsep(parent):
    return tk.Frame(parent, bg=BORDER, width=1)


def _hsep(parent):
    return tk.Frame(parent, bg=BORDER, height=1)


# ─── Основной класс ──────────────────────────────────────────────────────────
class ChannelFinderTab:
    def __init__(self, parent, notebook=None, _embed=False):
        if _embed:
            self.frame = tk.Frame(parent, bg=BG)
            self.frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.frame = tk.Frame(notebook, bg=BG)
            notebook.add(self.frame, text="🔭 Найти каналы")

        self._channels  = {l: {} for l in LANGS}
        self._joined    = set()
        self._listboxes = {}
        self._clabels   = {}
        self._running   = False
        self._paused    = False
        self._stopped   = False
        self._pb_anim   = False
        self._dot_phase = 0
        self._lang_on   = {l: tk.BooleanVar(value=False) for l in LANGS}
        self._tbtns     = {}

        self._build()

    # ─── Построение ──────────────────────────────────────────────────────────

    def _build(self):
        self._build_toolbar()
        self._build_summary()
        self._build_content()

    def _build_toolbar(self):
        bar = tk.Frame(self.frame, bg=BG2)
        bar.pack(fill=tk.X)

        # Заголовок
        top = tk.Frame(bar, bg=BG2, padx=18, pady=10)
        top.pack(fill=tk.X)
        tk.Label(top, text="⊚  Поиск Telegram-каналов",
                 font=(F, 13, "bold"), bg=BG2, fg=TEXT).pack(side=tk.LEFT)
        # _stat создаётся позже в _build_toolbar после _stat_bar
        self._stat_topright = tk.Label(top, text="",
                              font=(F, 9), bg=BG2, fg=TEXT2)
        self._stat_topright.pack(side=tk.RIGHT)

        _hsep(bar).pack(fill=tk.X)

        # Строка элементов
        row = tk.Frame(bar, bg=BG2, padx=18, pady=9)
        row.pack(fill=tk.X)

        # — Тогглы языков (Canvas с border-radius)
        tk.Label(row, text="Язык:", font=(F, 8),
                 bg=BG2, fg=TEXT2).pack(side=tk.LEFT, padx=(0, 8))
        for lang, cfg in LANGS.items():
            b = _rounded_btn(row,
                             text=f"{cfg['flag']}  {lang}",
                             cmd=lambda l=lang: self._toggle(l),
                             bg=cfg["toff"], fg=TEXT2,
                             fsz=9, radius=8, px=12, py=5, min_w=70)
            b.pack(side=tk.LEFT, padx=2, pady=3)
            self._tbtns[lang] = b

        _vsep(row).pack(side=tk.LEFT, fill=tk.Y, padx=14, pady=3)

        # — Глубина
        tk.Label(row, text="Глубина:", font=(F, 8),
                 bg=BG2, fg=TEXT2).pack(side=tk.LEFT, padx=(0, 8))
        self._depth = tk.IntVar(value=2)
        self._depth_btns = {}
        for val, lbl in [(1, "Быстро"), (2, "Стандарт"), (3, "Глубоко")]:
            b = _rounded_btn(row, text=lbl,
                             cmd=lambda v=val: self._set_depth(v),
                             bg=BLUE2 if val == 2 else PANEL,
                             fg=TEXT if val == 2 else TEXT2,
                             fsz=9, radius=8, px=9, py=5, min_w=64)
            b.pack(side=tk.LEFT, padx=2, pady=3)
            self._depth_btns[val] = b

        _vsep(row).pack(side=tk.LEFT, fill=tk.Y, padx=14, pady=3)

        # — Мин. подписчиков
        tk.Label(row, text="Мин. подп.:", font=(F, 8),
                 bg=BG2, fg=TEXT2).pack(side=tk.LEFT, padx=(0, 6))
        self._min_m = tk.IntVar(value=MIN_MEMBERS)
        tk.Spinbox(row, from_=0, to=100000, increment=100,
                   textvariable=self._min_m, width=7, font=(F, 9),
                   bg=PANEL2, fg=TEXT, buttonbackground=PANEL,
                   insertbackground=BLUE, relief=tk.FLAT, bd=0,
                   ).pack(side=tk.LEFT)

        _vsep(row).pack(side=tk.LEFT, fill=tk.Y, padx=14, pady=3)

        # — Кнопки управления (закруглённые)
        self._run_btn = _rounded_btn(row, "▶  Найти", self._run,
                                     bg=BLUE, fg=TEXT, fsz=10,
                                     radius=9, px=14, py=5, min_w=90)
        self._run_btn.pack(side=tk.LEFT, padx=(0, 5), pady=3)

        self._pause_btn = _rounded_btn(row, "⏸", self._pause,
                                       bg=PANEL, fg=TEXT, fsz=10,
                                       radius=9, px=10, py=5, min_w=36,
                                       state="disabled")
        self._pause_btn.pack(side=tk.LEFT, padx=2, pady=3)

        self._stop_btn = _rounded_btn(row, "⏹", self._stop,
                                      bg="#4A1818", fg=TEXT, fsz=10,
                                      radius=9, px=10, py=5, min_w=36,
                                      state="disabled")
        self._stop_btn.pack(side=tk.LEFT, padx=2, pady=3)

        # — Правая сторона
        _rounded_btn(row, "📄 Экспорт", self._export,
                     bg=PANEL, fg=TEXT2, fsz=8,
                     radius=7, px=8, py=4, min_w=70).pack(side=tk.RIGHT, padx=2, pady=3)
        _rounded_btn(row, "📂 Загрузить", self._load,
                     bg=PANEL, fg=TEXT2, fsz=8,
                     radius=7, px=8, py=4, min_w=80).pack(side=tk.RIGHT, padx=2, pady=3)

        # ─── Статус + прогресс-бар — единый блок ────────────────────────────
        prog_wrap = tk.Frame(self.frame, bg=BG2)
        prog_wrap.pack(fill=tk.X)

        # Статусная строка
        self._stat_bar = tk.Frame(prog_wrap, bg=BG2)
        self._stat_bar.pack(fill=tk.X)

        # Иконка-dot (анимированный индикатор)
        self._stat_dot = tk.Label(self._stat_bar, text="●",
                                  font=(F, 9), bg=BG2, fg=MUTED)
        self._stat_dot.pack(side=tk.LEFT, padx=(8, 2), pady=5)

        self._stat = tk.Label(self._stat_bar,
                              text="Готов к поиску",
                              font=(F, 9), bg=BG2, fg=TEXT2, anchor="w")
        self._stat.pack(side=tk.LEFT, fill=tk.X, pady=5)

        # Прогресс-бар — толще и заметнее
        s = ttk.Style()
        s.configure("Chan.Horizontal.TProgressbar",
                    troughcolor=BORDER, background=BLUE,
                    thickness=5, relief=tk.FLAT, borderwidth=0)
        self._pb = ttk.Progressbar(
            prog_wrap, mode="indeterminate",
            style="Chan.Horizontal.TProgressbar")
        self._pb.pack(fill=tk.X, pady=(0, 1))
        self._pb_anim = False

    def _build_summary(self):
        """Итоговая полоса — всегда видна, обновляется динамически."""
        self._sum_frame = tk.Frame(self.frame, bg=PANEL, height=40)
        self._sum_frame.pack(fill=tk.X, padx=0)
        self._sum_frame.pack_propagate(False)
        self._redraw_summary()

    def _redraw_summary(self):
        for w in self._sum_frame.winfo_children():
            w.destroy()

        total   = sum(len(self._channels[l]) for l in LANGS)
        joined  = len(self._joined)

        # Большой счётчик
        tk.Label(self._sum_frame,
                 text=f"  Найдено:  {total}",
                 font=(F, 12, "bold"), bg=PANEL,
                 fg=GOLD if total > 0 else TEXT2).pack(side=tk.LEFT, padx=6)

        _vsep(self._sum_frame).pack(side=tk.LEFT, fill=tk.Y, pady=6, padx=10)

        # По языкам
        for lang, cfg in LANGS.items():
            n = len(self._channels[lang])
            on = self._lang_on[lang].get()
            fg = cfg["hi"] if n > 0 else (TEXT2 if on else MUTED)
            fw = "bold" if n > 0 else "normal"
            tk.Label(self._sum_frame,
                     text=f"{cfg['flag']}  {n}",
                     font=(F, 11, fw), bg=PANEL, fg=fg,
                     padx=12).pack(side=tk.LEFT)

        # Вступивших
        if joined > 0:
            _vsep(self._sum_frame).pack(side=tk.LEFT, fill=tk.Y, pady=8, padx=8)
            tk.Label(self._sum_frame,
                     text=f"✅  Вступил:  {joined}",
                     font=(F, 10, "bold"), bg=PANEL, fg=GREEN,
                     padx=6).pack(side=tk.LEFT)

    def _build_content(self):
        self._content = tk.Frame(self.frame, bg=BG)
        self._content.pack(fill=tk.BOTH, expand=True)

        # Пустой экран
        self._empty = tk.Frame(self._content, bg=BG)
        self._empty.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(self._empty, text="🔭", font=(F, 48), bg=BG, fg=MUTED).pack()
        tk.Label(self._empty, text="Здесь появятся найденные каналы",
                 font=(F, 13), bg=BG, fg=TEXT2).pack(pady=(6, 2))
        tk.Label(self._empty,
                 text="Включите один или несколько языков  →  нажмите  ▶ Найти",
                 font=(F, 9), bg=BG, fg=MUTED).pack()

        # Контейнер для колонок
        self._cols = tk.Frame(self._content, bg=BG)

        # Подсказка
        tk.Label(self.frame,
                 text="Двойной клик — вступить   ·   Ctrl+Двойной клик — открыть в браузере",
                 font=(F, 8), bg=BG, fg=MUTED).pack(pady=4)

    # ─── Тогглы и глубина ────────────────────────────────────────────────────

    def _toggle(self, lang):
        v = self._lang_on[lang]
        v.set(not v.get())
        cfg = LANGS[lang]
        b = self._tbtns[lang]
        if v.get():
            b._base  = cfg["ton"]
            b._hover = _lighten(cfg["ton"], 0.15)
            b._fg    = TEXT
        else:
            b._base  = cfg["toff"]
            b._hover = _lighten(cfg["toff"], 0.20)
            b._fg    = TEXT2
        b.redraw()

    def _set_depth(self, val):
        self._depth.set(val)
        for v, b in self._depth_btns.items():
            b._base  = BLUE2 if v == val else PANEL
            b._fg    = TEXT  if v == val else TEXT2
            b._hover = _lighten(b._base)
            b.redraw()

    def _selected(self):
        return [l for l, v in self._lang_on.items() if v.get()]

    # ─── Колонки ─────────────────────────────────────────────────────────────

    def _rebuild_cols(self, langs):
        """Перестроить колонки — только для выбранных языков."""
        # Убрать пустой экран
        self._empty.place_forget()
        # Очистить старые
        for w in self._cols.winfo_children():
            w.destroy()
        self._listboxes = {}
        self._clabels   = {}
        # Показать контейнер
        self._cols.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        n = len(langs)
        for i, lang in enumerate(langs):
            cfg = LANGS[lang]
            pad_r = 0 if i == n - 1 else 1   # 1px граница между колонками

            col = tk.Frame(self._cols, bg=cfg["bg"])
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                     padx=(0, pad_r))

            # Заголовок колонки
            hdr = tk.Frame(col, bg=cfg["hdr"], pady=9, padx=14)
            hdr.pack(fill=tk.X)
            tk.Label(hdr, text=f"{cfg['flag']}  {cfg['label']}",
                     font=(F, 10, "bold"), bg=cfg["hdr"],
                     fg=TEXT).pack(side=tk.LEFT)
            cnt_lbl = tk.Label(hdr, text="0",
                               font=(F, 11, "bold"),
                               bg=cfg["hdr"], fg=cfg["hi"])
            cnt_lbl.pack(side=tk.RIGHT)
            self._clabels[lang] = cnt_lbl

            # Листбокс
            lb = tk.Listbox(col, bg=cfg["bg"], fg=cfg["fg"],
                            selectbackground=cfg["hi"],
                            selectforeground=TEXT,
                            font=(FM, 9), relief=tk.FLAT, bd=0,
                            highlightthickness=0, activestyle="none",
                            cursor="hand2")
            lb.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

            sb = ttk.Scrollbar(col, orient=tk.VERTICAL, command=lb.yview)
            sb.pack(fill=tk.Y, side=tk.RIGHT)
            lb.config(yscrollcommand=sb.set)

            lb.bind("<Double-Button-1>",
                    lambda e, l=lang: self._join(e, l))
            lb.bind("<Control-Double-Button-1>",
                    lambda e, l=lang: self._browser(e, l))
            self._listboxes[lang] = lb

    def _show_empty(self):
        self._cols.pack_forget()
        self._empty.place(relx=0.5, rely=0.5, anchor="center")

    # ─── Поиск ───────────────────────────────────────────────────────────────

    def _run(self):
        langs = self._selected()
        if not langs:
            messagebox.showinfo("Выберите язык",
                                "Включите хотя бы один язык перед запуском.")
            return

        # Принудительно сбрасываем состояние (на случай зависшего прошлого поиска)
        self._running = False
        self._stopped = False
        self._paused  = False
        self._pb_anim = False

        # Сначала перестраиваем UI
        self._rebuild_cols(langs)

        # Потом включаем контролы (Canvas set_state)
        try:
            self._set_controls(True)
        except Exception as e:
            print(f"[DEBUG] _set_controls error: {e}")

        # Запускаем прогресс
        try:
            self._pb.start(10)
            self._pb_anim = True
            self._stat_dot.config(fg=BLUE)
            self._animate_dot()
        except Exception as e:
            print(f"[DEBUG] pb/dot error: {e}")

        self._stat.config(text="⏳ Запускаю поиск...", fg=TEXT)

        def go():
            import traceback, os
            print(f"[SCAN] Поток запущен, langs={langs}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            err = None
            try:
                loop.run_until_complete(self._scan(langs))
                print("[SCAN] _scan завершён без ошибок")
            except Exception as e:
                err = traceback.format_exc()
                print(f"[SCAN] ОШИБКА:\n{err}")
                try:
                    os.makedirs("data", exist_ok=True)
                    with open("data/scan_error.log", "w", encoding="utf-8") as f:
                        f.write(err)
                    print("[SCAN] Лог записан: data/scan_error.log")
                except Exception as e2:
                    print(f"[SCAN] Не смог записать лог: {e2}")
            finally:
                loop.close()

            if err:
                last = err.strip().split("\n")[-1][:150]
                def _on_err(msg=last):
                    self._stat.config(text=f"❌ {msg}", fg=RED)
                    self._pb.stop()
                    self._pb_anim = False
                    self._running = False   # принудительный сброс
                    try:
                        self._set_controls(False)
                    except Exception:
                        pass
                self.frame.after(0, _on_err)
            else:
                self.frame.after(0, self._done)

        t = threading.Thread(target=go, daemon=True)
        t.start()
        print(f"[SCAN] Тред запущен: {t.name}")

    async def _scan(self, langs):
        from pyrogram import Client
        from pyrogram.enums import ChatType

        self.frame.after(0, lambda: self._stat.config(
            text="Подключаюсь к Telegram...", fg=TEXT))

        async with Client("freelance_session",
                          api_id=API_ID, api_hash=API_HASH,
                          workdir="data") as app:

            # Проверяем кто залогинен
            try:
                me = await app.get_me()
                self.frame.after(0, lambda n=me.first_name: self._stat.config(
                    text=f"Сессия: @{me.username or me.first_name} — загружаю диалоги..."))
            except Exception as e:
                self.frame.after(0, lambda err=str(e): self._stat.config(
                    text=f"⚠ Сессия: {err[:60]}", fg=GOLD))

            chats = []
            async for d in app.get_dialogs():
                if self._stopped:
                    break
                c = d.chat
                if c.type in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                    chats.append(c)

            total = len(chats)
            if total == 0:
                self.frame.after(0, lambda: self._stat.config(
                    text="⚠ Диалогов 0 — возможно сессия не авторизована или нет каналов",
                    fg=GOLD))
                return
            self.frame.after(0, lambda t=total: self._stat.config(
                text=f"Загружено {t} каналов/групп — анализирую...", fg=TEXT))

            depth     = self._depth.get()
            msg_limit = {1: 0, 2: 10, 3: 30}[depth]
            min_m     = self._min_m.get()

            sm = sj = sl = sf = found = 0

            for i, chat in enumerate(chats):
                if self._stopped:
                    break
                while self._paused and not self._stopped:
                    await asyncio.sleep(0.4)

                uname   = getattr(chat, "username", None) or ""
                title   = getattr(chat, "title", "") or ""
                members = getattr(chat, "members_count", 0) or 0

                self.frame.after(0, lambda i=i, t=title, f=found,
                                        _sm=sm, _sj=sj, _sl=sl, _sf=sf:
                    self._stat.config(
                        text=f"[{i+1}/{total}]  {t[:28]}  "
                             f"│ ✅{f}  подп.−{_sm}  лишние−{_sj}  "
                             f"язык−{_sl}  фильтр−{_sf}"))

                if members < min_m:
                    sm += 1; continue

                # Blacklist — только явно нерелевантные (курсы, школы)
                if _is_jobboard(title, uname):
                    sj += 1; continue

                # ── Шаг 1: быстрая проверка по названию ──────────────────
                # IT/фриланс канал по названию — берём сразу без чтения сообщений
                title_ok = bool(_IT_CHAN.search(title) or _IT_CHAN.search(uname))

                # ── Шаг 2: читаем текст только если нужен (depth > 1 или название неясное) ──
                desc = ""
                if depth >= 1:
                    try:
                        fc = await app.get_chat(uname or chat.id)
                        desc = getattr(fc, "description", "") or ""
                    except Exception:
                        pass

                extra_text = ""
                if depth >= 2 and msg_limit > 0:
                    try:
                        tgt = uname or chat.id
                        async for msg in app.get_chat_history(tgt, limit=msg_limit):
                            if msg.text:
                                extra_text += " " + msg.text
                    except Exception:
                        pass

                full_text = title + " " + uname + " " + desc + extra_text

                # ── Шаг 3: IT-признак в полном тексте ───────────────────
                text_ok = bool(_IT_CHAN.search(full_text[:500]))

                if not title_ok and not text_ok:
                    sf += 1; continue

                # ── Шаг 4: определяем язык ───────────────────────────────
                lang = _detect_lang(title, full_text)
                if lang not in langs:
                    sl += 1; continue

                # ── Шаг 5: urgent-сигналы (для иконки 🔥) ────────────────
                urgent = bool(re.search(
                    r"срочно|urgently|urgent|asap|сейчас|немедленно|today",
                    full_text[:300], re.IGNORECASE))
                score = 50 + (20 if urgent else 0) + (10 if title_ok else 0)

                found += 1
                key = (uname or str(chat.id)).lower()
                if key in self._channels.get(lang, {}):
                    continue

                entry = dict(username=uname, title=title, members=members,
                             lang=lang, link=f"https://t.me/{uname}" if uname else "",
                             joined=False, is_urgent=urgent, score=score)
                self._channels[lang][key] = entry
                self.frame.after(0, lambda k=key, m=members, l=lang,
                                        t=title, u=urgent:
                    self._add(l, k, m, t, u))

                await asyncio.sleep(0.05)

    def _add(self, lang, key, members, title, urgent=False):
        lb = self._listboxes.get(lang)
        if not lb:
            return
        m_s  = f"{members//1000}K" if members >= 1000 else str(members)
        icon = "🔥" if urgent else "  "
        lb.insert(tk.END, f"{icon} @{key}  ({m_s})  {title[:30]}")
        n = len(self._channels[lang])
        if lang in self._clabels:
            self._clabels[lang].config(text=str(n))
        self._redraw_summary()

    def _refill(self, lang):
        lb = self._listboxes.get(lang)
        if not lb:
            return
        cfg = LANGS[lang]
        lb.delete(0, tk.END)
        for key, info in self._channels[lang].items():
            m = info.get("members", 0)
            m_s  = f"{m//1000}K" if m >= 1000 else str(m)
            icon = "🔥" if info.get("is_urgent") else "  "
            lb.insert(tk.END, f"{icon} @{key}  ({m_s})  {info.get('title','')[:30]}")
            idx = lb.size() - 1
            if key in self._joined:
                lb.itemconfig(idx, fg=GREEN, bg=GREEN2)
            else:
                lb.itemconfig(idx, fg=cfg["fg"])
        n = len(self._channels[lang])
        if lang in self._clabels:
            self._clabels[lang].config(text=str(n))

    def _animate_dot(self):
        """Пульсирующий dot пока идёт поиск."""
        if not self._pb_anim:
            return
        colors = [BLUE, "#a78bfa", "#6c63ff", BORDER, BLUE]
        cur = getattr(self, "_dot_phase", 0)
        self._stat_dot.config(fg=colors[cur % len(colors)])
        self._dot_phase = (cur + 1) % len(colors)
        self.frame.after(400, self._animate_dot)

    def _done(self):
        self._pb.stop()
        self._pb_anim = False
        self._stat_dot.config(fg="#4FAE4E")  # зелёный — готово
        self._set_controls(False)
        parts = [f"{LANGS[l]['flag']} {l}: {len(self._channels[l])}"
                 for l in LANGS if self._channels[l]]
        self._stat.config(fg=TEXT,
            text="✅ Готово  —  " + ("  ·  ".join(parts) or "ничего не найдено"))
        self._redraw_summary()
        self._save()

    # ─── Управление ──────────────────────────────────────────────────────────

    def _pause(self):
        self._paused = not self._paused
        # Обновляем текст Canvas-кнопки через перерисовку
        import types
        new_text = "▶" if self._paused else "⏸"
        # Патчим функцию draw чтобы изменить текст
        old_base = self._pause_btn._base
        cv = self._pause_btn
        cv.delete("all")
        w = cv.winfo_width(); h = cv.winfo_height()
        r = 9
        for c, args, kw in [
            ("arc", (0,0,r*2,r*2), {"start":90,"extent":90,"fill":old_base,"outline":""}),
            ("arc", (w-r*2,0,w,r*2), {"start":0,"extent":90,"fill":old_base,"outline":""}),
            ("arc", (0,h-r*2,r*2,h), {"start":180,"extent":90,"fill":old_base,"outline":""}),
            ("arc", (w-r*2,h-r*2,w,h), {"start":270,"extent":90,"fill":old_base,"outline":""}),
            ("rectangle", (r,0,w-r,h), {"fill":old_base,"outline":""}),
            ("rectangle", (0,r,w,h-r), {"fill":old_base,"outline":""}),
        ]:
            getattr(cv, f"create_{c}")(*args, **kw)
        cv.create_text(w//2, h//2, text=new_text,
                       font=(F, 10, "bold"),
                       fill=GOLD if self._paused else TEXT, anchor="center")

        if self._paused:
            self._pb_anim = False
            self._stat_dot.config(fg=GOLD)
            self._stat.config(text="⏸ Пауза", fg=GOLD)
        else:
            self._pb_anim = True
            self._stat_dot.config(fg=BLUE)
            self._stat.config(text="▶ Продолжаю...", fg=TEXT)
            self._animate_dot()

    def _stop(self):
        self._stopped = True
        self._paused  = False
        self._pb_anim = False
        self._pb.stop()
        self._stat_dot.config(fg=RED)
        self._set_controls(False)
        self._stat.config(text="⏹ Остановлено", fg=TEXT2)

    def _set_controls(self, running):
        self._running = running
        print(f"[CTRL] _set_controls(running={running})")
        for btn, state_on, state_off in [
            (self._pause_btn, "normal",   "disabled"),
            (self._stop_btn,  "normal",   "disabled"),
            (self._run_btn,   "disabled", "normal"),
        ]:
            try:
                btn.set_state(state_on if running else state_off)
            except Exception as e:
                print(f"[CTRL] set_state error: {e}")
        if not running:
            self._paused = False

    # ─── Вступление / браузер ────────────────────────────────────────────────

    def _sel(self, event, lang):
        lb = self._listboxes.get(lang)
        if not lb:
            return None, None
        s = lb.curselection()
        if not s:
            return None, None
        m = re.search(r'@(\S+?)\s', lb.get(s[0]))
        return (m.group(1), s[0]) if m else (None, None)

    def _browser(self, event, lang):
        uname, _ = self._sel(event, lang)
        if uname:
            webbrowser.open(f"https://t.me/{uname}")

    def _join(self, event, lang):
        uname, idx = self._sel(event, lang)
        if not uname:
            return
        if not messagebox.askyesno(
                "Вступить", f"Вступить в @{uname}?"):
            return

        lb = self._listboxes.get(lang)
        if lb:
            lb.itemconfig(idx, fg=GOLD)   # жёлтый — ожидание

        self._stat.config(text=f"⏳  Вступаю в @{uname}...")

        def go():
            err = None
            try:
                async def _do():
                    from pyrogram import Client
                    from pyrogram.errors import UserAlreadyParticipant, FloodWait
                    async with Client("freelance_session",
                                     api_id=API_ID, api_hash=API_HASH,
                                     workdir="data") as app:
                        try:
                            await app.join_chat(uname)
                        except UserAlreadyParticipant:
                            raise Exception("already")
                        except FloodWait as e:
                            raise Exception(f"flood:{e.value}")
                lp = asyncio.new_event_loop()
                lp.run_until_complete(_do())
                lp.close()
            except Exception as e:
                err = str(e)

            def after():
                if not err or err == "already":
                    self._joined.add(uname.lower())
                    if lb:
                        txt = lb.get(idx)
                        lb.delete(idx)
                        lb.insert(idx, txt)
                        lb.itemconfig(idx, fg=GREEN, bg=GREEN2)
                    msg = "уже состоишь ✅" if err == "already" else "вступил ✅"
                    self._stat.config(text=f"@{uname}  —  {msg}")
                    self._redraw_summary()
                elif err.startswith("flood:"):
                    secs = err.split(":")[1]
                    if lb:
                        lb.itemconfig(idx, fg=GOLD, bg=PANEL)
                    self._stat.config(text=f"⏳ FloodWait {secs} сек.")
                    messagebox.showwarning("FloodWait",
                        f"Telegram просит подождать {secs} сек.")
                else:
                    if lb:
                        lb.itemconfig(idx, fg="#EF5350", bg=PANEL)
                    self._stat.config(text=f"❌ {err}")
                    messagebox.showerror("Ошибка", f"@{uname}\n\n{err}")

            self.frame.after(0, after)

        threading.Thread(target=go, daemon=True).start()

    # ─── Сохранение / загрузка ───────────────────────────────────────────────

    def _save(self):
        os.makedirs("data", exist_ok=True)
        with open("data/scout_channels.json", "w", encoding="utf-8") as f:
            json.dump(self._channels, f, ensure_ascii=False, indent=2)

    def _load(self):
        try:
            with open("data/scout_channels.json", encoding="utf-8") as f:
                data = json.load(f)
            for l in LANGS:
                self._channels[l] = data.get(l, {})
            langs = [l for l in LANGS if self._channels[l]]
            if not langs:
                messagebox.showinfo("Пусто", "В файле нет каналов."); return
            for l in LANGS:
                has = bool(self._channels[l])
                self._lang_on[l].set(has)
                cfg = LANGS[l]
                self._tbtns[l].config(
                    bg=cfg["ton"] if has else cfg["toff"],
                    fg=TEXT if has else TEXT2,
                    relief=tk.GROOVE if has else tk.FLAT)
            self._rebuild_cols(langs)
            for l in langs:
                self._refill(l)
            total = sum(len(self._channels[l]) for l in LANGS)
            self._stat.config(text=f"📂 Загружено {total} каналов")
            self._redraw_summary()
        except FileNotFoundError:
            messagebox.showinfo("Нет файла",
                "Сначала выполните поиск.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _export(self):
        os.makedirs("data", exist_ok=True)
        path = "data/channels_to_join.txt"
        with open(path, "w", encoding="utf-8") as f:
            for lang, chs in self._channels.items():
                if not chs:
                    continue
                f.write(f"\n── {lang} ────────────────────────\n")
                for key, info in chs.items():
                    f.write(f"  {info.get('link', 't.me/' + key)}"
                            f"  ({info.get('members',0)})  {info.get('title','')}\n")
        messagebox.showinfo("Готово", f"Сохранено: {path}")

"""
window.py — Главное окно Freelance Bot
Дизайн: боковая навигационная панель + контентная область.
Режим «Каналы»  → только вкладка поиска каналов.
Режим «Заявки» → вкладки «Заявки» + «Статусы».
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import webbrowser
import json
import os
from datetime import datetime

try:
    from filters.classifier import get_all_categories, get_templates_for_category
except Exception:
    def get_all_categories(): return []
    def get_templates_for_category(category): return []

# ── Цветовая палитра Nexio — Violet Midnight ──────────────────────────────────
C = {
    "bg":          "#0f0f1a",   # Violet Midnight — основной фон
    "sidebar":     "#0b0b14",   # ещё темнее для сайдбара
    "panel":       "#16162a",   # карточки/панели
    "panel2":      "#1e1e35",   # поля ввода
    "accent":      "#6c63ff",   # фиолетовый — основной акцент
    "accent2":     "#4FAE4E",   # зелёный — позитивные действия
    "blue":        "#5048e5",   # dim-фиолетовый
    "danger":      "#ef4444",   # красный
    "text":        "#e8e8f4",   # основной текст — ярче
    "muted":       "#8080a8",   # серо-фиолетовый — контраст выше
    "matched":     "#b8a8ff",   # светлый фиолетовый — ярче
    "uncertain":   "#F0B429",   # золото
    "border":      "#2a2a45",   # граница
    "hover":       "#22223a",   # hover
    "nav_active":  "#1e1e38",   # активный пункт
    "nav_text":    "#9090b8",   # неактивный текст — читаемее
}

FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_HEAD   = ("Segoe UI", 10, "bold")
FONT_BODY   = ("Segoe UI", 9)
FONT_SMALL  = ("Segoe UI", 8)
FONT_MONO   = ("Consolas", 9)

# ── Радиус скругления кнопок (мягкий стиль) ───────────────────────────────
BTN_RADIUS = 10   # используется через стиль ttk и вручную где возможно

PAYMENT_OPTIONS = [
    ("🟢 Сбербанк", "Сбербанк"), ("🟡 Тинькофф", "Тинькофф"),
    ("🟠 Альфа-Банк", "Альфа-Банк"), ("🔵 ВТБ", "ВТБ"),
    ("🟣 Газпромбанк", "Газпромбанк"), ("🔴 Россельхозбанк", "Россельхозбанк"),
    ("🟤 Почта Банк", "Почта Банк"), ("⚫ Открытие", "Открытие"),
    ("🔵 Райффайзен", "Райффайзен"), ("🟡 МТС Банк", "МТС Банк"),
    ("🟠 Совкомбанк", "Совкомбанк"), ("🔵 Росбанк", "Росбанк"),
    ("🛒 Озон Банк", "Озон Банк"), ("🟡 WB Банк", "WB Банк"),
    ("💎 Крипта (TRC20 USDT)", "Крипта TRC20"),
    ("💵 Наличные", "Наличные"), ("❓ Другое", "Другое"),
]
PAYMENT_LABELS = [p[0] for p in PAYMENT_OPTIONS]
PAYMENT_VALUES = {p[0]: p[1] for p in PAYMENT_OPTIONS}

TASK_STATUSES = [
    "🆕 Новый", "💬 Переговоры", "🔧 В работе",
    "✅ Выполнено", "❌ Отказ заказчика", "🚫 Отклонили", "🔄 На доработке",
]

RESULTS_FILE = "data/daily_results.json"
PAGE_SIZE    = 10


def load_daily_results() -> dict:
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_daily_results(data: dict):
    try:
        os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _card(parent, **kw) -> tk.Frame:
    """Карточка с лёгким рельефом."""
    f = tk.Frame(parent, bg=C["panel"], highlightbackground=C["border"],
                 highlightthickness=1, **kw)
    return f


def _btn(parent, text, cmd, color=None, fg="white", width=None, small=False):
    base_bg = color or C["blue"]
    # Высветление при hover: смешиваем с белым на 15%
    def _lighten(hex_color):
        h = hex_color.lstrip("#")
        r, g, b_ = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r2 = min(255, int(r + (255-r)*0.18))
        g2 = min(255, int(g + (255-g)*0.18))
        b2_ = min(255, int(b_ + (255-b_)*0.18))
        return f"#{r2:02x}{g2:02x}{b2_:02x}"
    hover_bg = _lighten(base_bg)
    kw = dict(text=text, command=cmd, bg=base_bg,
              fg=fg, font=FONT_BODY if not small else FONT_SMALL,
              relief=tk.FLAT, cursor="hand2",
              activebackground=hover_bg, activeforeground=fg,
              padx=12, pady=5, borderwidth=0)
    if width:
        kw["width"] = width
    b = tk.Button(parent, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=hover_bg))
    b.bind("<Leave>", lambda e: b.config(bg=base_bg))
    return b


def _sep(parent, orient="h", color=None):
    c = color or C["border"]
    if orient == "h":
        return tk.Frame(parent, bg=c, height=1)
    return tk.Frame(parent, bg=c, width=1)


def _label(parent, text, size=9, bold=False, color=None, **kw):
    font = ("Segoe UI", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text, font=font,
                    bg=kw.pop("bg", C["bg"]),
                    fg=color or C["text"], **kw)


# ── Диалог результата ─────────────────────────────────────────────────────────

class ResultDialog(tk.Toplevel):
    def __init__(self, parent, item: dict, on_save_callback):
        super().__init__(parent)
        self.item    = item
        self.on_save = on_save_callback
        self.title("Статус заявки")
        self.geometry("540x500")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self._load_existing()

    def _build(self):
        # Шапка
        hdr = tk.Frame(self, bg=C["panel"], pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📋  Обновить статус заявки",
                 font=FONT_TITLE, bg=C["panel"], fg=C["accent"]).pack()
        info = (f"{self.item.get('channel','?')}  ·  {self.item.get('category','—')}")
        tk.Label(hdr, text=info, font=FONT_SMALL, bg=C["panel"],
                 fg=C["muted"]).pack(pady=(2, 0))

        body = tk.Frame(self, bg=C["bg"], padx=20, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        def row(label, widget_fn):
            tk.Label(body, text=label, font=FONT_BODY, bg=C["bg"],
                     fg=C["muted"], anchor="w").pack(fill=tk.X, pady=(6, 1))
            return widget_fn()

        self.status_var = tk.StringVar(value=TASK_STATUSES[0])
        row("Статус задания", lambda: ttk.Combobox(
            body, textvariable=self.status_var, values=TASK_STATUSES,
            state="readonly", font=FONT_BODY))._widget if False else None
        cb = ttk.Combobox(body, textvariable=self.status_var,
                          values=TASK_STATUSES, state="readonly", font=FONT_BODY)
        cb.pack(fill=tk.X)
        tk.Label(body, text="Сумма оплаты (₽)", font=FONT_BODY,
                 bg=C["bg"], fg=C["muted"]).pack(fill=tk.X, pady=(8, 1))
        self.amount_var = tk.StringVar()
        tk.Entry(body, textvariable=self.amount_var, font=FONT_BODY,
                 bg=C["panel2"], fg=C["text"], insertbackground=C["accent"],
                 relief=tk.FLAT, highlightbackground=C["border"],
                 highlightthickness=1).pack(fill=tk.X, ipady=4)
        tk.Label(body, text="Способ оплаты", font=FONT_BODY,
                 bg=C["bg"], fg=C["muted"]).pack(fill=tk.X, pady=(8, 1))
        self.payment_var = tk.StringVar(value=PAYMENT_LABELS[0])
        ttk.Combobox(body, textvariable=self.payment_var,
                     values=PAYMENT_LABELS, state="readonly",
                     font=FONT_BODY).pack(fill=tk.X)
        tk.Label(body, text="Комментарий", font=FONT_BODY,
                 bg=C["bg"], fg=C["muted"]).pack(fill=tk.X, pady=(8, 1))
        self.comment_box = tk.Text(body, height=3, font=FONT_BODY,
                                   bg=C["panel2"], fg=C["text"],
                                   insertbackground=C["accent"],
                                   relief=tk.FLAT, wrap=tk.WORD)
        self.comment_box.pack(fill=tk.X)

        # Кнопки
        _sep(self).pack(fill=tk.X)
        btn_row = tk.Frame(self, bg=C["bg"], pady=10, padx=20)
        btn_row.pack(fill=tk.X)
        _btn(btn_row, "💾  Сохранить", self._save,
             color=C["accent2"], width=16).pack(side=tk.LEFT, padx=(0, 8))
        _btn(btn_row, "✖  Отмена", self.destroy,
             color=C["danger"], width=12).pack(side=tk.LEFT)

    def _load_existing(self):
        key  = self._get_key()
        data = load_daily_results()
        if key in data:
            s    = data[key]
            hist = s.get("history", [])
            src  = hist[-1] if hist else s
            self.status_var.set(src.get("status", TASK_STATUSES[0]))
            self.amount_var.set(src.get("amount", ""))
            self.payment_var.set(src.get("payment_label", PAYMENT_LABELS[0]))
            self.comment_box.delete("1.0", tk.END)
            self.comment_box.insert(tk.END, src.get("comment", ""))

    def _get_key(self):
        if self.item.get("_forced_key"):
            return self.item["_forced_key"]
        return (f"{self.item.get('platform','')}_{self.item.get('channel','')}"
                f"_{self.item.get('msg_id','')}")

    def _save(self):
        key  = self._get_key()
        data = load_daily_results()
        pl   = self.payment_var.get()
        now  = datetime.now().strftime("%d.%m.%Y %H:%M")
        existing    = data.get(key, {})
        orig_date   = existing.get("date", now)
        report_date = existing.get("report_date", now)
        text_preview = (self.item.get("text") or self.item.get("text_preview") or "")[:150]
        history = existing.get("history", [])
        history.append({
            "changed_at":    now,
            "status":        self.status_var.get(),
            "amount":        self.amount_var.get().strip(),
            "payment_label": pl,
            "payment_value": PAYMENT_VALUES.get(pl, pl),
            "comment":       self.comment_box.get("1.0", tk.END).strip(),
        })
        current  = history[-1]
        prev_key = self.item.get("_prev_key", "")
        if prev_key and prev_key != key and prev_key in data:
            data[prev_key]["superseded"]    = True
            data[prev_key]["superseded_by"] = key
        data[key] = {
            "date": orig_date, "report_date": report_date, "changed_at": now,
            "platform": self.item.get("platform", ""),
            "channel":  self.item.get("channel", ""),
            "category": self.item.get("category", ""),
            "match_percent": self.item.get("match_percent", 0),
            "link": self.item.get("link", ""),
            "text_preview": text_preview,
            "status": current["status"], "amount": current["amount"],
            "payment_label": current["payment_label"],
            "payment_value": current["payment_value"],
            "comment": current["comment"], "history": history,
        }
        save_daily_results(data)
        try:
            from export.excel_export import export_results_report
            export_results_report(data)
        except Exception:
            pass
        self.on_save(key, data[key])
        self.destroy()


# ── Главное окно ──────────────────────────────────────────────────────────────

class FreelanceWindow:
    def __init__(self, on_send_callback, on_search_callback=None):
        self.on_send       = on_send_callback
        self.on_search     = on_search_callback
        self.results       = []
        self.page_offset   = 0
        self.current_index = 0
        self.current_link  = ""
        self.inwork_items  = {}
        self._current_mode = None   # "search" | "channels"

        self.root = tk.Tk()
        self.root.title("Nexio  ·  Андрей")
        self.root.geometry("1280x760")
        self.root.minsize(1100, 660)
        self.root.configure(bg=C["bg"])

        # Чёткость шрифтов на HiDPI-экранах Windows
        try:
            self.root.tk.call("tk", "scaling", self.root.winfo_fpixels("1i") / 72)
        except Exception:
            pass

        self._apply_styles()
        self._load_inwork_on_start()
        self._build_ui()

    def _apply_styles(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TNotebook",     background=C["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=C["panel"], foreground=C["nav_text"],
                    padding=[14, 6], font=FONT_BODY)
        s.map("TNotebook.Tab",
              background=[("selected", C["nav_active"])],
              foreground=[("selected", C["accent"])])
        s.configure("TCombobox", fieldbackground=C["panel2"],
                    background=C["panel2"], foreground=C["text"],
                    selectbackground=C["nav_active"])
        s.configure("TScrollbar", background=C["panel"], troughcolor=C["bg"],
                    arrowcolor=C["muted"])

    def _load_inwork_on_start(self):
        data = load_daily_results()
        for key, item in data.items():
            status = item.get("status", "")
            if not any(s in status for s in ("Выполнено", "Отказ", "Отклонили")):
                self.inwork_items[key] = item

    # ── Каркас ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Боковая панель
        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # Разделитель
        _sep(self.root, "v", C["border"]).pack(side=tk.LEFT, fill=tk.Y)

        # Правая часть
        right = tk.Frame(self.root, bg=C["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Верхняя статус-полоса
        self.topbar = tk.Frame(right, bg=C["panel"], height=42)
        self.topbar.pack(fill=tk.X)
        self.topbar.pack_propagate(False)
        self._build_topbar()

        _sep(right).pack(fill=tk.X)

        # Контент
        self.content = tk.Frame(right, bg=C["bg"])
        self.content.pack(fill=tk.BOTH, expand=True)

        # Страницы
        self._pages = {}
        self._build_page_search()
        self._build_page_channels()

    # ── Боковая панель ────────────────────────────────────────────────────────

    def _build_sidebar(self):
        # Логотип Nexio — Орбита
        logo = tk.Frame(self.sidebar, bg=C["sidebar"], pady=16)
        logo.pack(fill=tk.X)

        icon_c = tk.Canvas(logo, width=52, height=52,
                           bg=C["sidebar"], highlightthickness=0)
        icon_c.pack()
        # Фон иконки
        icon_c.create_rectangle(4, 4, 48, 48, fill="#1e1e38",
                                outline="#2a2a45", width=1)
        # Орбита 1 — внешняя
        icon_c.create_oval(10, 10, 42, 42,
                           outline="#6c63ff", width=1, dash=(4, 3))
        # Орбита 2 — средняя
        icon_c.create_oval(16, 16, 36, 36,
                           outline="#a78bfa", width=1)
        # Центр
        icon_c.create_oval(23, 23, 29, 29, fill="#6c63ff", outline="")
        # Спутник на внешней орбите
        icon_c.create_oval(38, 24, 44, 30, fill="#a78bfa", outline="")

        tk.Label(logo, text="Nexio", font=("Segoe UI", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(pady=(6, 0))
        tk.Label(logo, text="by Андрей", font=FONT_SMALL,
                 bg=C["sidebar"], fg=C["muted"]).pack()

        _sep(self.sidebar, color=C["border"]).pack(fill=tk.X, padx=12, pady=6)

        # Навигационные кнопки
        self._nav_btns = {}
        nav_items = [
            ("search",   "⊹", "Поиск заявок"),    # Tabler: magnifier style
            ("channels", "⊚", "Найти каналы"),    # Tabler: scan/orbit style
        ]
        for key, icon, label in nav_items:
            btn = self._nav_item(self.sidebar, icon, label, key)
            self._nav_btns[key] = btn

        _sep(self.sidebar, color=C["border"]).pack(fill=tk.X, padx=12, pady=6)

        # Нижняя часть сайдбара — кнопка поиска
        bottom = tk.Frame(self.sidebar, bg=C["sidebar"])
        bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=12, padx=10)

        self.search_btn = tk.Button(
            bottom, text="⌕  Искать сейчас",
            command=self._manual_search,
            bg=C["accent"], fg="white",
            font=FONT_BODY, relief=tk.FLAT,
            cursor="hand2", pady=8, padx=6)
        self.search_btn.pack(fill=tk.X, pady=(0, 6))

        self.status_label = tk.Label(
            bottom, text="⏳ Ожидание...",
            bg=C["sidebar"], fg=C["muted"],
            font=FONT_SMALL, wraplength=180, justify=tk.LEFT)
        self.status_label.pack(fill=tk.X)

    def _nav_item(self, parent, icon, label, key):
        f = tk.Frame(parent, bg=C["sidebar"], cursor="hand2")
        f.pack(fill=tk.X, padx=8, pady=2)

        icon_lbl = tk.Label(f, text=icon, font=("Segoe UI", 13),
                            bg=C["sidebar"], fg=C["nav_text"], width=3)
        icon_lbl.pack(side=tk.LEFT)
        text_lbl = tk.Label(f, text=label, font=FONT_BODY,
                            bg=C["sidebar"], fg=C["nav_text"], anchor="w")
        text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def click(e=None):
            self._show_page(key)

        for w in (f, icon_lbl, text_lbl):
            w.bind("<Button-1>", click)
            w.bind("<Enter>", lambda e, fr=f, il=icon_lbl, tl=text_lbl: (
                fr.config(bg=C["hover"]), il.config(bg=C["hover"]),
                tl.config(bg=C["hover"])))
            w.bind("<Leave>", lambda e, fr=f, il=icon_lbl, tl=text_lbl: (
                None if self._current_mode == key else (
                    fr.config(bg=C["sidebar"]), il.config(bg=C["sidebar"]),
                    tl.config(bg=C["sidebar"]))))

        f._icon = icon_lbl
        f._text = text_lbl
        return f

    def _set_nav_active(self, key):
        for k, f in self._nav_btns.items():
            active = (k == key)
            bg = C["nav_active"] if active else C["sidebar"]
            fg = C["accent"] if active else C["nav_text"]
            f.config(bg=bg)
            f._icon.config(bg=bg, fg=fg)
            f._text.config(bg=bg, fg=fg)

    # ── Топбар ────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        self.topbar_title = tk.Label(
            self.topbar, text="", font=FONT_TITLE,
            bg=C["panel"], fg=C["text"], padx=16)
        self.topbar_title.pack(side=tk.LEFT, pady=8)

        self.counter_label = tk.Label(
            self.topbar, text="",
            font=FONT_SMALL, bg=C["panel"], fg=C["muted"], padx=16)
        self.counter_label.pack(side=tk.RIGHT, pady=8)

    # ── Страницы ──────────────────────────────────────────────────────────────

    def _show_page(self, key):
        if self._current_mode == key:
            return
        prev_key = self._current_mode
        self._current_mode = key
        self._set_nav_active(key)

        titles = {
            "search":   "⊹  Поиск заявок",
            "channels": "⊚  Найти каналы",
        }
        self.topbar_title.config(text=titles.get(key, ""))

        # ── Fade-переход ──────────────────────────────────────────────────
        prev_page = self._pages.get(prev_key)
        next_page = self._pages.get(key)
        if not next_page:
            return

        if prev_page and prev_key:
            # Fade out старой страницы, затем показываем новую
            self._fade_out_page(prev_page, lambda: self._fade_in_page(next_page))
        else:
            # Первый показ — без анимации
            for w in self.content.winfo_children():
                w.pack_forget()
            next_page.pack(fill=tk.BOTH, expand=True)

    def _fade_out_page(self, page, callback):
        """Fade через Canvas-оверлей поверх content-области."""
        bg = C["bg"]
        # Создаём Canvas-оверлей поверх контент-области
        cw = self.content.winfo_width()  or 800
        ch = self.content.winfo_height() or 600
        overlay = tk.Canvas(self.content, width=cw, height=ch,
                            bg=bg, highlightthickness=0)
        overlay.place(x=0, y=0, relwidth=1, relheight=1)

        # Рисуем затемняющий прямоугольник с нарастающей прозрачностью
        # Tkinter Canvas не имеет rgba, поэтому используем stipple-паттерн
        rect = overlay.create_rectangle(0, 0, cw, ch,
                                        fill=bg, outline="", stipple="gray12")
        steps = 6
        stipples = ["gray12", "gray25", "gray50", "gray75", "", ""]

        def step(i):
            if i >= steps:
                overlay.destroy()
                for w in self.content.winfo_children():
                    if w != overlay:
                        w.pack_forget()
                callback()
                return
            try:
                overlay.itemconfig(rect, stipple=stipples[i])
            except Exception:
                pass
            self.root.after(22, lambda: step(i + 1))

        step(0)

    def _fade_in_page(self, page):
        """Показывает страницу и запускает fade-in через Canvas-оверлей."""
        page.pack(fill=tk.BOTH, expand=True)
        bg = C["bg"]
        cw = self.content.winfo_width()  or 800
        ch = self.content.winfo_height() or 600
        overlay = tk.Canvas(self.content, width=cw, height=ch,
                            bg=bg, highlightthickness=0)
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        rect = overlay.create_rectangle(0, 0, cw, ch, fill=bg, outline="")
        stipples = ["", "gray75", "gray50", "gray25", "gray12", "gray12"]

        def step(i):
            if i >= len(stipples):
                overlay.destroy()
                return
            try:
                sp = stipples[i]
                if sp:
                    overlay.itemconfig(rect, stipple=sp)
                else:
                    overlay.itemconfig(rect, fill=bg, stipple="")
            except Exception:
                pass
            self.root.after(22, lambda: step(i + 1))

        step(0)

    # ── Страница «Поиск заявок» ───────────────────────────────────────────────

    def _build_page_search(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["search"] = page

        nb = ttk.Notebook(page)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        tab_found = tk.Frame(nb, bg=C["bg"])
        nb.add(tab_found, text="📋  Заявки")
        self._build_found_tab(tab_found)

        tab_status = tk.Frame(nb, bg=C["bg"])
        nb.add(tab_status, text="📊  Статусы проектов")
        self._build_status_tab(tab_status)

    def _build_found_tab(self, parent):
        # Левая часть — список заявок
        pane = tk.PanedWindow(parent, orient=tk.HORIZONTAL,
                              bg=C["bg"], sashwidth=4,
                              sashrelief=tk.FLAT, sashpad=2)
        pane.pack(fill=tk.BOTH, expand=True)

        # ── Левая панель: список ─────────────────────────────────────────────
        left = _card(pane)
        pane.add(left, minsize=280, width=310)

        hdr = tk.Frame(left, bg=C["panel"], pady=8, padx=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Найденные заявки", font=FONT_HEAD,
                 bg=C["panel"], fg=C["text"]).pack(side=tk.LEFT)

        lf = tk.Frame(left, bg=C["panel"])
        lf.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.listbox = tk.Listbox(
            lf, bg=C["panel2"], fg=C["text"],
            selectbackground=C["nav_active"], selectforeground=C["accent"],
            font=FONT_MONO, relief=tk.FLAT, bd=0,
            highlightthickness=0, activestyle="none")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Пагинация
        pg = tk.Frame(left, bg=C["panel"], padx=8, pady=6)
        pg.pack(fill=tk.X)
        self.prev_btn = _btn(pg, "◀", self._page_prev, small=True)
        self.prev_btn.pack(side=tk.LEFT)
        self.page_label = tk.Label(pg, text="", font=FONT_SMALL,
                                   bg=C["panel"], fg=C["muted"])
        self.page_label.pack(side=tk.LEFT, expand=True)
        self.next_btn = _btn(pg, "▶", self._page_next,
                             color=C["accent2"], small=True)
        self.next_btn.pack(side=tk.RIGHT)

        _btn(left, "📋  Показать все", self._show_all,
             color=C["panel"]).pack(fill=tk.X, padx=8, pady=(0, 6))

        # ── Правая панель: детали ────────────────────────────────────────────
        right = tk.Frame(pane, bg=C["bg"])
        pane.add(right, minsize=400)

        # Категория
        cat_bar = tk.Frame(right, bg=C["panel"], padx=12, pady=6)
        cat_bar.pack(fill=tk.X)
        self.category_label = tk.Label(
            cat_bar, text="Категория: —", font=FONT_HEAD,
            bg=C["panel"], fg=C["accent"])
        self.category_label.pack(side=tk.LEFT)

        body = tk.Frame(right, bg=C["bg"], padx=12, pady=6)
        body.pack(fill=tk.BOTH, expand=True)

        # Текст заявки
        _label(body, "Текст заявки", bold=True, bg=C["bg"]).pack(anchor="w")
        self.text_box = scrolledtext.ScrolledText(
            body, height=6, font=FONT_MONO,
            bg=C["panel2"], fg=C["text"],
            insertbackground=C["accent"], relief=tk.FLAT,
            wrap=tk.WORD, bd=0)
        self.text_box.pack(fill=tk.X, pady=(2, 8))

        # Ссылка
        self.link_label = tk.Label(
            body, text="", bg=C["bg"], fg="#5AB0FF",
            font=(FONT_BODY[0], FONT_BODY[1], "underline"),
            cursor="hand2", wraplength=500, justify=tk.LEFT)
        self.link_label.pack(anchor="w", pady=(0, 8))
        self.link_label.bind("<Button-1>", self._open_link)

        # Варианты ответа
        _label(body, "Варианты ответа", bold=True, bg=C["bg"]).pack(anchor="w")
        self.variants_listbox = tk.Listbox(
            body, bg=C["panel2"], fg=C["matched"],
            selectbackground=C["nav_active"], selectforeground=C["accent"],
            font=FONT_MONO, height=3, relief=tk.FLAT, bd=0,
            highlightthickness=0, activestyle="none")
        self.variants_listbox.pack(fill=tk.X, pady=(2, 6))
        self.variants_listbox.bind("<<ListboxSelect>>", self._on_variant_select)

        # Ручной выбор категории
        mf = _card(body)
        mf.pack(fill=tk.X, pady=(0, 6))
        tk.Label(mf, text="  Выбрать категорию вручную:", font=FONT_SMALL,
                 bg=C["panel"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(
            mf, textvariable=self.category_var,
            values=get_all_categories(), state="readonly", font=FONT_BODY)
        self.category_dropdown.pack(fill=tk.X, padx=6, pady=(2, 2))
        self.category_dropdown.bind("<<ComboboxSelected>>",
                                    self._on_manual_category_select)
        self.manual_tpl_listbox = tk.Listbox(
            mf, bg=C["panel2"], fg="#87CEEB",
            selectbackground=C["nav_active"],
            font=FONT_MONO, height=2, relief=tk.FLAT,
            bd=0, highlightthickness=0, activestyle="none")
        self.manual_tpl_listbox.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.manual_tpl_listbox.bind("<<ListboxSelect>>",
                                     self._on_manual_template_select)

        # Поле ответа
        _label(body, "Наш ответ  (редактируется)", bold=True,
               bg=C["bg"]).pack(anchor="w")
        self.reply_box = scrolledtext.ScrolledText(
            body, height=4, font=FONT_MONO,
            bg=C["panel2"], fg=C["matched"],
            insertbackground=C["accent"], relief=tk.FLAT,
            wrap=tk.WORD, bd=0)
        self.reply_box.pack(fill=tk.X, pady=(2, 8))

        # Кнопки действий
        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.pack(fill=tk.X)
        actions = [
            ("✅  Отправить",      self._send,               C["accent2"]),
            ("⏭  Пропустить",    self._skip,               "#4A3A10"),
            ("📊  Статус",         self._open_result_dialog,  C["blue"]),
            ("📥  Excel",          self._export_report,       "#2A3A2A"),
        ]
        for text, cmd, bg in actions:
            _btn(btn_row, text, cmd, color=bg).pack(
                side=tk.LEFT, padx=(0, 6))

    # ── Страница статусов (бывшая «В работе») ────────────────────────────────

    def _build_status_tab(self, parent):
        tk.Label(parent, text="История и статусы проектов",
                 font=FONT_HEAD, bg=C["bg"], fg=C["muted"],
                 anchor="w").pack(fill=tk.X, padx=12, pady=(8, 4))

        pane = tk.PanedWindow(parent, orient=tk.HORIZONTAL,
                              bg=C["bg"], sashwidth=4)
        pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        left = _card(pane)
        pane.add(left, minsize=260, width=320)

        lf = tk.Frame(left, bg=C["panel"])
        lf.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.inwork_listbox = tk.Listbox(
            lf, bg=C["panel2"], fg="#90CAF9",
            selectbackground=C["nav_active"],
            font=FONT_MONO, relief=tk.FLAT, bd=0,
            highlightthickness=0, activestyle="none")
        self.inwork_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2 = ttk.Scrollbar(lf, orient=tk.VERTICAL,
                             command=self.inwork_listbox.yview)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self.inwork_listbox.config(yscrollcommand=sb2.set)
        self.inwork_listbox.bind("<<ListboxSelect>>", self._on_inwork_select)

        right = _card(pane)
        pane.add(right, minsize=350)

        rh = tk.Frame(right, bg=C["panel"], padx=12, pady=8)
        rh.pack(fill=tk.X)
        tk.Label(rh, text="Детали проекта", font=FONT_HEAD,
                 bg=C["panel"], fg=C["text"]).pack(side=tk.LEFT)

        self.inwork_detail = tk.Text(
            right, font=FONT_MONO, bg=C["panel2"], fg=C["text"],
            relief=tk.FLAT, wrap=tk.WORD, state=tk.DISABLED,
            padx=10, pady=8, bd=0)
        self.inwork_detail.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        _sep(right).pack(fill=tk.X)
        btn_r = tk.Frame(right, bg=C["panel"], padx=10, pady=8)
        btn_r.pack(fill=tk.X)
        _btn(btn_r, "✏️  Изменить статус",
             self._open_result_from_inwork,
             color=C["blue"]).pack(side=tk.LEFT, padx=(0, 8))
        _btn(btn_r, "🔗  Открыть",
             self._open_inwork_link,
             color="#2A3A2A").pack(side=tk.LEFT)

        self._inwork_link = ""
        self._inwork_item = {}
        self._refresh_inwork_list()

    # ── Страница «Найти каналы» ───────────────────────────────────────────────

    def _build_page_channels(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self._pages["channels"] = page

        from gui.channel_finder_tab import ChannelFinderTab
        self._channel_finder_tab = ChannelFinderTab(page, _embed=True)

    # ── Логика списка заявок ─────────────────────────────────────────────────

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        total = len(self.results)
        end   = min(self.page_offset + PAGE_SIZE, total)
        for item in self.results[self.page_offset:end]:
            sm     = item.get("status_match")
            dot    = "🟢" if sm == "MATCHED" else ("🟡" if sm == "UNCERTAIN" else "🔵")
            ch     = item.get("channel", "")[:22]
            cat    = f"  {item.get('category','')[:14]}" if item.get("category") else ""
            suffix = f"  [{item['_result_status']}]" if item.get("_result_status") else ""
            self.listbox.insert(tk.END, f" {dot} {ch}{cat}{suffix}")

        self.prev_btn.config(state=tk.NORMAL if self.page_offset > 0 else tk.DISABLED)
        remaining = total - end
        self.next_btn.config(
            state=tk.NORMAL if remaining > 0 else tk.DISABLED,
            text="▶" if remaining > 0 else "—")
        self.page_label.config(
            text=f"{self.page_offset+1}–{end} из {total}" if total else "пусто")

    def _page_next(self):
        if self.page_offset + PAGE_SIZE < len(self.results):
            self.page_offset += PAGE_SIZE
            self._refresh_list()

    def _page_prev(self):
        self.page_offset = max(0, self.page_offset - PAGE_SIZE)
        self._refresh_list()

    def _show_all(self):
        self.listbox.delete(0, tk.END)
        for item in self.results:
            sm  = item.get("status_match")
            dot = "🟢" if sm == "MATCHED" else ("🟡" if sm == "UNCERTAIN" else "🔵")
            cat = f"  {item.get('category','')[:14]}" if item.get("category") else ""
            self.listbox.insert(tk.END,
                f" {dot} {item.get('channel','')[:22]}{cat}")
        self.page_offset = 0
        total = len(self.results)
        self.page_label.config(text=f"все {total}")

    def update_results(self, results: list):
        self.results     = results
        self.page_offset = 0
        matched   = sum(1 for r in results if r.get("status_match") == "MATCHED")
        uncertain = sum(1 for r in results if r.get("status_match") == "UNCERTAIN")
        self.counter_label.config(
            text=f"Найдено: {len(results)}  ·  🟢 {matched}  ·  🟡 {uncertain}")
        self._refresh_list()

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = self.page_offset + sel[0]
        if idx >= len(self.results):
            return
        self.current_index = idx
        item = self.results[idx]
        cat  = item.get("category")
        pct  = item.get("match_percent", 0)
        self.category_label.config(
            text=f"Категория: {cat}  ({pct}%)" if cat else "Категория: не определена")
        self.text_box.config(state=tk.NORMAL)
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, item.get("text", ""))
        self.current_link = item.get("link", "")
        self.link_label.config(
            text=f"🔗  {self.current_link}" if self.current_link else "")
        self.variants_listbox.delete(0, tk.END)
        replies = item.get("replies", [])
        for i, r in enumerate(replies, 1):
            self.variants_listbox.insert(
                tk.END, f"  {i}.  {r[:90]}{'…' if len(r)>90 else ''}")
        self.category_var.set("")
        self.manual_tpl_listbox.delete(0, tk.END)
        self.reply_box.delete("1.0", tk.END)
        self.reply_box.insert(tk.END,
            replies[0] if replies else item.get("reply", ""))

    def _on_variant_select(self, event):
        sel = self.variants_listbox.curselection()
        if not sel or not self.results:
            return
        replies = self.results[self.current_index].get("replies", [])
        idx = sel[0]
        if idx < len(replies):
            self.reply_box.delete("1.0", tk.END)
            self.reply_box.insert(tk.END, replies[idx])

    def _on_manual_category_select(self, event):
        cat  = self.category_var.get()
        if not cat:
            return
        tpls = get_templates_for_category(cat)
        self.manual_tpl_listbox.delete(0, tk.END)
        for i, t in enumerate(tpls, 1):
            self.manual_tpl_listbox.insert(
                tk.END, f"  {i}.  {t[:90]}{'…' if len(t)>90 else ''}")
        self._manual_tpls = tpls

    def _on_manual_template_select(self, event):
        sel = self.manual_tpl_listbox.curselection()
        if not sel or not hasattr(self, "_manual_tpls"):
            return
        idx = sel[0]
        if idx < len(self._manual_tpls):
            self.reply_box.delete("1.0", tk.END)
            self.reply_box.insert(tk.END, self._manual_tpls[idx])

    def _open_link(self, event):
        if self.current_link:
            webbrowser.open(self.current_link)

    def _send(self):
        if not self.results:
            return
        item = self.results[self.current_index]
        text = self.reply_box.get("1.0", tk.END).strip()
        link = self.current_link
        if not text:
            messagebox.showwarning("Пустой ответ", "Введи текст ответа.")
            return
        if not link:
            messagebox.showwarning("Нет ссылки", "У этой заявки нет ссылки.")
            return
        self.status_label.config(text="⏳ Отправка...")
        self.root.update_idletasks()

        def _do():
            try:
                from sender import send_reply
                result = send_reply(link, text)
            except Exception as e:
                result = f"❌ {e}"
            self.root.after(0, lambda: self._after_send(item, result))

        threading.Thread(target=_do, daemon=True).start()

    def _after_send(self, item: dict, result: str):
        item["reply"]  = self.reply_box.get("1.0", tk.END).strip()
        item["status"] = "отправлен"
        self.on_send(item)
        list_pos = self.current_index - self.page_offset
        ok = result.startswith("✅")
        if 0 <= list_pos < self.listbox.size():
            self.listbox.itemconfig(list_pos, fg=C["muted"] if ok else "#EF9A9A")
        self.status_label.config(text=result)
        if not ok:
            messagebox.showerror("Ошибка отправки", result)

    def _skip(self):
        if not self.results:
            return
        item = self.results[self.current_index]
        item["status"] = "пропущен"
        list_pos = self.current_index - self.page_offset
        if 0 <= list_pos < self.listbox.size():
            self.listbox.itemconfig(list_pos, fg=C["muted"])
        self.status_label.config(text="⏭ Пропущено")

    def _open_result_dialog(self):
        if not self.results:
            messagebox.showinfo("Нет заявок", "Сначала выберите заявку.")
            return
        ResultDialog(self.root, self.results[self.current_index],
                     self._on_result_saved)

    def _on_result_saved(self, key: str, data: dict):
        status   = data.get("status", "")
        item     = self.results[self.current_index]
        item["_result_status"] = status.lstrip("🆕💬🔧✅❌🚫🔄 ")
        list_pos = self.current_index - self.page_offset
        has_status = status and status != "🆕 Новый"
        if has_status:
            if 0 <= list_pos < self.listbox.size():
                self.listbox.delete(list_pos)
            self.results.pop(self.current_index)
            total     = len(self.results)
            matched   = sum(1 for r in self.results if r.get("status_match") == "MATCHED")
            uncertain = sum(1 for r in self.results if r.get("status_match") == "UNCERTAIN")
            self.counter_label.config(
                text=f"Найдено: {total}  ·  🟢 {matched}  ·  🟡 {uncertain}")
            if self.page_offset >= total and self.page_offset > 0:
                self.page_offset = max(0, self.page_offset - PAGE_SIZE)
            self.inwork_items[key] = data
        self._refresh_inwork_list()
        self.status_label.config(text=f"💾 Сохранено: {status}")

    # ── Статусы проектов ─────────────────────────────────────────────────────

    def _refresh_inwork_list(self):
        if not hasattr(self, "inwork_listbox"):
            return
        self.inwork_listbox.delete(0, tk.END)
        self._inwork_keys_order = []
        fresh_data = load_daily_results()
        for key in list(self.inwork_items.keys()):
            if key in fresh_data:
                self.inwork_items[key] = fresh_data[key]
        from collections import defaultdict
        groups: dict = defaultdict(list)
        for key, item in self.inwork_items.items():
            date_raw  = item.get("report_date") or item.get("date", "")
            date_only = date_raw[:10] if date_raw else "Без даты"
            groups[date_only].append((key, item))
        for date_key in sorted(groups.keys(), reverse=True):
            self.inwork_listbox.insert(
                tk.END, f" ── {date_key} ─────────────────")
            self.inwork_listbox.itemconfig(
                tk.END, fg=C["accent"],
                selectbackground=C["bg"],
                selectforeground=C["accent"])
            self._inwork_keys_order.append(None)
            for key, item in groups[date_key]:
                history = item.get("history", [])
                channel = item.get("channel", "?")[:20]
                cat     = item.get("category", "?")[:16]
                if not history:
                    status_raw = item.get("status", "—")
                    status     = status_raw.lstrip("🆕💬🔧✅❌🚫🔄 ")
                    changed    = item.get("changed_at", "")[-5:]
                    self.inwork_listbox.insert(
                        tk.END, f"  [{status}] {channel} · {changed}")
                    self.inwork_listbox.itemconfig(
                        tk.END, fg=self._status_color(status_raw))
                    self._inwork_keys_order.append((key, -1))
                else:
                    for i, record in enumerate(history):
                        is_last    = (i == len(history) - 1)
                        status_raw = record.get("status", "—")
                        status     = status_raw.lstrip("🆕💬🔧✅❌🚫🔄 ")
                        changed    = record.get("changed_at", "")[-5:]
                        extra      = ""
                        if record.get("amount"):
                            extra += f" · {record['amount']}₽"
                        if is_last:
                            label = f"  ▶ [{status}]{extra} · {channel}"
                            color = self._status_color(status_raw)
                        else:
                            label = f"    [{status}]{extra} · {channel}"
                            color = "#333A50"
                        self.inwork_listbox.insert(tk.END, f" {label}")
                        self.inwork_listbox.itemconfig(tk.END, fg=color)
                        self._inwork_keys_order.append((key, i))

    def _status_color(self, status_raw: str) -> str:
        if "В работе"   in status_raw: return "#90CAF9"
        if "Переговоры" in status_raw: return "#FFF176"
        if "Выполнено"  in status_raw: return "#4CAF50"
        if "Доработк"   in status_raw: return "#FFCC80"
        if any(s in status_raw for s in ("Отказ", "Отклон")): return "#EF9A9A"
        return "#6A7490"

    def _on_inwork_select(self, event):
        sel = self.inwork_listbox.curselection()
        if not sel or not hasattr(self, "_inwork_keys_order"):
            return
        idx   = sel[0]
        if idx >= len(self._inwork_keys_order):
            return
        entry = self._inwork_keys_order[idx]
        if entry is None:
            return
        key, hist_idx = entry
        fresh_data    = load_daily_results()
        item          = fresh_data.get(key, self.inwork_items.get(key, {}))
        if not item:
            return
        item["_key"]          = key
        self.inwork_items[key] = item
        self._inwork_item      = item
        self._inwork_link      = item.get("link", "")
        self._update_inwork_detail(item, hist_idx)

    def _update_inwork_detail(self, data: dict, hist_idx: int = -1):
        if not hasattr(self, "inwork_detail"):
            return
        history = data.get("history", [])
        if history and 0 <= hist_idx < len(history):
            record = history[hist_idx]
        elif history:
            record = history[-1]
        else:
            record = data
        rd = data.get("report_date") or data.get("date", "")
        rd_short = rd[:10] if rd else "?"
        history_lines = ""
        if history:
            history_lines = "\n─── История изменений ─────────────────\n"
            for i, h in enumerate(history):
                marker = "▶ " if i == len(history) - 1 else "  "
                line   = f"{marker}{h.get('changed_at','')}  →  {h.get('status','—')}"
                if h.get("amount"):  line += f"  ·  {h['amount']}₽"
                if h.get("comment"): line += f"  ·  {h['comment'][:30]}"
                history_lines += line + "\n"
        detail_text = (
            f"Канал:     {data.get('channel','—')}  ·  {data.get('category','—')}\n"
            f"Дата:      {data.get('date','—')}\n"
            f"Сумма:     {record.get('amount','') or '—'} ₽  ·  {record.get('payment_value','—')}\n"
            f"Статус:    {record.get('status','—')}\n"
            f"Коммент.:  {record.get('comment','') or '—'}\n"
            f"Превью:    {data.get('text_preview','—')[:120]}"
            f"{history_lines}"
        )
        self.inwork_detail.config(state=tk.NORMAL)
        self.inwork_detail.delete("1.0", tk.END)
        self.inwork_detail.insert(tk.END, detail_text)
        self.inwork_detail.config(state=tk.DISABLED)

    def _open_result_from_inwork(self):
        if not self._inwork_item:
            return
        key        = self._inwork_item.get("_key", "")
        fresh_data = load_daily_results()
        item       = fresh_data.get(key, self._inwork_item)
        item["_forced_key"] = key
        item["_prev_key"]   = key
        ResultDialog(self.root, item, self._on_result_saved_from_inwork)

    def _on_result_saved_from_inwork(self, key: str, data: dict):
        status = data.get("status", "")
        self.inwork_items[key]    = data
        self._inwork_item         = data
        self._inwork_item["_key"] = key
        self._refresh_inwork_list()
        self._try_export_excel()
        self._update_inwork_detail(data)
        self.status_label.config(text=f"💾 Статус: {status}")

    def _open_inwork_link(self):
        if self._inwork_link:
            webbrowser.open(self._inwork_link)

    def _try_export_excel(self):
        try:
            from export.excel_export import export_results_report
            export_results_report(load_daily_results())
        except PermissionError:
            messagebox.showwarning("Файл открыт", "Закройте Excel и повторите.")
        except Exception:
            pass

    def _export_report(self):
        data = load_daily_results()
        if not data:
            messagebox.showinfo("Нет данных", "Нет сохранённых результатов.")
            return
        try:
            from export.excel_export import export_results_report
            path = export_results_report(data)
            messagebox.showinfo("Готово", f"Отчёт сохранён:\n{path}")
            self.status_label.config(text="📊 Excel выгружен")
        except PermissionError:
            messagebox.showwarning("Файл открыт", "Закройте Excel перед выгрузкой.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ── Поиск ────────────────────────────────────────────────────────────────

    def _manual_search(self):
        if not self.on_search:
            return
        self.search_btn.config(state=tk.DISABLED, text="⏳ Поиск...")
        self.status_label.config(text="🔎 Ищу заявки...")

        def _run():
            try:
                self.on_search()
            finally:
                self.root.after(0, lambda: self.search_btn.config(
                    state=tk.NORMAL, text="🔎  Искать сейчас"))

        threading.Thread(target=_run, daemon=True).start()

    def set_status(self, text: str):
        self.status_label.config(text=text)

    def switch_to_channels_tab(self):
        self.root.after(150, lambda: self._show_page("channels"))

    def switch_to_search_tab(self):
        self.root.after(150, lambda: self._show_page("search"))

    def run(self):
        # Показать страницу по умолчанию без анимации
        if self._current_mode is None:
            self._current_mode = "search"
            self._set_nav_active("search")
            page = self._pages.get("search")
            if page:
                page.pack(fill=tk.BOTH, expand=True)
            self.topbar_title.config(text="⊹  Поиск заявок")
        self.root.mainloop()

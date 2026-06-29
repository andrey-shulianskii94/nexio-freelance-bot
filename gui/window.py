import tkinter as tk
from tkinter import ttk, scrolledtext
import threading


class FreelanceWindow:
    def __init__(self, on_send_callback):
        """
        on_send_callback — функция которая вызывается при нажатии кнопки Отправить.
        Принимает item (словарь с данными сообщения).
        """
        self.on_send = on_send_callback
        self.results = []
        self.current_index = 0

        self.root = tk.Tk()
        self.root.title("Freelance Bot — Андрей | Автоматизирую бизнес")
        self.root.geometry("900x600")
        self.root.configure(bg="#0D1B2A")

        self._build_ui()

    def _build_ui(self):
        # Заголовок
        title = tk.Label(
            self.root,
            text="🤖 Freelance Bot",
            font=("Arial", 16, "bold"),
            bg="#0D1B2A",
            fg="#C9A227",
        )
        title.pack(pady=10)

        # Счётчик
        self.counter_label = tk.Label(
            self.root,
            text="Найдено: 0 | Горячих: 0 | Холодных: 0",
            font=("Arial", 10),
            bg="#0D1B2A",
            fg="white",
        )
        self.counter_label.pack()

        # Фрейм с результатами
        main_frame = tk.Frame(self.root, bg="#0D1B2A")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Список результатов (слева)
        list_frame = tk.Frame(main_frame, bg="#0D1B2A")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            list_frame,
            text="Найденные заявки:",
            bg="#0D1B2A",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack()

        self.listbox = tk.Listbox(
            list_frame,
            bg="#132238",
            fg="white",
            selectbackground="#C9A227",
            selectforeground="black",
            font=("Arial", 9),
            width=40,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Детали (справа)
        detail_frame = tk.Frame(main_frame, bg="#0D1B2A")
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        tk.Label(
            detail_frame,
            text="Текст заявки:",
            bg="#0D1B2A",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack()

        self.text_box = scrolledtext.ScrolledText(
            detail_frame,
            height=8,
            bg="#132238",
            fg="white",
            font=("Arial", 9),
            wrap=tk.WORD,
        )
        self.text_box.pack(fill=tk.X, pady=(0, 5))

        tk.Label(
            detail_frame,
            text="Наш ответ (можно редактировать):",
            bg="#0D1B2A",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack()

        self.reply_box = scrolledtext.ScrolledText(
            detail_frame,
            height=8,
            bg="#1a3a1a",
            fg="#90EE90",
            font=("Arial", 9),
            wrap=tk.WORD,
        )
        self.reply_box.pack(fill=tk.X, pady=(0, 5))

        # Кнопки
        btn_frame = tk.Frame(detail_frame, bg="#0D1B2A")
        btn_frame.pack(fill=tk.X)

        self.send_btn = tk.Button(
            btn_frame,
            text="✅ Отправить",
            command=self._send,
            bg="#1B6B1B",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
        )
        self.send_btn.pack(side=tk.LEFT, padx=5)

        self.skip_btn = tk.Button(
            btn_frame,
            text="⏭ Пропустить",
            command=self._skip,
            bg="#6B3A1B",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
        )
        self.skip_btn.pack(side=tk.LEFT, padx=5)

        # Статус
        self.status_label = tk.Label(
            self.root,
            text="⏳ Ожидание запуска парсера...",
            bg="#0D1B2A",
            fg="#C9A227",
            font=("Arial", 9),
        )
        self.status_label.pack(pady=5)

    def update_results(self, results: list):
        """Обновляет список результатов в окне"""
        self.results = results
        self.listbox.delete(0, tk.END)

        hot = sum(1 for r in results if r.get("type") == "HOT")
        cold = sum(1 for r in results if r.get("type") == "COLD")

        self.counter_label.config(
            text=f"Найдено: {len(results)} | 🟢 Горячих: {hot} | 🔵 Холодных: {cold}"
        )

        for i, item in enumerate(results):
            emoji = "🟢" if item.get("type") == "HOT" else "🔵"
            platform = item.get("platform", "")
            channel = item.get("channel", "")[:20]
            self.listbox.insert(tk.END, f"{emoji} [{platform}] {channel}")

    def _on_select(self, event):
        """Показывает детали выбранной заявки"""
        selection = self.listbox.curselection()
        if not selection:
            return

        self.current_index = selection[0]
        item = self.results[self.current_index]

        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, item.get("text", ""))

        self.reply_box.delete("1.0", tk.END)
        self.reply_box.insert(tk.END, item.get("reply", ""))

    def _send(self):
        """Отправляет ответ и помечает как отправленный"""
        if not self.results:
            return

        item = self.results[self.current_index]
        reply_text = self.reply_box.get("1.0", tk.END).strip()
        item["reply"] = reply_text
        item["status"] = "отправлен"

        self.on_send(item)

        self.listbox.itemconfig(self.current_index, fg="#888888")
        self.status_label.config(text=f"✅ Отправлено: {item.get('channel', '')}")

    def _skip(self):
        """Пропускает заявку"""
        if not self.results:
            return
        item = self.results[self.current_index]
        item["status"] = "пропущен"
        self.listbox.itemconfig(self.current_index, fg="#555555")
        self.status_label.config(text=f"⏭ Пропущено")

    def set_status(self, text: str):
        """Обновляет строку статуса"""
        self.status_label.config(text=text)

    def run(self):
        self.root.mainloop()

# 🚀 Nexio — Freelance Intelligence Bot

> Умный помощник для фрилансеров: автоматический поиск заказов в Telegram и ВКонтакте с классификацией и уведомлениями.

![Python](https://img.shields.io/badge/Python-3.12+-3776ab?style=flat&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-API-26a5e4?style=flat&logo=telegram&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat)

---

## ✨ Что умеет Nexio

- 🔍 **Парсит фриланс-каналы** Telegram и группы ВКонтакте в реальном времени
- 🧠 **Классифицирует заявки** на: 🟢 Горячие / 🟡 Похожие / 🔴 Спам
- 📲 **Отправляет уведомления** с готовым текстом отклика прямо в Telegram
- 📊 **Выгружает результаты** в Excel в конце дня
- ⏰ **Автозапуск по расписанию** — каждый час без участия пользователя
- 🖥️ **GUI-интерфейс** — удобное desktop-окно управления (Violet Midnight тема)
- 💾 **Кэш дубликатов** — не показывает одно объявление дважды

---

## 🛠️ Технологический стек

| Категория | Технологии |
|---|---|
| Язык | Python 3.12+ |
| Telegram | Pyrogram, python-telegram-bot |
| Парсинг | requests, BeautifulSoup4 |
| GUI | tkinter (тема Violet Midnight) |
| Планировщик | APScheduler |
| Экспорт | openpyxl (Excel) |

---

## 🚀 Быстрый старт

```bash
git clone https://github.com/andrey-shulianskii94/nexio-freelance-bot.git
cd nexio-freelance-bot
pip install -r requirements.txt
cp .env.example .env
python main.py
```

---

## 📁 Структура проекта
nexio-freelance-bot/
├── main.py                    # Точка входа, планировщик
├── gui/
│   ├── window.py              # Главное окно (Violet Midnight)
│   ├── channel_finder_tab.py  # Вкладка поиска каналов
│   └── splash.py              # Экран загрузки
├── parsers/
│   ├── telegram_parser.py     # Парсинг Telegram
│   ├── channel_finder.py      # Поиск каналов
│   └── vk_parser.py           # Парсинг ВКонтакте
├── filters/
│   ├── classifier.py          # Классификатор HOT/COLD/SPAM
│   └── smart_filter.py        # Умная фильтрация
├── export/
│   └── excel_export.py        # Выгрузка в Excel
└── .env.example               # Шаблон переменных
---

## 👤 Автор

**Андрей Шулянский** — Python-разработчик, автоматизация бизнеса

- 🐙 GitHub: [@andrey-shulianskii94](https://github.com/andrey-shulianskii94)
- 💼 Kwork: [freizenlost](https://kwork.ru/user/freizenlost)
- 📱 Telegram: @avto_biznes_andrey

---

## 📄 Лицензия

MIT License

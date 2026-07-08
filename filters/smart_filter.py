"""
smart_filter.py — трёхуровневая умная фильтрация сообщений и каналов
=====================================================================

Уровень 1 — ТРИГГЕРЫ  : ищу, нужен, hire, looking for, busco...
Уровень 2 — ПРЕДМЕТ   : python, бот, парсер, дизайн, django...
Уровень 3 — ТИП       : FREELANCE / FULLTIME / URGENT / UNKNOWN
             + срочность (срочно, asap, горит...)

analyze(text, lang=None) → dict:
  {
    "relevant":  bool,           # True если уровни 1+2 оба сработали
    "job_type":  str,            # "FREELANCE"|"FULLTIME"|"URGENT"|"UNKNOWN"
    "is_urgent": bool,
    "triggers":  list[str],
    "subjects":  list[str],
    "score":     int,            # 0-100 (уверенность)
    "lang":      str,            # "RU"|"EN"|"ES"|"UNK"
  }
"""

import re

# ═══════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 1 — ТРИГГЕРЫ (сигнал спроса / предложения работы)
# ═══════════════════════════════════════════════════════════════════════════════

TRIGGERS_RU = [
    # Базовые слова спроса (только конкретный запрос, не общие слова)
    "ищу", "нужен", "нужна", "нужно", "нужны",
    "требуется", "требуются",
    "ищем", "набираем", "нанимаем", "нанимаю",
    "приглашаем", "приглашаю",
    # Заказы и задачи (конкретные — не просто "работа")
    "есть заказ", "есть задача", "есть проект",
    "небольшая задача", "небольшой проект",
    "проектная работа", "по проекту",
    # Работа / подработка (только конкретные формы)
    "подработка", "халтура", "подзаработать",
    "разовая работа", "разовый проект",
    # Поиск специалиста
    "ищу специалиста", "ищу разработчика", "ищу программиста",
    "ищу фрилансера", "ищу исполнителя", "ищу дизайнера",
    "ищу верстальщика", "ищу аналитика", "ищу тестировщика",
    "нужен специалист", "нужен разработчик", "нужен программист",
    "нужен дизайнер", "нужен фрилансер", "нужен исполнитель",
    "нужен верстальщик", "нужен аналитик", "нужен тестировщик",
    "нужен сеошник", "нужен копирайтер", "нужен маркетолог",
    # Предложения
    "предлагаю работу", "предлагаем работу", "предлагаю проект",
    "кто возьмётся", "кто возьмется", "кто может", "кто умеет",
    "кто делает", "кто занимается", "кто берёт", "кто берет",
    "помогите сделать", "помогите разработать", "помогите настроить",
    "нужна помощь", "нужна помощь с",
    # В команду
    "в команду", "в поиске", "в поиске специалиста",
    "ищем в команду", "набираем в команду",
    # Бюджет / оплата как сигнал
    "бюджет", "готов заплатить", "готовы заплатить", "оплачу",
    "оплата по договорённости", "оплата договорная",
    "готов обсуждать", "обсуждаем",
    # ТЗ
    "тз готово", "есть тз", "по тз",
]

TRIGGERS_EN = [
    # Core demand words
    "hiring", "hire", "needed", "wanted", "seeking", "looking",
    "require", "requires", "required",
    "opportunity", "vacancy", "opening", "position",
    # Phrases
    "looking for", "we need", "need a", "need an", "need someone",
    "in search of", "searching for",
    "open position", "open role", "open to",
    "job offer", "work offer", "project offer",
    "join our team", "join the team",
    # Who can / help
    "who can", "anyone who", "anyone able",
    "help needed", "help required", "assistance needed",
    # Specialist search
    "freelancer needed", "developer needed", "programmer needed",
    "designer needed", "writer needed", "analyst needed",
    "tester needed", "qa needed", "marketer needed",
    "looking for a developer", "looking for a designer",
    "looking for a freelancer", "looking for someone",
    "need a developer", "need a designer", "need a programmer",
    "need a freelancer", "need an expert",
    # Budget / pay signals
    "budget", "paying", "will pay", "pay per", "rate negotiable",
    "fixed budget", "hourly rate",
    # Taking orders
    "taking on", "accepting orders", "open for work",
    "available for work", "taking projects",
]

TRIGGERS_ES = [
    # Palabras base
    "busco", "necesito", "buscamos", "necesitamos",
    "contratamos", "contrato", "contratando",
    "vacante", "oportunidad", "posición",
    # Frases
    "se busca", "se necesita", "en busca de", "buscando a",
    "oferta de trabajo", "oferta de proyecto",
    "unirse al equipo", "únete al equipo",
    "busco desarrollador", "busco diseñador", "busco programador",
    "busco freelancer", "busco especialista",
    "necesito desarrollador", "necesito diseñador",
    # Quién puede
    "quien puede", "alguien que", "ayuda necesaria",
    "necesito ayuda con", "ayuda con",
    # Presupuesto
    "presupuesto", "pago", "pagamos", "remuneración",
    "hay proyecto", "tengo proyecto", "tengo trabajo",
]

# ═══════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 2 — ПРЕДМЕТ (что именно ищут)
# ═══════════════════════════════════════════════════════════════════════════════

SUBJECTS_RU = [
    # ── Python / общее ──
    "python", "питон", "пайтон",
    "разработчик", "разработка", "разработчики",
    "программист", "программирование", "программисты",
    "девелопер", "кодер", "кодинг",
    # ── Бэкенд фреймворки ──
    "django", "fastapi", "flask", "aiohttp", "tornado",
    "sqlalchemy", "celery", "redis", "rabbitmq",
    # ── Боты Telegram / VK / Discord ──
    "бот", "боты", "телеграм бот", "тг бот", "tg бот",
    "telegram bot", "aiogram", "pyrogram", "telethon",
    "вк бот", "дискорд бот", "discord бот",
    "чат-бот", "чатбот",
    # ── Парсеры / автоматизация ──
    "парсер", "парсинг", "парсить", "парсинг сайтов",
    "скрапер", "скрапинг", "веб-скрейпинг",
    "selenium", "playwright", "puppeteer", "beautifulsoup", "scrapy",
    "скрипт", "скрипты", "автоматизация", "автоматизировать",
    "автоматический", "автоматизированный",
    # ── Веб-разработка ──
    "сайт", "вебсайт", "веб-сайт", "веб сайт",
    "wordpress", "вордпресс", "wp",
    "woocommerce", "шопифай", "shopify",
    "лендинг", "лендинг пейдж", "landing",
    "интернет-магазин", "интернет магазин", "онлайн-магазин",
    "веб", "веб-разработка", "веб разработка",
    "html", "css", "верстка", "вёрстка", "вёрстальщик", "верстальщик",
    "javascript", "js", "typescript", "ts",
    "react", "vue", "angular", "nuxt", "next",
    "node", "nodejs", "node.js",
    # ── Мобильная разработка ──
    "android", "андроид", "kotlin", "java",
    "ios", "swift", "flutter", "react native",
    "мобильное приложение", "мобилка", "мобильный",
    "приложение для андроид", "приложение для ios",
    # ── 1С ──
    "1с", "1с программист", "1с разработчик", "1с:предприятие",
    "1с конфигурация", "1с бухгалтерия",
    # ── Данные / аналитика ──
    "данные", "аналитика", "аналитик", "data",
    "excel", "таблица", "таблицы", "google sheets", "гугл таблицы",
    "отчёт", "отчет", "дашборд", "dashboard",
    "база данных", "бд", "субд", "sql", "postgresql", "mysql", "sqlite",
    "mongodb", "nosql",
    "pandas", "numpy", "matplotlib",
    # ── Дизайн ──
    "дизайн", "дизайнер", "дизайнеры",
    "ux", "ui", "ux/ui", "ui/ux",
    "figma", "фигма", "adobe", "photoshop", "illustrator",
    "макет", "макеты", "прототип", "прототипы",
    "логотип", "логотипы", "брендинг",
    "графика", "графический дизайн",
    "баннер", "баннеры", "иллюстрация",
    # ── Интеграции / API / CRM ──
    "api", "интеграция", "интеграции", "интегрировать",
    "crm", "bitrix", "битрикс", "битрикс24",
    "amocrm", "амо", "amo",
    "1с интеграция", "api интеграция",
    "rest api", "webhook", "вебхук",
    # ── SEO / маркетинг / контент ──
    "seo", "сео", "продвижение", "продвижение сайта",
    "копирайтер", "копирайтинг", "тексты",
    "таргет", "таргетолог", "контекст",
    "маркетолог",
    # ── QA / тестирование ──
    "тестировщик", "qa", "тестирование", "тест",
    # ── DevOps / сервер ──
    "devops", "docker", "докер", "kubernetes",
    "сервер", "vps", "хостинг", "nginx", "linux",
    "настройка сервера", "деплой", "ci/cd",
    # ── AI / ML ──
    "ai", "ml", "machine learning", "нейросеть", "нейросети",
    "gpt", "chatgpt", "openai", "llm",
    # ── Маркетплейсы ──
    "wildberries", "wb", "ozon", "озон", "маркетплейс",
    "seller", "продавец", "карточка товара",
    # ── Общие ──
    "telegram", "телеграм",
    "программа", "приложение", "расширение", "плагин",
]

SUBJECTS_EN = [
    # Python / general dev
    "python", "developer", "programmer", "coder", "engineer", "dev",
    # Backend
    "django", "fastapi", "flask", "aiohttp",
    "backend", "back-end", "back end",
    "api", "rest api", "graphql", "microservice",
    # Bots
    "bot", "telegram bot", "tg bot", "chatbot", "chat bot",
    "aiogram", "pyrogram", "telethon", "discord bot",
    # Parsers / automation
    "parser", "scraper", "scraping", "web scraping", "crawling",
    "selenium", "playwright", "beautifulsoup", "scrapy",
    "script", "automation", "automate",
    # Frontend / web
    "frontend", "front-end", "front end",
    "fullstack", "full stack", "full-stack",
    "website", "web app", "webapp", "web development",
    "html", "css", "javascript", "js", "typescript",
    "react", "vue", "angular", "next", "nuxt", "node",
    "wordpress", "woocommerce", "shopify", "landing page",
    "e-commerce", "ecommerce", "online store",
    # Mobile
    "android", "ios", "flutter", "kotlin", "swift", "react native",
    "mobile app", "mobile application",
    # Data / analytics
    "data", "analytics", "analyst", "excel", "spreadsheet",
    "dashboard", "report", "sql", "database", "postgresql",
    "pandas", "numpy", "data science",
    # Design
    "design", "designer", "ux", "ui", "ux/ui", "ui/ux",
    "figma", "logo", "branding", "mockup", "prototype",
    "graphic design", "banner", "illustration",
    # Integrations / CRM
    "integration", "crm", "webhook", "zapier",
    # Marketing / content
    "seo", "copywriter", "copywriting", "content",
    "smm", "marketing", "marketer",
    # QA
    "qa", "testing", "tester", "quality assurance",
    # DevOps
    "devops", "docker", "kubernetes", "server", "vps", "nginx",
    "deployment", "ci/cd", "linux",
    # AI / ML
    "ai", "ml", "machine learning", "neural network",
    "gpt", "chatgpt", "openai", "llm",
    # General
    "telegram", "app", "application", "plugin", "extension",
]

SUBJECTS_ES = [
    # Python / dev
    "python", "desarrollador", "programador", "developer", "dev",
    # Backend
    "django", "fastapi", "flask", "backend", "api", "rest",
    # Bots
    "bot", "telegram bot", "chatbot", "aiogram",
    # Parsers
    "parser", "scraper", "scraping", "selenium", "script", "automatización",
    # Web
    "frontend", "fullstack", "sitio web", "página web", "web",
    "wordpress", "shopify", "tienda online", "ecommerce",
    "html", "css", "javascript", "react", "vue", "node",
    "landing", "landing page",
    # Mobile
    "android", "ios", "flutter", "aplicación móvil", "app móvil",
    # Data
    "datos", "análisis", "excel", "base de datos", "sql", "dashboard",
    # Design
    "diseño", "diseñador", "ux", "ui", "figma", "logo",
    "branding", "banner", "ilustración",
    # CRM / integrations
    "integración", "crm", "api", "webhook",
    # Marketing
    "seo", "marketing", "copywriter", "contenido", "smm",
    # QA / DevOps
    "qa", "testing", "devops", "docker", "servidor",
    # AI
    "inteligencia artificial", "ia", "ml", "machine learning", "gpt",
    # General
    "telegram", "aplicación", "plugin", "sistema",
]

# ═══════════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 3 — ТИП ЗАНЯТОСТИ
# ═══════════════════════════════════════════════════════════════════════════════

FREELANCE_MARKERS = [
    # RU — тип работы
    "фриланс", "фрилансер", "фрилансерам",
    "удалённо", "удаленно", "удалёнка", "удаленка", "удалённая",
    "разовый", "разовая", "разово", "разовое задание", "разовый проект",
    "проектная работа", "по проекту", "проектно",
    "задача", "задание", "небольшая задача", "небольшой проект",
    "подработка", "халтура",
    "тз", "техзадание", "по тз",
    "оплата за проект", "оплата по факту", "оплата после",
    "оплата на руки", "оплата сразу",
    "частичная занятость", "частично", "парт-тайм",
    "без оформления", "договор подряда", "гпх",
    "предоплата", "предоплата 50", "аванс",
    "кворк", "kwork", "fl.ru", "фл ру",
    # EN — type
    "freelance", "freelancer", "remote", "work from home", "wfh",
    "one-time", "one time", "single task", "single project",
    "gig", "short gig", "task",
    "project based", "project-based", "contract",
    "contract work", "contract position",
    "per project", "fixed price", "fixed budget",
    "part time", "part-time",
    "without benefits", "no benefits",
    # ES
    "freelance", "freelancer", "remoto", "remota", "trabajo remoto",
    "proyecto", "tarea", "trabajo puntual", "pago por proyecto",
    "media jornada", "sin contrato fijo",
]

FULLTIME_MARKERS = [
    # RU — явные job-board / постоянная занятость
    "вакансия", "вакансии", "вакансий", "канал вакансий",
    "оклад", "зп", "зарплата", "белая зарплата",
    "официальное трудоустройство", "трудоустройство",
    "трудовой договор", "трудовая книжка",
    "офис", "в офисе", "офисная работа", "офисный формат",
    "полный рабочий день", "полная занятость", "фулл-тайм",
    "постоянная работа", "постоянно", "на постоянную",
    "в штат", "штатный", "штатный сотрудник",
    "соц пакет", "соцпакет", "дмс", "страховка медицинская",
    "оплачиваемый отпуск", "больничный",
    "испытательный срок",
    "рассматриваем резюме", "отправьте резюме", "пришлите резюме",
    "собеседование", "на собеседование",
    "jobs", "job board", "джобс",
    # EN
    "full-time", "full time", "permanent", "permanent position",
    "salary", "salaried", "annual salary",
    "in-office", "on-site", "onsite", "office based",
    "benefits", "health insurance", "dental", "401k",
    "paid vacation", "paid time off", "pto",
    "employment contract", "long-term contract",
    "staff", "employee", "employment",
    "send your resume", "send your cv", "submit resume",
    "interview", "hiring process",
    # ES
    "tiempo completo", "jornada completa", "jornada laboral",
    "salario", "sueldo", "remuneración mensual",
    "oficina", "presencial", "trabajo presencial",
    "empleo permanente", "contrato indefinido", "contrato laboral",
    "prestaciones", "seguro médico", "vacaciones pagadas",
    "envía tu cv", "entrevista",
]

URGENT_MARKERS = [
    # RU
    "срочно", "срочная", "срочный", "срочное",
    "горит", "горящий", "горящая", "горящий проект",
    "нужно сегодня", "нужно сейчас", "прямо сейчас",
    "как можно быстрее", "как можно скорее", "кан скорей",
    "нужно срочно", "очень срочно",
    "к сегодняшнему", "к завтрашнему", "до завтра", "до вечера",
    "дедлайн сегодня", "дедлайн завтра",
    "асап", "асап!", "в ближайшее время",
    # EN
    "asap", "urgent", "urgently", "urgency",
    "immediately", "right now", "right away",
    "today", "tonight", "by tomorrow", "by end of day",
    "deadline today", "deadline tomorrow",
    "rush job", "rush project", "rush order",
    "need now", "needed now", "needed asap", "needed immediately",
    "time sensitive", "time-sensitive",
    # ES
    "urgente", "urgentemente", "con urgencia",
    "inmediatamente", "ahora mismo",
    "para hoy", "para mañana",
    "lo antes posible", "cuanto antes",
    "asap", "fecha límite hoy",
]

# ═══════════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def _norm(text: str) -> str:
    return text.lower().strip()


def _find_matches(text: str, word_list: list) -> list:
    """
    Ищет слова/фразы из word_list в тексте.
    Фразы (>1 слова): простой поиск подстроки.
    Одиночные слова: с границей (не внутри другого слова).
    """
    text_norm = _norm(text)
    found = []
    for word in word_list:
        w = _norm(word)
        if " " in w or "-" in w or "/" in w:
            # Фраза или составное слово — подстрока
            if w in text_norm:
                found.append(word)
        else:
            # Одиночное слово — с границей
            pattern = r"(?<![а-яёa-z\d])" + re.escape(w) + r"(?![а-яёa-z\d])"
            if re.search(pattern, text_norm):
                found.append(word)
    return found


def _detect_lang(text: str) -> str:
    """Определяет язык: RU / EN / ES / UNK."""
    t = text.lower()
    cyr   = len(re.findall(r"[а-яё]", t))
    latin = len(re.findall(r"[a-z]", t))
    total = cyr + latin
    if total == 0:
        return "UNK"

    if cyr / total > 0.35:
        return "RU"

    es_chars = len(re.findall(r"[áéíóúüñ¿¡]", t))
    es_words = len(re.findall(
        r"\b(hola|gracias|necesito|busco|trabajo|proyecto|diseño|desarrollador|"
        r"programador|remoto|pagamos|tenemos|buscamos)\b", t))
    if es_chars > 1 or es_words >= 1:
        return "ES"

    return "EN"


def _combo_score(text: str, triggers: list, subjects: list) -> int:
    """
    Считает пары (триггер, предмет) встретившихся в пределах 150 символов.
    Каждая уникальная пара = +1.
    """
    text_norm = _norm(text)
    score = 0
    seen = set()
    for tr in triggers:
        tr_n = _norm(tr)
        idx_tr = text_norm.find(tr_n)
        if idx_tr == -1:
            continue
        for subj in subjects:
            subj_n = _norm(subj)
            idx_s  = text_norm.find(subj_n)
            if idx_s == -1:
                continue
            pair = (tr_n, subj_n)
            if pair in seen:
                continue
            if abs(idx_tr - idx_s) <= 150:
                score += 1
                seen.add(pair)
    return score


# ═══════════════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(text: str, lang: str = None) -> dict:
    """
    Анализирует текст по трём уровням.

    Args:
        text: Текст сообщения
        lang: Подсказка языка ("RU"|"EN"|"ES"). None — автоопределение.

    Returns dict с ключами: relevant, job_type, is_urgent,
                             triggers, subjects, score, lang
    """
    if not text or not text.strip():
        return _empty_result("UNK")

    detected_lang = lang or _detect_lang(text)

    # Выбираем словари по языку
    # Для RU дополнительно проверяем EN-предметы (многие пишут технические
    # слова на английском даже в русском тексте)
    if detected_lang == "RU":
        triggers = TRIGGERS_RU
        subjects = SUBJECTS_RU + SUBJECTS_EN   # технические слова часто EN
    elif detected_lang == "ES":
        triggers = TRIGGERS_ES
        subjects = SUBJECTS_ES + SUBJECTS_EN
    else:  # EN + UNK
        triggers = TRIGGERS_EN
        subjects = SUBJECTS_EN

    # ── Уровень 1: триггеры ──
    found_triggers = _find_matches(text, triggers)

    # ── Уровень 2: предмет ──
    found_subjects = _find_matches(text, subjects)
    # Убираем дубли (из-за слияния RU+EN)
    found_subjects = list(dict.fromkeys(found_subjects))

    # ── Уровень 3: тип занятости ──
    found_freelance = _find_matches(text, FREELANCE_MARKERS)
    found_fulltime  = _find_matches(text, FULLTIME_MARKERS)
    found_urgent    = _find_matches(text, URGENT_MARKERS)

    is_urgent    = len(found_urgent) > 0
    has_freelance = len(found_freelance) > 0
    has_fulltime  = len(found_fulltime) > 0

    if is_urgent and not has_fulltime:
        job_type = "URGENT"
    elif has_freelance and not has_fulltime:
        job_type = "FREELANCE"
    elif has_fulltime and not has_freelance:
        job_type = "FULLTIME"
    elif has_freelance and has_fulltime:
        job_type = "FREELANCE" if len(found_freelance) >= len(found_fulltime) else "FULLTIME"
    else:
        job_type = "UNKNOWN"

    # ── Релевантность ──
    # Считаем релевантным даже если только предмет без триггера,
    # но с высоким combo_score (контекст очевидного заказа)
    combo = _combo_score(text, found_triggers, found_subjects)
    relevant = (
        (len(found_triggers) > 0 and len(found_subjects) > 0)
        or (len(found_subjects) >= 2 and combo > 0)
    )

    # ── Оценка score 0-100 ──
    score = 0
    score += min(len(found_triggers) * 12, 25)   # до 25 за триггеры
    score += min(len(found_subjects) * 10, 30)    # до 30 за предметы
    score += min(combo * 15, 30)                   # до 30 за близкие комбо
    if is_urgent:
        score += 10
    if has_freelance:
        score += 5
    score = min(score, 100)

    return {
        "relevant":  relevant,
        "job_type":  job_type,
        "is_urgent": is_urgent,
        "triggers":  found_triggers,
        "subjects":  found_subjects,
        "score":     score,
        "lang":      detected_lang,
    }


def _empty_result(lang: str) -> dict:
    return {
        "relevant":  False,
        "job_type":  "UNKNOWN",
        "is_urgent": False,
        "triggers":  [],
        "subjects":  [],
        "score":     0,
        "lang":      lang,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# БЫСТРЫЕ ХЕЛПЕРЫ для интеграции
# ═══════════════════════════════════════════════════════════════════════════════

def is_freelance_message(text: str, lang: str = None) -> bool:
    """True если релевантно И не постоянная работа."""
    r = analyze(text, lang)
    return r["relevant"] and r["job_type"] != "FULLTIME"


def is_fulltime_message(text: str, lang: str = None) -> bool:
    """True если это явно постоянная работа (нам не нужна)."""
    r = analyze(text, lang)
    return r["job_type"] == "FULLTIME"


def label(result: dict) -> str:
    """Текстовая метка для UI."""
    if not result["relevant"]:
        return ""
    mapping = {
        "URGENT":   "🔥 СРОЧНО",
        "FREELANCE": "✅ Фриланс",
        "FULLTIME":  "🏢 Постоянная",
        "UNKNOWN":   "❓ Тип неизвестен",
    }
    tag = mapping.get(result["job_type"], "")
    return f"{tag} (score={result['score']})"

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime
import os

EXPORT_PATH = "data/results.xlsx"


def export_to_excel(results: list):
    """
    Создаёт или обновляет файл Excel с результатами дня.
    results — список словарей из парсеров.
    """
    os.makedirs("data", exist_ok=True)

    if os.path.exists(EXPORT_PATH):
        wb = openpyxl.load_workbook(EXPORT_PATH)
    else:
        wb = openpyxl.Workbook()

    date_str = datetime.now().strftime("%d.%m.%Y")

    if date_str in wb.sheetnames:
        ws = wb[date_str]
    else:
        ws = wb.create_sheet(title=date_str)
        # Заголовки
        headers = [
            "Площадка",
            "Канал/Группа",
            "Тип",
            "Текст сообщения",
            "Наш ответ",
            "Статус",
            "Сумма ₽",
            "Время",
        ]
        ws.append(headers)

        # Стиль заголовков
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1B3A6B")
            cell.alignment = Alignment(horizontal="center")

    # Добавляем данные
    for item in results:
        ws.append(
            [
                item.get("platform", ""),
                item.get("channel", ""),
                "🟢 Горячий" if item.get("type") == "HOT" else "🔵 Холодный",
                item.get("text", ""),
                item.get("reply", ""),
                item.get("status", "новый"),
                item.get("amount", ""),
                datetime.now().strftime("%H:%M"),
            ]
        )

    # Ширина колонок
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 40
    ws.column_dimensions["E"].width = 40
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 10
    ws.column_dimensions["H"].width = 10

    wb.save(EXPORT_PATH)
    return EXPORT_PATH

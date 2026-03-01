import os

def list_directory(path: str = ".") -> str:
    """
    Показує вміст вказаної папки (файли та підпапки).
    Використовуй цей інструмент, коли потрібно дізнатися структуру проекту, 
    знайти потрібний файл або перевірити, чи існує директорія.
    
    Args:
        path: Шлях до папки (за замовчуванням поточна директорія).
    """
    print(f"📂 [File Master]: Сканую директорію: {path}")
    try:
        if not os.path.exists(path):
            return f"Помилка: Шлях {path} не існує."
        
        items = os.listdir(path)
        result = f"Вміст папки '{path}':\n"
        for item in items:
            item_path = os.path.join(path, item)
            item_type = "[ПАПКА]" if os.path.isdir(item_path) else "[ФАЙЛ]"
            result += f"- {item_type} {item}\n"
        return result
    except Exception as e:
        return f"Помилка доступу до папки: {e}"

def read_file(filepath: str) -> str:
    """
    Читає вміст текстового файлу або файлу з кодом (.py, .txt, .md, .json тощо).
    Використовуй цей інструмент, щоб проаналізувати існуючий код перед тим, як пропонувати зміни.
    
    Args:
        filepath: Повний або відносний шлях до файлу.
    """
    print(f"📄 [File Master]: Читаю файл: {filepath}")
    try:
        if not os.path.exists(filepath):
            return f"Помилка: Файл {filepath} не знайдено."
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"--- Початок файлу {filepath} ---\n{content}\n--- Кінець файлу ---"
    except Exception as e:
        return f"Помилка читання файлу: {e}"

def write_file(filepath: str, content: str) -> str:
    """
    Створює новий файл або ПОВНІСТЮ перезаписує існуючий заданим текстом/кодом.
    Використовуй цей інструмент для створення нових скриптів або застосування рефакторингу.
    
    Args:
        filepath: Шлях, куди зберегти файл.
        content: Текст або код, який потрібно записати.
    """
    print(f"✍️ [File Master]: Записую дані у файл: {filepath}")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Успіх: Дані успішно записані у файл {filepath}."
    except Exception as e:
        return f"Помилка запису у файл: {e}"

# Експортуємо інструменти для Оркестратора
EXPORTED_TOOLS = [list_directory, read_file, write_file]
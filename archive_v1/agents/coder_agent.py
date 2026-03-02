"""
Coder Agent - Аналіз та генерація коду.

Агент виконує:
1. Аналіз всього проекту (структура, залежності)
2. Пошук багів та проблем
3. Генерація повних модулів з кількома файлами
4. Рефакторинг коду
"""
import sys
import os
import datetime
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Виправлення кодування для Windows консолі
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Налаштування шляхів
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Додаємо батьківську директорію для імпорту config та GitOps
sys.path.insert(0, str(root_dir))

try:
    import config
except ImportError:
    config = None

# Імпорт GitOps для безпеки (прямий імпорт файлу, щоб уникнути завантаження skills/__init__.py)
try:
    import importlib.util
    git_ops_path = root_dir / "skills" / "git_ops.py"
    if git_ops_path.exists():
        spec = importlib.util.spec_from_file_location("git_ops", str(git_ops_path))
        git_ops_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(git_ops_module)
        GitOps = git_ops_module.GitOps
    else:
        GitOps = None
except Exception as e:
    print(f"⚠️ [CODER] GitOps не завантажено: {e}", file=sys.stderr)
    GitOps = None

# Імпортуємо шляхи з config.py
import config
PROJECTS_DIR = str(config.PROJECTS_ROOT_DIR)


def analyze_project(project_name: str, task_type: str = "analyze", context_info: str = ""):
    """
    Аналізує проект або виконує інші задачі з кодом.
    
    Args:
        project_name: Назва проекту
        task_type: Тип задачі (analyze, find_bugs, generate_module, refactor)
        context_info: Додатковий контекст
    """
    print(f"💻 [CODER] Починаю роботу над проектом: {project_name}")
    print(f"📋 [CODER] Тип задачі: {task_type}")
    
    # 1. Налаштування Gemini
    api_key = config.GOOGLE_API_KEY
    if not api_key:
        print("❌ [CODER] Помилка: Не знайдено GOOGLE_API_KEY")
        return

    genai.configure(api_key=api_key)
    
    # Використовуємо модель для кодування з config
    coder_model = getattr(config, "GEMINI_CODER_MODEL", "gemini-3.1-pro-preview")
    
    try:
        print(f"🧠 [CODER] Використовую модель: {coder_model}")
        model = genai.GenerativeModel(coder_model)
    except Exception as e:
        print(f"⚠️ [CODER] Не вдалося завантажити {coder_model}: {e}")
        model = genai.GenerativeModel('gemini-1.5-pro')

    # 2. Знаходимо проект
    project_path = _find_project(project_name)
    if not project_path:
        error_msg = f"❌ [CODER] Проект '{project_name}' не знайдено"
        print(error_msg, file=sys.stderr)
        raise FileNotFoundError(error_msg)
    
    print(f"✅ [CODER] Проект знайдено: {project_path}")
    
    # 3. Виконуємо задачу залежно від типу
    if task_type == "analyze":
        result = _analyze_project_structure(model, project_path, context_info)
    elif task_type == "find_bugs":
        result = _find_bugs(model, project_path, context_info)
    elif task_type == "generate_module":
        result = _generate_module(model, project_path, context_info)
    elif task_type == "refactor":
        result = _refactor_code(model, project_path, context_info)
    else:
        result = f"Невідомий тип задачі: {task_type}"
    
    # 4. Збереження результату
    _save_result(project_name, task_type, result, project_path)
    
def _find_project(project_name: str) -> str:
    """
    Знаходить шлях до проекту.
    
    Args:
        project_name: Назва проекту
        
    Returns:
        Шлях до проекту або None
    """
    print(f"🔍 [CODER] Шукаю проект: {project_name}")
    
    # Перевіряємо стандартну папку Projects
    if os.path.exists(PROJECTS_DIR):
        # Спробуємо точну назву
        project_path = os.path.join(PROJECTS_DIR, project_name)
        if os.path.exists(project_path):
            print(f"✅ [CODER] Знайдено в Projects: {project_path}")
            return project_path
        
        # Спробуємо з великої літери
        project_path = os.path.join(PROJECTS_DIR, project_name.capitalize())
        if os.path.exists(project_path):
            print(f"✅ [CODER] Знайдено в Projects (capitalized): {project_path}")
            return project_path
        
        # Спробуємо пошук за частиною назви
        try:
            for item in os.listdir(PROJECTS_DIR):
                item_path = os.path.join(PROJECTS_DIR, item)
                if os.path.isdir(item_path):
                    if project_name.lower() in item.lower() or item.lower() in project_name.lower():
                        print(f"✅ [CODER] Знайдено за частиною назви: {item_path}")
                        return item_path
        except Exception as e:
            print(f"⚠️ [CODER] Помилка пошуку в Projects: {e}")
    
    # Перевіряємо поточну директорію (SystemCOO)
    current_project = root_dir / project_name
    if current_project.exists():
        print(f"✅ [CODER] Знайдено в поточній директорії: {current_project}")
        return str(current_project)
    
    # Перевіряємо, чи це сам SystemCOO
    if project_name.lower() in ["systemcoo", "system coo", "атлас", "atlas"]:
        print(f"✅ [CODER] Це SystemCOO: {root_dir}")
        return str(root_dir)
    
    print(f"❌ [CODER] Проект '{project_name}' не знайдено в {PROJECTS_DIR}")
    return None


def _analyze_project_structure(model, project_path: str, context_info: str) -> str:
    """
    Аналізує структуру проекту з двоетапним мисленням (Scan-then-Read).
    
    Етап 1 (Мапа): Створює мапу проекту
    Етап 2 (Вивчення): Вибір ключових файлів та їх детальне читання
    
    Args:
        model: Gemini модель
        project_path: Шлях до проекту
        context_info: Додатковий контекст
        
    Returns:
        Результат аналізу
    """
    print("🔍 [CODER] Аналізую структуру проекту...")
    
    # ОПТИМІЗОВАНО: Використовуємо дефолтні ключові файли (без додаткового запиту до API)
    # Це швидше та не викликає rate limiting
    key_files = [
        "gui.py", "skills/brain.py", "skills/router.py",
        "agents/coder_agent.py", "agents/queue_manager.py"
    ]
    
    print(f"📂 [CODER] Використовую ключові файли: {', '.join(key_files)}")
    
    # Читаємо ключові файли
    files_with_lines = {}
    for file_path in key_files:
        lines = read_file_content(project_path, file_path)
        if lines:
            files_with_lines[file_path] = lines
    
    # Форматуємо файли з нумерацією рядків
    formatted_code = _format_files_with_line_numbers(files_with_lines)
    
    # Збираємо структуру проекту (без детального коду для швидкості)
    project_structure = _collect_project_info(project_path)
    
    # Діагностика
    files_count = len(files_with_lines)
    total_lines = sum(len(lines) for lines in files_with_lines.values())
    print(f"📊 [CODER] Прочитано {files_count} ключових файлів, {total_lines} рядків коду")
    
    if files_count == 0:
        print("⚠️ [CODER] УВАГА: Не знайдено файлів з кодом для аналізу!")
        # Fallback: використовуємо старий метод
        files_with_lines = read_project_files(project_path, max_files=10)
        formatted_code = _format_files_with_line_numbers(files_with_lines)
    
    prompt = f"""
РОЛЬ: Старший архітектор програмного забезпечення / Аналітик коду.
ЗАВДАННЯ: Провести ПОВНИЙ та ДЕТАЛЬНИЙ аналіз проекту на основі структури ТА коду.

СТРУКТУРА ПРОЕКТУ:
{project_structure}

═══════════════════════════════════════════════════════════════
КОД ФАЙЛІВ З НУМЕРАЦІЄЮ РЯДКІВ (ВИКОРИСТОВУЙТЕ ДЛЯ ТОЧНОГО АНАЛІЗУ):
═══════════════════════════════════════════════════════════════
{formatted_code}

КРИТИЧНО ВАЖЛИВО:
- НЕ використовуйте фрази типу "ймовірно містить", "може бути", "швидше за все"
- ВИКОРИСТОВУЙТЕ конкретні посилання на рядки коду: "рядок 45 містить помилку", "функція на рядках 120-150"
- АНАЛІЗУЙТЕ фактичний код, який надано вище з нумерацією рядків
- Цитуйте конкретні рядки коду для підтвердження висновків

КОНТЕКСТ: {context_info}

ВИМОГИ ДО АНАЛІЗУ:
- МОВА: ВИКЛЮЧНО українською мовою (Ukrainian). ВСІ відповіді мають бути українською!
- Аналіз має бути ПОВНИМ та ДЕТАЛЬНИМ (мінімум 2000 слів).
- Аналізуйте І структуру, І фактичний код:

1. СТРУКТУРА ТА АРХІТЕКТУРА ПРОЕКТУ:
   - Детальний опис структури папок та їх призначення
   - Архітектурні рішення та патерни
   - Організація модулів та компонентів

2. ОСНОВНІ КОМПОНЕНТИ ТА ЇХ ВЗАЄМОЗВ'ЯЗКИ:
   - Детальний опис кожного ключового компонента (на основі КОДУ)
   - Як компоненти взаємодіють між собою
   - Потоки даних та управління станом
   - Залежності між модулями

3. ТЕХНОЛОГІЇ ТА ЗАЛЕЖНОСТІ:
   - Всі використані бібліотеки та фреймворки (визначити з імпортів)
   - Версії Python та інших технологій
   - Зовнішні сервіси та API

4. ОЦІНКА ЯКОСТІ КОДУ:
   - Відповідність PEP 8 та best practices
   - Читабельність та підтримуваність
   - Наявність документації
   - Обробка помилок
   - Тестування

5. ПОТЕНЦІЙНІ БАГИ ТА ПРОБЛЕМИ:
   - Конкретні проблеми в коді з ТОЧНИМИ посиланнями на рядки (формат: "файл.py:рядок_45")
   - TODO коментарі та незавершені функції (з номерами рядків)
   - Потенційні race conditions (з посиланнями на код)
   - Проблеми з безпекою (конкретні приклади з рядками)
   - Проблеми з продуктивністю (з аналізом конкретного коду)
   - Memory leaks або інші проблеми з ресурсами (з посиланнями)
   - Відсутність обробки помилок (конкретні місця)

6. РЕКОМЕНДАЦІЇ ПО ПОКРАЩЕННЮ:
   - Конкретні пропозиції з прикладами
   - Рефакторинг коду
   - Оптимізація продуктивності
   - Покращення архітектури
   - Додавання тестів

7. ДОДАТКОВІ СПОСТЕРЕЖЕННЯ:
   - Унікальні особливості проекту
   - Сильні сторони
   - Області, що потребують уваги

ВАЖЛИВО: Базуйте аналіз на ФАКТИЧНОМУ КОДІ, який надано, а не тільки на назвах файлів!

ВИХІД: Детальний аналіз ВИКЛЮЧНО українською мовою, мінімум 2000 слів, з конкретними прикладами з коду та структурованими розділами.
"""
    
    try:
        # Налаштування генерації для довших відповідей
        from google.generativeai.types import GenerationConfig
        
        generation_config = GenerationConfig(
            temperature=0.7,  # Більше креативності для детального аналізу
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,  # Максимальна довжина відповіді
        )
        
        # Додаємо обробку rate limiting
        max_retries = 3
        retry_delay = 2  # секунди
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                result_text = response.text
                break  # Успішно, виходимо з циклу
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Resource exhausted" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"⚠️ [CODER] Rate limit досягнуто, чекаю {wait_time} сек перед повторною спробою...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Досягнуто ліміт API після {max_retries} спроб. Спробуйте пізніше.")
                else:
                    raise  # Інша помилка - прокидаємо далі
        
        # Перевірка довжини відповіді
        word_count = len(result_text.split())
        char_count = len(result_text)
        print(f"📊 [CODER] Перша спроба: {word_count} слів, {char_count} символів")
        
        # Якщо відповідь коротка, робимо до 2 повторних спроб
        max_retries = 2
        retry_count = 0
        
        while (word_count < 2000 or char_count < 10000) and retry_count < max_retries:
            retry_count += 1
            print(f"⚠️ [CODER] Відповідь занадто коротка ({word_count} слів, {char_count} символів), спроба {retry_count}/{max_retries}...")
            
            # Формуємо більш детальний промпт для повторної спроби
            retry_prompt = f"""{prompt}

═══════════════════════════════════════════════════════════════
КРИТИЧНО ВАЖЛИВО - РОЗШИРЕННЯ АНАЛІЗУ (спроба {retry_count}):
═══════════════════════════════════════════════════════════════

Поточна відповідь має лише {word_count} слів, але потрібно МІНІМУМ 2000 слів!

ВИМОГИ ДО РОЗШИРЕННЯ:
1. Розгорніть КОЖЕН з 7 розділів детально (мінімум 300 слів на розділ)
2. Додайте конкретні приклади з коду - цитуйте рядки коду з файлів
3. Опишіть кожен компонент детально - як він працює, що робить
4. Надайте конкретні рекомендації з прикладами коду
5. Додайте аналіз взаємозв'язків між компонентами
6. Включіть приклади використання API та функцій
7. Додайте оцінку продуктивності та масштабованості

ФОРМАТ:
- Кожен розділ має бути ДЕТАЛЬНИМ (не короткі пункти!)
- Використовуйте конкретні приклади з наданого коду
- Цитуйте рядки коду з файлів для підтвердження висновків
- Додайте таблиці та структуровані списки де можливо

Аналіз має бути ПОВНИМ та ДЕТАЛЬНИМ, не коротким резюме!
"""
            
            try:
                response = model.generate_content(
                    retry_prompt,
                    generation_config=generation_config
                )
                result_text = response.text
                word_count = len(result_text.split())
                char_count = len(result_text)
                print(f"📊 [CODER] Спроба {retry_count}: {word_count} слів, {char_count} символів")
            except Exception as e:
                print(f"❌ [CODER] Помилка при повторній спробі: {e}", file=sys.stderr)
                break
        
        print(f"✅ [CODER] Згенеровано аналіз: {word_count} слів, {char_count} символів")
        return result_text
    except Exception as e:
        error_msg = f"Помилка аналізу: {e}"
        print(f"❌ [CODER] {error_msg}", file=sys.stderr)
        return error_msg


def _find_bugs(model, project_path: str, context_info: str) -> str:
    """
    Знаходить баги та проблеми в коді.
    
    Args:
        model: Gemini модель
        project_path: Шлях до проекту
        context_info: Додатковий контекст
        
    Returns:
        Список знайдених проблем
    """
    print("🐛 [CODER] Шукаю баги та проблеми...")
    
    # Збираємо код з основних файлів
    code_samples = _collect_code_samples(project_path, max_files=10)
    
    prompt = f"""
ROLE: Senior Code Reviewer / Bug Hunter.
TASK: Find bugs, errors, and potential issues in the ACTUAL CODE.

CODE SAMPLES (ПОВНИЙ КОД ФАЙЛІВ):
{code_samples}

CONTEXT: {context_info}

REQUIREMENTS:
- Language: Ukrainian (Українська).
- Analyze the PROVIDED CODE for:
  1. Syntax errors (перевірте синтаксис Python)
  2. Logic errors (помилки в логіці)
  3. Performance issues (неефективні алгоритми, зайві цикли)
  4. Security vulnerabilities (SQL injection, XSS, небезпечні імпорти)
  5. Code smells (дублювання коду, довгі функції, magic numbers)
  6. Best practices violations (PEP 8, naming conventions)
  7. Missing error handling (try/except блоки)
  8. Type hints absence (якщо потрібно)
- Format: List of issues with:
  * File path
  * Line number (якщо можна визначити)
  * Description of the issue
  * Severity (Critical/High/Medium/Low)
  * Suggested fix
- IMPORTANT: Analyze the ACTUAL CODE provided, not assumptions!

OUTPUT: Detailed bug report with specific code references.
"""
    
    try:
        response = model.generate_content(prompt).text
        return response
    except Exception as e:
        return f"Помилка пошуку багів: {e}"


def _generate_module(model, project_path: str, context_info: str) -> str:
    """
    Генерує новий модуль з кількома файлами або окремі файли (HTML, CSS, Python).
    
    Args:
        model: Gemini модель
        project_path: Шлях до проекту
        context_info: Додатковий контекст (назва модуля, структура, тип файлу)
        
    Returns:
        Результат генерації
    """
    print("🏗️ [CODER] Генерую код...")
    
    # Визначаємо тип файлу з контексту
    context_lower = context_info.lower()
    file_type = "python"  # За замовчуванням
    if "html" in context_lower or "сторінка" in context_lower:
        file_type = "html"
    elif "css" in context_lower or "стилі" in context_lower:
        file_type = "css"
    elif "javascript" in context_lower or "js" in context_lower:
        file_type = "javascript"
    
    # Витягуємо назву модуля/файлу з контексту
    module_name = _extract_module_name(context_info)
    
    # Аналізуємо структуру проекту для розуміння стилю
    project_info = _collect_project_info(project_path)
    
    # Формуємо промпт залежно від типу файлу
    if file_type == "html":
        prompt = f"""
ROLE: Senior Frontend Developer.
TASK: Generate a complete HTML page with embedded CSS and JavaScript (if needed).

PROJECT STRUCTURE:
{project_info}

REQUIREMENTS:
{context_info}

CRITICAL FORMAT REQUIREMENT:
You MUST format your output using this exact structure:

=== index.html ===
[complete HTML file content here]

=== styles.css ===
[complete CSS file content here (if separate file needed)]

IMPORTANT:
- Use "===" markers (three equals signs) to separate files
- Include full relative path from project root
- Each file must be complete and ready to use
- Do NOT use markdown code blocks, just raw code
- HTML must be valid and include DOCTYPE, head, body
- CSS should be modern and responsive

OUTPUT: Complete HTML page with CSS in the format above.
"""
    elif file_type == "css":
        prompt = f"""
ROLE: Senior Frontend Developer.
TASK: Generate a complete CSS stylesheet.

PROJECT STRUCTURE:
{project_info}

REQUIREMENTS:
{context_info}

CRITICAL FORMAT REQUIREMENT:
You MUST format your output using this exact structure:

=== styles.css ===
[complete CSS file content here]

IMPORTANT:
- Use "===" markers (three equals signs) to separate files
- Include full relative path from project root
- CSS must be modern, responsive, and well-organized
- Do NOT use markdown code blocks, just raw code

OUTPUT: Complete CSS file in the format above.
"""
    else:
        # Python модуль (оригінальна логіка)
        prompt = f"""
ROLE: Senior Software Developer.
TASK: Generate a complete module with multiple files.

PROJECT STRUCTURE:
{project_info}

MODULE REQUIREMENTS:
{context_info}

REQUIREMENTS:
- Language: Python (unless specified otherwise).
- Generate complete, production-ready code.
- Include:
  1. Main module file
  2. __init__.py
  3. Tests (if applicable)
  4. Documentation (docstrings)
- Follow project's code style and conventions.

CRITICAL FORMAT REQUIREMENT:
You MUST format your output using this exact structure for each file:

=== path/to/file.py ===
[complete file content here]

=== path/to/another_file.py ===
[complete file content here]

IMPORTANT:
- Use "===" markers (three equals signs) to separate files
- Include full relative path from project root
- Each file must be complete and ready to use
- Do NOT use markdown code blocks (```python), just raw code
- Example format:
  === new_module/__init__.py ===
  # Module initialization
  from .main import MainClass
  
  === new_module/main.py ===
  class MainClass:
      def __init__(self):
          pass

OUTPUT: Complete module structure with all files in the format above.
"""
    
    try:
        print(f"🤖 [CODER] Генерую код через Gemini...")
        response = model.generate_content(prompt).text
        print(f"✅ [CODER] Код згенеровано, довжина: {len(response)} символів")
        
        # 🔥 НОВА ФУНКЦІОНАЛЬНІСТЬ: Відкриваємо Cursor та відправляємо промпт
        # Якщо це HTML/CSS/JS - відправляємо в Cursor для генерації
        if file_type in ["html", "css", "javascript"]:
            print(f"🎯 [CODER] Тип файлу: {file_type}, відкриваю Cursor...")
            try:
                from skills.cursor_agent import CursorAgent
                cursor_agent = CursorAgent()
                
                # Відкриваємо проект в Cursor
                cursor_path = cursor_agent.cursor_path
                if os.path.exists(cursor_path):
                    print(f"🚀 [CODER] Запускаю Cursor з проектом: {project_path}")
                    subprocess.Popen([cursor_path, project_path], shell=False)
                    print(f"⏳ [CODER] Чекаю 2 секунди поки Cursor відкриється...")
                    time.sleep(2)  # Чекаємо поки Cursor відкриється
                    print(f"✅ [CODER] Cursor має бути відкритий")
                else:
                    print(f"⚠️ [CODER] Cursor не знайдено за шляхом: {cursor_path}")
                
                # Формуємо промпт для Cursor
                cursor_prompt = f"""Create a {file_type.upper()} file with the following requirements:

{context_info}

Please generate complete, production-ready code with modern styling and best practices."""
                
                print(f"📤 [CODER] Відправляю промпт в Cursor Chat...")
                # Відправляємо промпт в Cursor
                cursor_result = cursor_agent.send_prompt(cursor_prompt, mode="chat")
                print(f"✅ [CODER] Промпт відправлено в Cursor: {cursor_result}")
                
                # Також записуємо файли на диск (backup)
                print(f"💾 [CODER] Зберігаю файли на диск як backup...")
                files_written = _write_module_to_project(response, project_path, module_name)
                if files_written:
                    response += f"\n\n✅ [CODER] Файли також збережено на диск:\n"
                    for file in files_written:
                        response += f"   - {file}\n"
                
                response += f"\n\n✅ [CODER] Промпт відправлено в Cursor Chat (Ctrl+L). Перевірте чат Cursor для результату."
                
            except Exception as e:
                print(f"⚠️ [CODER] Помилка інтеграції з Cursor: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Fallback: просто записуємо файли
                print(f"💾 [CODER] Fallback: зберігаю файли на диск...")
                files_written = _write_module_to_project(response, project_path, module_name)
                if files_written:
                    response += f"\n\n✅ [CODER] Модуль записано в проект:\n"
                    for file in files_written:
                        response += f"   - {file}\n"
        else:
            # Для Python модулів - просто записуємо файли
            print(f"💾 [CODER] Зберігаю Python модуль на диск...")
            files_written = _write_module_to_project(response, project_path, module_name)
            if files_written:
                response += f"\n\n✅ [CODER] Модуль записано в проект:\n"
                for file in files_written:
                    response += f"   - {file}\n"
        
        print(f"✅ [CODER] Генерація завершена успішно")
        return response
    except Exception as e:
        return f"Помилка генерації модуля: {e}"


def _refactor_code(model, project_path: str, context_info: str) -> str:
    """
    Рефакторить код.
    
    Args:
        model: Gemini модель
        project_path: Шлях до проекту
        context_info: Додатковий контекст (що рефакторити)
        
    Returns:
        Результат рефакторингу
    """
    print("🔧 [CODER] Рефакторю код...")
    
    # Збираємо код для рефакторингу
    code_samples = _collect_code_samples(project_path, max_files=5)
    
    prompt = f"""
ROLE: Senior Software Engineer / Refactoring Expert.
TASK: Refactor code to improve quality, readability, and maintainability.

CODE TO REFACTOR:
{code_samples}

REFACTORING REQUIREMENTS:
{context_info}

REQUIREMENTS:
- Language: Ukrainian (Українська) for comments, Python for code.
- Improve:
  1. Code structure and organization
  2. Variable and function naming
  3. Remove code duplication
  4. Improve error handling
  5. Add type hints (if applicable)
  6. Optimize performance
- Format: Provide refactored code with explanations.

OUTPUT: Refactored code with improvements.
"""
    
    try:
        response = model.generate_content(prompt).text
        return response
    except Exception as e:
        return f"Помилка рефакторингу: {e}"


def read_file_content(project_path: str, file_path: str, start_line: int = None, end_line: int = None) -> list:
    """
    Читає конкретний файл або діапазон рядків з нумерацією.
    
    Args:
        project_path: Шлях до проекту
        file_path: Відносний шлях до файлу (наприклад, "skills/router.py")
        start_line: Початковий рядок (якщо None - з початку)
        end_line: Кінцевий рядок (якщо None - до кінця)
        
    Returns:
        Список [(line_num, line_content), ...]
    """
    full_path = os.path.join(project_path, file_path)
    
    if not os.path.exists(full_path):
        print(f"❌ [CODER] Файл не знайдено: {file_path}")
        return []
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Визначаємо діапазон
        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = len(lines)
        
        # Обмежуємо діапазон
        start_line = max(1, min(start_line, len(lines)))
        end_line = max(start_line, min(end_line, len(lines)))
        
        # Витягуємо рядки з нумерацією
        numbered_lines = [(i+1, line.rstrip('\n')) for i, line in enumerate(lines[start_line-1:end_line])]
        
        print(f"✅ [CODER] Прочитано {file_path}: рядки {start_line}-{end_line} ({len(numbered_lines)} рядків)")
        return numbered_lines
        
    except Exception as e:
        print(f"❌ [CODER] Помилка читання {file_path}: {e}", file=sys.stderr)
        return []


def read_project_files(project_path: str, file_patterns: list = None, max_files: int = 20) -> dict:
    """
    Читає файли проекту з нумерацією рядків для точного аналізу.
    
    Args:
        project_path: Шлях до проекту
        file_patterns: Список патернів файлів для читання (наприклад, ['*.py'])
        max_files: Максимальна кількість файлів
        
    Returns:
        Словник {file_path: [(line_num, line_content), ...]}
    """
    if file_patterns is None:
        file_patterns = ['*.py']
    
    files_content = {}
    count = 0
    
    # Пріоритетні файли
    priority_files = [
        "gui.py", "main.py", "config.py",
        "skills/brain.py", "skills/router.py", "skills/context.py",
        # Департаменти видалено (залишено тільки operations.py)
        "agents/writer_agent.py", "agents/smm_agent.py", "agents/coder_agent.py",
        "agents/queue_manager.py", "skills/command_queue.py", "skills/journal.py"
    ]
    
    # Читаємо пріоритетні файли
    for priority_file in priority_files:
        if count >= max_files:
            break
            
        file_path = os.path.join(project_path, priority_file)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Зберігаємо з нумерацією рядків
                    numbered_lines = [(i+1, line.rstrip('\n')) for i, line in enumerate(lines)]
                    files_content[priority_file] = numbered_lines
                    count += 1
                    print(f"✅ [CODER] Прочитано з нумерацією: {priority_file} ({len(lines)} рядків)")
            except Exception as e:
                print(f"❌ [CODER] Помилка читання {priority_file}: {e}", file=sys.stderr)
    
    # Читаємо інші .py файли
    if count < max_files:
        try:
            for root, dirs, files in os.walk(project_path):
                if count >= max_files:
                    break
                    
                # Пропускаємо служебні папки
                dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules', '.idea']]
                
                for file in files:
                    if count >= max_files:
                        break
                        
                    if file.endswith('.py') and file not in ['__init__.py']:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, project_path)
                        
                        # Пропускаємо, якщо вже прочитали
                        if rel_path in files_content:
                            continue
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                numbered_lines = [(i+1, line.rstrip('\n')) for i, line in enumerate(lines)]
                                files_content[rel_path] = numbered_lines
                                count += 1
                        except Exception as e:
                            pass
        except Exception as e:
            print(f"⚠️ [CODER] Помилка обходу файлів: {e}", file=sys.stderr)
    
    print(f"📊 [CODER] Прочитано {len(files_content)} файлів з нумерацією рядків")
    return files_content


def _format_files_with_line_numbers(files_content: dict) -> str:
    """
    Форматує файли з нумерацією рядків для промпту.
    
    Args:
        files_content: Словник {file_path: [(line_num, line_content), ...]}
        
    Returns:
        Форматований текст з нумерацією рядків
    """
    formatted = []
    
    for file_path, lines in files_content.items():
        formatted.append(f"\n{'='*70}")
        formatted.append(f"ФАЙЛ: {file_path}")
        formatted.append(f"{'='*70}\n")
        
        # Додаємо нумерацію рядків
        for line_num, line_content in lines:
            formatted.append(f"{line_num:5d} | {line_content}")
        
        formatted.append("")  # Порожній рядок між файлами
    
    return "\n".join(formatted)


def _collect_project_info(project_path: str) -> str:
    """
    Збирає інформацію про структуру проекту ТА ключові файли з кодом.
    
    Args:
        project_path: Шлях до проекту
        
    Returns:
        Інформація про проект (структура + код ключових файлів)
    """
    info = []
    info.append(f"Project Path: {project_path}\n")
    info.append("=" * 60 + "\n")
    
    # 1. Структура папок
    info.append("📁 СТРУКТУРА ПРОЕКТУ:\n")
    try:
        for root, dirs, files in os.walk(project_path):
            # Пропускаємо венв та інші служебні папки
            dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules', '.idea', 'venv']]
            
            level = root.replace(project_path, '').count(os.sep)
            indent = ' ' * 2 * level
            info.append(f"{indent}{os.path.basename(root)}/")
            
            # Додаємо файли
            subindent = ' ' * 2 * (level + 1)
            for file in files[:10]:  # Більше файлів
                if file.endswith(('.py', '.js', '.ts', '.html', '.css', '.md', '.json')):
                    info.append(f"{subindent}{file}")
        
        info.append("\n" + "=" * 60 + "\n")
        
        # 2. КЛЮЧОВІ ФАЙЛИ З КОДОМ (для глибшого аналізу)
        info.append("📄 КОД КЛЮЧОВИХ ФАЙЛІВ:\n\n")
        
        # Пріоритетні файли для аналізу (більше файлів для повного аналізу)
        priority_files = [
            "gui.py", "main.py", "config.py",
            "skills/brain.py", "skills/router.py", "skills/context.py",
            # Департаменти видалено (залишено тільки operations.py)
            "agents/writer_agent.py", "agents/smm_agent.py", "agents/coder_agent.py",
            "agents/queue_manager.py", "skills/command_queue.py", "skills/journal.py"
        ]
        
        code_added = False
        files_read = 0
        total_code_size = 0
        
        for priority_file in priority_files:
            file_path = os.path.join(project_path, priority_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        original_size = len(content)
                        # Збільшуємо ліміт для пріоритетних файлів до 8000 символів
                        max_chars = 8000 if priority_file in ["gui.py", "skills/brain.py", "skills/router.py"] else 5000
                        if len(content) > max_chars:
                            content = content[:max_chars] + f"\n... (truncated, file too long: {original_size} chars total)"
                        info.append(f"=== {priority_file} ===\n{content}\n\n")
                        code_added = True
                        files_read += 1
                        total_code_size += len(content)
                        print(f"✅ [CODER] Прочитано: {priority_file} ({len(content)} символів)")
                except Exception as e:
                    error_msg = f"⚠️ Помилка читання {priority_file}: {e}"
                    info.append(f"{error_msg}\n\n")
                    print(f"❌ [CODER] {error_msg}", file=sys.stderr)
        
        print(f"📊 [CODER] Прочитано {files_read} файлів, всього {total_code_size} символів коду")
        
        # Якщо не знайшли пріоритетні файли, беремо перші .py файли з кореня
        if not code_added:
            try:
                for file in os.listdir(project_path):
                    if file.endswith('.py') and file not in ['__init__.py']:
                        file_path = os.path.join(project_path, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if len(content) > 3000:
                                    content = content[:3000] + "\n... (truncated)"
                                info.append(f"=== {file} ===\n{content}\n\n")
                                code_added = True
                                if len([x for x in info if "===" in x]) >= 3:  # Максимум 3 файли
                                    break
                        except:
                            pass
            except:
                pass
        
        return "\n".join(info)
    except Exception as e:
        return f"Помилка збору інформації: {e}"


def _collect_code_samples(project_path: str, max_files: int = 15) -> str:
    """
    Збирає зразки коду з проекту (ПОВНИЙ КОД, не тільки структуру).
    
    Args:
        project_path: Шлях до проекту
        max_files: Максимальна кількість файлів
        
    Returns:
        Зразки коду з повним вмістом
    """
    samples = []
    count = 0
    
    # Пріоритетні файли для аналізу
    priority_files = []
    
    try:
        # Спочатку збираємо пріоритетні файли
        for root, dirs, files in os.walk(project_path):
            # Пропускаємо служебні папки
            dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules', '.idea', 'venv']]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                
                # Пріоритет: головні файли проекту
                if any(priority in rel_path.lower() for priority in ['gui.py', 'main.py', 'brain.py', 'router.py', 'agent', 'department']):
                    priority_files.append(file_path)
        
        # Читаємо пріоритетні файли повністю
        for file_path in priority_files[:max_files//2]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Для пріоритетних файлів - більше коду
                    if len(content) > 8000:
                        # Беремо початок та кінець файлу
                        content = content[:4000] + "\n\n... (middle part truncated) ...\n\n" + content[-4000:]
                    rel_path = os.path.relpath(file_path, project_path)
                    samples.append(f"\n{'='*60}\n=== {rel_path} (ПОВНИЙ КОД) ===\n{'='*60}\n{content}\n")
                    count += 1
            except Exception as e:
                print(f"⚠️ [CODER] Помилка читання {file_path}: {e}")
        
        # Додаємо інші файли
        for root, dirs, files in os.walk(project_path):
            if count >= max_files:
                break
                
            dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules', '.idea', 'venv']]
            
            for file in files:
                if count >= max_files:
                    break
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                
                # Пропускаємо, якщо вже додали
                if file_path in priority_files:
                    continue
                
                if file.endswith(('.py', '.js', '.ts', '.html', '.css')):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Для звичайних файлів - до 5000 символів
                            if len(content) > 5000:
                                content = content[:5000] + "\n... (truncated, file too long)"
                            samples.append(f"\n{'='*60}\n=== {rel_path} ===\n{'='*60}\n{content}\n")
                            count += 1
                    except Exception as e:
                        print(f"⚠️ [CODER] Помилка читання {file_path}: {e}")
        
        if not samples:
            return "⚠️ Не вдалося зібрати зразки коду. Перевірте шлях до проекту."
        
        return "\n".join(samples)
    except Exception as e:
        return f"Помилка збору зразків: {e}"


def _extract_module_name(context_info: str) -> str:
    """
    Витягує назву модуля з контексту.
    
    Args:
        context_info: Контекст з назвою модуля
        
    Returns:
        Назва модуля
    """
    # Простий парсинг
    words = context_info.lower().split()
    if "модуль" in words:
        idx = words.index("модуль")
        if idx + 1 < len(words):
            return words[idx + 1]
    return "new_module"


def _write_module_to_project(generated_code: str, project_path: str, module_name: str) -> list:
    """
    Парсить згенерований код та записує файли безпосередньо в проект.
    Підтримує формати: === path/to/file ===, File: path/to/file, та markdown блоки.
    """
    print(f"💾 [CODER] Запис модуля '{module_name}' у {project_path}...")
    
    # 🔒 БЕЗПЕКА: Створюємо Git backup перед змінами
    if GitOps and os.path.exists(os.path.join(project_path, ".git")):
        try:
            commit_msg = f"🛡️ [ATLAS BACKUP] Before writing module: {module_name}"
            GitOps.quick_commit(project_path, commit_msg)
            print("✅ [CODER] Git backup створено")
        except Exception as e:
            print(f"⚠️ [CODER] Git backup failed: {e}")
    
    files_written = []
    
    # Регулярні вирази для різних форматів виводу AI
    patterns = [
        r'===?\s*(.+?)\s*===?\s*\n(.*?)(?=\n===?\s*|$)', # === path/to/file ===
        r'File:\s*(.+?)\s*\n(.*?)(?=\nFile:\s*|$)',     # File: path/to/file
        r'#\s*([a-zA-Z0-9_\-\./]+\.[a-z0-9]+)\s*\n(.*?)(?=\n#\s*[a-zA-Z0-9_\-\./]+\.[a-z0-9]+|$)', # # path/to/file.py
    ]
    
    all_matches = []
    for pattern in patterns:
        matches = re.findall(pattern, generated_code, re.DOTALL)
        if matches:
            all_matches.extend(matches)
            break # Використовуємо перший спрацювавший формат
            
    if all_matches:
        for file_path, content in all_matches:
            file_path = file_path.strip().replace('`', '')
            content = content.strip()
            
            # Видаляємо markdown обгортки (```python ... ```)
            content = re.sub(r'```[a-z]*\s*\n?', '', content)
            content = re.sub(r'```\s*$', '', content)
            
            # Робимо шлях відносним до кореня проекту, якщо він не такий
            if file_path.startswith(module_name) and not os.path.isabs(file_path):
                pass
            
            full_path = os.path.join(project_path, file_path)
            
            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_written.append(file_path)
                print(f"   📄 Створено: {file_path}")
            except Exception as e:
                print(f"   ❌ Помилка запису {file_path}: {e}")
    else:
        # Fallback: якщо AI не використав формат, але видав код
        print("⚠️ [CODER] Не знайдено структуру файлів, записую як монолітний файл...")
        ext = ".py"
        if "<html>" in generated_code.lower(): ext = ".html"
        
        target_file = os.path.join(project_path, f"{module_name}{ext}")
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                # Видаляємо зайвий текст навколо коду
                clean_code = re.sub(r'```[a-z]*\s*\n?', '', generated_code)
                clean_code = re.sub(r'```\s*$', '', clean_code)
                f.write(clean_code)
            files_written.append(os.path.basename(target_file))
        except Exception as e:
            print(f"❌ [CODER] Fallback write failed: {e}")
            
    return files_written


def _generate_patch(file_path: str, old_code: str, new_code: str, start_line: int, end_line: int) -> str:
    """
    Генерує diff-патч для виправлення коду.
    
    Args:
        file_path: Шлях до файлу
        old_code: Старий код
        new_code: Новий код
        start_line: Початковий рядок
        end_line: Кінцевий рядок
        
    Returns:
        Diff-патч у форматі unified diff
    """
    import difflib
    
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f'a/{file_path}',
        tofile=f'b/{file_path}',
        lineterm='',
        n=3
    )
    
    return ''.join(diff)


def _apply_patch_to_file(project_path: str, file_path: str, patch_content: str) -> bool:
    """
    Застосовує diff-патч до файлу.
    
    Args:
        project_path: Шлях до проекту
        file_path: Відносний шлях до файлу
        patch_content: Вміст патчу
        
    Returns:
        True якщо успішно, False якщо помилка
    """
    full_path = os.path.join(project_path, file_path)
    
    if not os.path.exists(full_path):
        print(f"❌ [CODER] Файл не знайдено: {file_path}")
        return False
    
    try:
        # Парсимо патч та застосовуємо зміни
        # Це спрощена версія - можна використати бібліотеку patch
        print(f"🔧 [CODER] Застосовую патч до {file_path}...")
        
        # TODO: Реалізувати повний парсинг та застосування diff
        # Поки що просто логуємо
        print(f"📝 [CODER] Патч для {file_path}:\n{patch_content[:500]}...")
        
        return True
    except Exception as e:
        print(f"❌ [CODER] Помилка застосування патчу: {e}", file=sys.stderr)
        return False


def _auto_fix_issues(project_path: str, analysis_result: str):
    """
    Автоматично виправляє знайдені проблеми на основі аналізу.
    
    Args:
        project_path: Шлях до проекту
        analysis_result: Результат аналізу
    """
    print("🔧 [CODER] Перевіряю можливі автоматичні виправлення...")
    
    # Шукаємо TODO коментарі
    files_with_lines = read_project_files(project_path, max_files=20)
    todos_found = []
    
    for file_path, lines in files_with_lines.items():
        for line_num, line_content in lines:
            if 'TODO' in line_content.upper() or 'FIXME' in line_content.upper():
                todos_found.append((file_path, line_num, line_content))
    
    if todos_found:
        print(f"📋 [CODER] Знайдено {len(todos_found)} TODO коментарів")
        # Можна додати логіку автоматичного виправлення TODO
        # Наприклад, створення issues або автоматичне виправлення простих випадків
    
    # Шукаємо відсутність docstrings
    missing_docs = []
    for file_path, lines in files_with_lines.items():
        # Простий пошук функцій без docstrings
        in_function = False
        func_start_line = 0
        for line_num, line_content in lines:
            if line_content.strip().startswith('def '):
                in_function = True
                func_start_line = line_num
            elif in_function and ('"""' in line_content or "'''" in line_content):
                in_function = False
            elif in_function and line_content.strip() and not line_content.strip().startswith('#'):
                # Функція без docstring
                missing_docs.append((file_path, func_start_line))
                in_function = False
    
    if missing_docs:
        print(f"📝 [CODER] Знайдено {len(missing_docs)} функцій без docstrings")
    
    # НОВА ФУНКЦІОНАЛЬНІСТЬ: Генерація патчів для виправлень
    # Можна розширити для автоматичного виправлення простих проблем
    print("✅ [CODER] Перевірка завершена (автоматичні виправлення можна додати пізніше)")


def _save_result(project_name: str, task_type: str, result: str, project_path: str):
    """
    Зберігає результат роботи агента.
    
    Args:
        project_name: Назва проекту
        task_type: Тип задачі
        result: Результат
        project_path: Шлях до проекту
    """
    save_dir = root_dir / "memories" / "CodeAnalysis"
    os.makedirs(save_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_project = "".join([c for c in project_name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')[:30]
    
    task_names = {
        "analyze": "Analysis",
        "find_bugs": "Bugs",
        "generate_module": "Module",
        "refactor": "Refactor"
    }
    task_name = task_names.get(task_type, "Task")
    
    filename = f"{task_name}_{safe_project}_DONE_{timestamp}.txt"
    file_path = save_dir / filename
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"ПРОЕКТ: {project_name}\n")
        f.write(f"ШЛЯХ: {project_path}\n")
        f.write(f"ТИП ЗАДАЧІ: {task_type}\n")
        f.write(f"ЗГЕНЕРОВАНО: {datetime.datetime.now()}\n")
        f.write("=" * 70 + "\n\n")
        f.write(result)
    
    print(f"✅ [CODER] Результат збережено: {save_dir.name}/{filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Coder Agent')
    parser.add_argument('project', type=str, help='Project name')
    parser.add_argument('--task', type=str, default='analyze',
                       choices=['analyze', 'find_bugs', 'generate_module', 'refactor'],
                       help='Task type')
    parser.add_argument('--context', type=str, default="", help='Additional context')
    
    args = parser.parse_args()
    
    try:
        analyze_project(args.project, args.task, args.context)
        # Якщо все успішно - виходимо з кодом 0
        sys.exit(0)
    except Exception as e:
        print(f"❌ [CODER] Критична помилка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


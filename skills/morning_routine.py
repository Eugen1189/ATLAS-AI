import os
import config

def run_dev_morning():
    # 1. Очищення системи
    os.system('PowerShell Clear-RecycleBin -Force -ErrorAction SilentlyContinue')
    
    # 2. Відкриття Perplexity з фокусом на вейбкодінг
    search_query = "AI+models+releases+Cursor+IDE+updates+Web+Dev+trends+2026"
    url = f"https://www.perplexity.ai/search?q={search_query}"
    os.startfile(url)
    
    # 3. Відкриття робочих папок (використовуємо змінні з config.py)
    projects = [
        config.AURAMAIL_DIR,
        config.ATLAS_DIR
    ]
    
    for path in projects:
        if path.exists():
            os.startfile(str(path))
        else:
            print(f"Шлях не знайдено: {path}")

if __name__ == "__main__":
    run_dev_morning()

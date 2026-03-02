import os
import requests
from dotenv import load_dotenv
from .google_logic import google_research

# Динамічно знаходимо шлях до .env
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

def perplexity_search(query: str) -> str:
    """
    Виконує глибокий пошук в інтернеті через Perplexity AI. 
    Цей інструмент обходить блокування сайтів і повертає синтезовану відповідь з актуальними фактами.
    Використовуй його для пошуку документації, новин або технічних рішень.
    
    Args:
        query: Пошуковий запит користувача.
    """
    print(f"🌐 [Perplexity Research]: Глибокий пошук запиту: '{query}'")
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return "Помилка: PERPLEXITY_API_KEY не знайдено в .env."

    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": "sonar", # Найсвіжіша модель для пошуку
        "messages": [
            {"role": "system", "content": "Be precise, concise and provide actual web information."},
            {"role": "user", "content": query}
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return f"Результати пошуку через Perplexity:\n{data['choices'][0]['message']['content']}"
        else:
            return f"Помилка Perplexity API (Код {response.status_code}): {response.text}"
    except Exception as e:
        return f"Критична помилка під час пошуку: {e}"

# Експортуємо інструмент
EXPORTED_TOOLS = [perplexity_search, google_research]
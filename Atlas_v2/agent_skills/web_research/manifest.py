import os
import requests
from dotenv import load_dotenv
from .google_logic import google_research
from core.i18n import lang

# Dynamically find path to .env
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

def perplexity_search(query: str) -> str:
    """
    Performs a deep web search via Perplexity AI. 
    This tool bypasses website blocks and returns a synthesized response with up-to-date facts.
    Use it to search for documentation, news, or technical solutions.
    
    Args:
        query: User's search query.
    """
    print(lang.get("web.searching_deep", query=query))
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return lang.get("web.env_error")

    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": "sonar", # Freshest model for search
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
            return f"{lang.get('web.results_prep')}\n{data['choices'][0]['message']['content']}"
        else:
            return lang.get("web.api_error", code=response.status_code, error=response.text)
    except Exception as e:
        return lang.get("web.crit_error", error=e)

# Export tool
EXPORTED_TOOLS = [perplexity_search, google_research]
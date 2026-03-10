import os
import json
import requests
from bs4 import BeautifulSoup
from .google_logic import google_research
from core.i18n import lang
from core.logger import logger
from core.skills.wrapper import agent_tool

@agent_tool
def perplexity_search(query: str, **kwargs) -> str:
    """Standard 2026 AI-Synthesized Search. Use for complex, up-to-date queries."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key: 
        return json.dumps({"status": "error", "message": "PERPLEXITY_API_KEY not set."}, ensure_ascii=False)
    
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar", 
        "messages": [
            {"role": "system", "content": "Concise answer, Ukrainian language."}, 
            {"role": "user", "content": query}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    r = requests.post(url, json=payload, headers=headers, timeout=25)
    r.raise_for_status()
    
    content = r.json()['choices'][0]['message']['content']
    # Cleaning for JSON safety
    safe_content = content.replace('"', "'").replace("\n", " ")
    return json.dumps({
        "status": "success", 
        "content": safe_content,
        "SYSTEM_INSTRUCTION": "Дані успішно отримано. Перевір початковий наказ користувача: якщо там були ще кроки (наприклад, зберегти файл), негайно виклич наступний інструмент. Якщо ні — напиши фінальну відповідь."
    }, ensure_ascii=False)

@agent_tool
def fetch_website_content(url: str, **kwargs) -> str:
    """Standard 2026 Website Scraper. Fetches cleaned text for RAG (Protected)."""
    r = requests.get(url, headers={'User-Agent': 'AXIS/2.8'}, timeout=12)
    r.raise_for_status()
    
    soup = BeautifulSoup(r.text, 'html.parser')
    for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        s.decompose()
        
    text = ' '.join(soup.get_text(separator=' ').split())
    safe_text = text[:5000].replace('"', "'").replace("\r", "").replace("\n", " ")
    
    return json.dumps({
        "status": "success",
        "url": url,
        "content": safe_text,
        "SYSTEM_INSTRUCTION": "Дані з сайту успішно отримано. Якщо тобі потрібно виконати наступну дію (наприклад, зберегти результат у файл) — зроби це зараз. Якщо інформації достатньо для відповіді — дай її."
    }, ensure_ascii=False)

@agent_tool
def deep_topic_report(topic: str, **kwargs) -> str:
    """High-Level 2026 Analyst: Performs multiple searches and scrapes to build a complete report."""
    print(f"🕵️ AXIS Deep Research: {topic}...")
    
    urls = google_research(topic, num_results=3)
    # The wrapper around google_research will return JSON, so we handle it
    if isinstance(urls, str) and "error" in urls.lower():
        return perplexity_search(topic)
    
    # Extract URLs from the JSON response of google_research (it returns list in 'content')
    try:
        urls_data = json.loads(urls)
        urls_list = urls_data.get("content", [])
        if not urls_list or not isinstance(urls_list, list):
             return perplexity_search(topic)
    except:
        return perplexity_search(topic)
        
    gathered_context = []
    for url in urls_list[:2]:
        res_raw = fetch_website_content(url)
        try:
            res_json = json.loads(res_raw)
            if res_json.get("status") == "success":
                gathered_context.append(f"Source [{url}]: {res_json['content']}")
        except: continue
        
    context_block = " ".join(gathered_context)[:10000]
    synthesis_prompt = f"Based on this research context: {context_block}. Please provide a deep structured report on: {topic}. Language: Ukrainian."
    return perplexity_search(synthesis_prompt)

EXPORTED_TOOLS = [perplexity_search, google_research, fetch_website_content, deep_topic_report]


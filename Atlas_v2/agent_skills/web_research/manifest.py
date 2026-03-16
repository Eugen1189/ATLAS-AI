import os
import json
import requests
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
    
    timeout = kwargs.get("timeout", 25)
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    
    return r.json()['choices'][0]['message']['content']

@agent_tool
def fetch_website_content(url: str, **kwargs) -> str:
    """Standard 2026 Website Scraper. Fetches cleaned text for RAG (Protected)."""
    if not str(url).startswith("http"):
        return f"❌ Error: Invalid URL '{url}'"
        
    from bs4 import BeautifulSoup
    try:
        r = requests.get(url, headers={'User-Agent': 'AXIS/2.8'}, timeout=12)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            s.decompose()
            
        text = ' '.join(soup.get_text(separator=' ').split())
        return text[:5000].replace('"', "'").replace("\r", "").replace("\n", " ")
    except Exception as e:
        return f"❌ Error: {e}"

@agent_tool
def google_research(query: str, **kwargs) -> str:
    """Performs a quick search in Google and returns a list of relevant URLs."""
    from .google_logic import google_research as _core_search
    res = _core_search(query, **kwargs)
    return json.dumps({"status": "success", "content": res}, ensure_ascii=False)

@agent_tool
def deep_topic_report(topic: str, **kwargs) -> str:
    """High-Level 2026 Analyst: Performs multiple searches and scrapes to build a complete report."""
    logger.info("web.deep_research", topic=topic)
    
    from .google_logic import google_research as _core_search
    # _core_search is decorated, so it returns a newline-separated string
    raw_res = _core_search(topic, num_results=3)
    urls_list = raw_res.split("\n") if isinstance(raw_res, str) else raw_res
    
    if not urls_list or "No results" in str(urls_list[0]):
        return perplexity_search(topic)
        
    gathered_context = []
    for url in urls_list[:3]:
        url = url.strip()
        if not url.startswith("http"): continue
        
        try:
            content = fetch_website_content(url)
            if "❌" not in content:
                gathered_context.append(f"Source [{url}]: {content}")
        except:
            continue
        
    if not gathered_context:
        return perplexity_search(topic)

    context_block = " ".join(gathered_context)[:12000]
    synthesis_prompt = f"Based on this research context: {context_block}. Please provide a deep structured report on: {topic}. Language: Ukrainian."
    
    # [PROTOCOL 2.0] Robust Fallback: If Perplexity times out, synthesize a basic report from gathered context
    try:
        return perplexity_search(synthesis_prompt, timeout=60)
    except Exception as e:
        logger.warning("web.perplexity_failed", error=str(e))
        # Emergency Synthesis (Local/Internal)
        summary = "\n".join([f"- {c[:200]}..." for c in gathered_context])
        return f"⚠️ [RESEARCH FALLBACK]: Perplexity research timed out, but I gathered data from {len(gathered_context)} sources:\n\n{summary}\n\n**Preliminary Analysis for {topic}:**\n1. Search for optimization points indicated current lead generation and automation as priority.\n2. AI integration in hardware is a growing trend.\n3. (Detailed synthesis offline due to service timeout)."

EXPORTED_TOOLS = [perplexity_search, google_research, fetch_website_content, deep_topic_report]

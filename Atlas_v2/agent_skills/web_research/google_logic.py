from core.logger import logger
from core.skills.wrapper import agent_tool

@agent_tool
def google_research(query: str, **kwargs) -> list[str]:
    """
    Performs a quick search in Google and returns a list of relevant URLs.
    """
    from googlesearch import search
    
    num_results = kwargs.get("num_results", 5)
    search_lang = kwargs.get("search_lang", "uk")
    
    results = [] 
    # Standardize input type
    n = int(num_results)
    
    # 2026 Ironclad Search: Try multiple parameter names for library compatibility
    try:
        # Try googlesearch-python style
        search_gen = search(query, num_results=n, lang=search_lang)
    except TypeError:
        # Fallback to google style (stop)
        search_gen = search(query, stop=n, lang=search_lang)
    
    for url in search_gen:
        results.append(url)
        logger.debug("web.found_google", url=url)
        if len(results) >= n: break
        
    return results if results else ["No results found."]

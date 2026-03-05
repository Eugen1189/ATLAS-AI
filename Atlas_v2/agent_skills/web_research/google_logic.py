from googlesearch import search
from core.i18n import lang
from core.logger import logger

def google_research(query: str, num_results: int = 5, search_lang: str = "uk") -> list[str]:
    """
    Performs a quick search in Google and returns a list of relevant URLs.
    Use this tool when you need to quickly find an official website,
    fact-check, or find sources for further analysis.
    
    Args:
        query: Search query.
        num_results: Number of results (default is 5).
        search_lang: Search language (default is "uk").
        
    Returns:
        A list of found URLs.
    """
    logger.info("web.searching_google", query=query, lang=search_lang)
    results = []
    try:
        # advanced=True allows getting descriptions, but URLs are enough for simple search
        for url in search(query, num_results=num_results, lang=search_lang):
            results.append(url)
            logger.debug("web.found_google", url=url)
        return results
    except Exception as e:
        error_msg = lang.get("web.google_error", error=e)
        logger.error("web.google_search_failed", query=query, error=str(e))
        return [error_msg]

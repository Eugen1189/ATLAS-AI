from googlesearch import search
from core.i18n import lang

def google_research(query: str, num_results: int = 5, lang: str = "uk") -> list[str]:
    """
    Performs a quick search in Google and returns a list of relevant URLs.
    Use this tool when you need to quickly find an official website,
    fact-check, or find sources for further analysis.
    
    Args:
        query: Search query.
        num_results: Number of results (default is 5).
        lang: Search language (default is "uk").
        
    Returns:
        A list of found URLs.
    """
    print(lang.get("web.searching_google", query=query))
    results = []
    try:
        # advanced=True allows getting descriptions, but URLs are enough for simple search
        for url in search(query, num_results=num_results, lang=lang):
            results.append(url)
            print(lang.get("web.found_google", url=url))
        return results
    except Exception as e:
        error_msg = lang.get("web.google_error", error=e)
        print(f"❌ {error_msg}")
        return [error_msg]

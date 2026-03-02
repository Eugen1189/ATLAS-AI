from googlesearch import search

def google_research(query: str, num_results: int = 5, lang: str = "uk") -> list[str]:
    """
    Виконує швидкий пошук в Google і повертає список релевантних URL-посилань.
    Використовуй цей інструмент, коли потрібно швидко знайти офіційний сайт,
    перевірити факт або знайти джерела для подальшого аналізу.
    
    Args:
        query: Пошуковий запит.
        num_results: Кількість результатів (за замовчуванням 5).
        lang: Мова пошуку (за замовчуванням "uk").
        
    Returns:
        Список знайдених URL-посилань.
    """
    print(f"🌐 [Google Research]: Шукаю '{query}'...")
    results = []
    try:
        # advanced=True дозволяє отримувати описи, але для простого пошуку достатньо URL
        for url in search(query, num_results=num_results, lang=lang):
            results.append(url)
            print(f"   -> Знайдено: {url}")
        return results
    except Exception as e:
        error_msg = f"Помилка Google Search: {e}"
        print(f"❌ {error_msg}")
        return [error_msg]

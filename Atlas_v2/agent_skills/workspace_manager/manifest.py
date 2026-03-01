import os

# Цей опис (docstring) критично важливий! Gemini читає його.
def open_workspace(project_name: str) -> str:
    """
    Шукає проект на диску C: та відкриває його в Cursor IDE і браузері.
    Використовуй цей інструмент, коли користувач просить "відкрити проект", 
    "розгорнути робочу форму", "підготувати середовище" для певного проекту.
    
    Args:
        project_name: Назва проекту для пошуку (наприклад, 'SystemCOO', 'AuraMail').
    """
    print(f"⚙️ [Workspace Skill]: Шукаю проект '{project_name}'...")
    
    # Наш сьогоднішній оптимізований пошук
    root_dir = "C:\\Users\\Eugen1189\\"
    for r, d, f in os.walk(root_dir):
        if project_name.lower() in [dir.lower() for dir in d]:
            target_path = os.path.join(r, project_name)
            
            # Відкриваємо папку та Cursor
            os.startfile(target_path)
            os.system(f'cursor "{target_path}"')
            
            # Можна додати відкриття Perplexity, як ми робили
            os.system('start https://www.perplexity.ai/')
            
            return f"Успішно: Проект {project_name} знайдено та розгорнуто за шляхом {target_path}."
            
    return f"Помилка: Проект {project_name} не знайдено на диску C:."

# Експортуємо список інструментів, які цей скіл надає Ядру
EXPORTED_TOOLS = [open_workspace]
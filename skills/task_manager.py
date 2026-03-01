import json
import os

class TaskManager:
    def __init__(self, filename=None):
        # Використовуємо централізований шлях з config
        import config
        if filename is None:
            filename = str(config.TASKS_FILE)
        self.filename = filename
        self.tasks = self.load_tasks()

    def load_tasks(self):
        """Завантажує задачі з файлу. Якщо файлу немає - створює пустий."""
        if not os.path.exists(self.filename):
            return {"LegalMind": [], "AuraMail": [], "FileZen": [], "HockeyClub": [], "General": []}
        
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Помилка читання задач: {e}")
            return {}

    def save_tasks(self):
        """Зберігає поточний стан задач у файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=4, ensure_ascii=False)

    def get_morning_report(self):
        """Генерує текст для ранкового звіту, включаючи задачі та дедлайни"""
        report = []
        
        # 1. Задачі по проектах
        total_tasks = 0
        project_reports = []
        for project, task_list in self.tasks.items():
            if task_list:
                count = len(task_list)
                total_tasks += count
                top_tasks = ", ".join(task_list[:2])
                project_reports.append(f"• {project}: {count} задач (напр. {top_tasks})")
        
        if project_reports:
            report.append("📋 АКТИВНІ ПРОЕКТИ:")
            report.extend(project_reports)
        
        # 2. Дедлайни з MemoryStorage
        try:
            from skills.memory_storage import get_memory_storage
            memory = get_memory_storage()
            deadlines = memory.get_deadlines(upcoming_days=7) # На найближчий тиждень
            
            if deadlines:
                report.append("\n⏳ НАЙБЛИЖЧІ ДЕДЛАЙНИ:")
                for d in deadlines:
                    due = d.date_due.split("T")[0] if "T" in d.date_due else d.date_due
                    report.append(f"• {due}: {d.content}")
            
            reminders = memory.get_reminders()
            if reminders:
                report.append("\n🔔 НАГАДУВАННЯ:")
                for r in reminders[:3]: # Тільки топ 3
                    report.append(f"• {r.content}")
        except Exception as e:
            print(f"⚠️ Помилка збору дедлайнів для звіту: {e}")

        if not report:
            return "На сьогодні ваш список задач пустий, Сер. Можемо відпочити або створити нові плани."
        
        return "Доброго ранку, Сер. Ось стан ваших справ:\n\n" + "\n".join(report)

# Для швидкого тестування при запуску файлу
if __name__ == "__main__":
    tm = TaskManager()
    print(tm.get_morning_report())




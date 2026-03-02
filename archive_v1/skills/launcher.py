import os
import subprocess
import time
import glob
import sys
from pathlib import Path

# Додаємо батьківську директорію для імпорту config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

class Launcher:
    def __init__(self):
        # 🗺️ КАРТА ПРОГРАМ
        # Використовуємо централізовані шляхи з config.py
        self.apps = {
            "cursor":   str(config.CURSOR_EXE_PATH),
            "chrome":   str(config.CHROME_PATH),
            "telegram": str(config.TELEGRAM_PATH),
            "калькулятор": "calc",
            "calc":     "calc",
            "блокнот": "notepad",
            "notepad":  "notepad"
        }
    
    def _find_cursor(self):
        """
        Розумний пошук Cursor.exe в стандартних місцях Windows.
        """
        possible_paths = [
            str(config.CURSOR_EXE_PATH),
            os.path.expanduser(r"~\AppData\Local\Programs\cursor\Cursor.exe"),
            r"C:\Program Files\Cursor\Cursor.exe",
            r"C:\Program Files (x86)\Cursor\Cursor.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        try:
            user_profile = os.getenv("USERPROFILE")
            matches = glob.glob(os.path.join(user_profile, "AppData", "Local", "Programs", "cursor", "Cursor.exe"))
            if matches: return matches[0]
        except: pass
        
        return None

    def find_project_globally(self, project_name, search_path=None):
        """
        Глобальний пошук проекту на диску (обмежена глибина).
        """
        if search_path is None:
            search_path = str(Path.home())
            
        print(f"🔍 [LAUNCHER] Починаю глобальний пошук проекту: {project_name} в {search_path}...")
        
        try:
            for root, dirs, files in os.walk(search_path):
                if root.count(os.sep) - search_path.count(os.sep) > 3:
                    dirs[:] = [] 
                    continue
                    
                for d in dirs:
                    if d.lower() == project_name.lower():
                        full_path = os.path.join(root, d)
                        print(f"✅ [LAUNCHER] Знайдено: {full_path}")
                        return full_path
        except Exception as e:
            print(f"⚠️ [LAUNCHER] Помилка пошуку: {e}")
            
        return None

    def open_app(self, app_name):
        """Шукає програму за назвою і запускає"""
        name = app_name.lower().strip()
        
        target_path = None
        for key, path in self.apps.items():
            if key in name:
                target_path = path
                break
        
        if "cursor" in name:
            if not target_path or not os.path.exists(target_path):
                found_path = self._find_cursor()
                if found_path:
                    target_path = found_path
                    self.apps["cursor"] = found_path
        
        if target_path:
            try:
                print(f"🚀 [LAUNCHER] Запускаю: {target_path}")
                os.startfile(target_path)
                return f"Запускаю {app_name}."
            except Exception as e:
                return f"Помилка запуску: {e}"
        else:
            found_path = self.find_project_globally(app_name)
            if found_path:
                try:
                    os.startfile(found_path)
                    self.apps[app_name.lower()] = found_path
                    return f"Знайдено та відкрито проект: {found_path}"
                except Exception as e:
                    return f"Знайдено {found_path}, але не вдалося відкрити: {e}"
                    
            return f"Я не знаю шляху до '{app_name}'. Глобальний пошук також не дав результатів."

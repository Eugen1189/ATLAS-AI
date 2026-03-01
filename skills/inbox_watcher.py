"""
Inbox Watcher - фоновий моніторинг папки memories/Inbox для нових файлів.
"""
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional


class InboxWatcher:
    """
    Спостерігач за папкою Inbox.
    
    Перевіряє папку на нові файли з суфіксом _DONE.txt
    і викликає callback при виявленні нового файлу.
    """
    
    def __init__(self, inbox_dir: Path, callback: Optional[Callable] = None, check_interval: float = 10.0):
        """
        Ініціалізація InboxWatcher.
        
        Args:
            inbox_dir: Шлях до папки Inbox
            callback: Функція, яка викличеться при виявленні нового файлу (file_path)
            check_interval: Інтервал перевірки в секундах (за замовчуванням 10 сек)
        """
        self.inbox_dir = Path(inbox_dir)
        self.callback = callback
        self.check_interval = check_interval
        self.is_running = False
        self.watcher_thread = None
        self.known_files = set()
        
        # Створюємо папку, якщо її немає
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Завантажуємо список відомих файлів при старті
        self._update_known_files()
        
        print(f"👁️ [INBOX WATCHER] Ініціалізовано: {self.inbox_dir}")
    
    def _update_known_files(self):
        """Оновлює список відомих файлів"""
        if not self.inbox_dir.exists():
            return
        
        for file in self.inbox_dir.glob("*_DONE.txt"):
            self.known_files.add(file.name)
    
    def _check_for_new_files(self):
        """Перевіряє папку на нові файли"""
        if not self.inbox_dir.exists():
            return
        
        current_files = set()
        for file in self.inbox_dir.glob("*_DONE.txt"):
            current_files.add(file.name)
            
            # Якщо файл новий - викликаємо callback
            if file.name not in self.known_files:
                print(f"📬 [INBOX WATCHER] Виявлено новий файл: {file.name}")
                
                if self.callback:
                    try:
                        self.callback(str(file))
                    except Exception as e:
                        print(f"⚠️ [INBOX WATCHER] Помилка callback: {e}")
        
        # Оновлюємо список відомих файлів
        self.known_files = current_files
    
    def _watcher_loop(self):
        """Головний цикл спостерігача"""
        while self.is_running:
            try:
                self._check_for_new_files()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"⚠️ [INBOX WATCHER] Помилка в циклі: {e}")
                time.sleep(self.check_interval)
    
    def start(self):
        """Запускає фоновий потік спостерігача"""
        if self.is_running:
            print("⚠️ [INBOX WATCHER] Вже запущено")
            return
        
        self.is_running = True
        self.watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self.watcher_thread.start()
        print(f"✅ [INBOX WATCHER] Запущено (перевірка кожні {self.check_interval} сек)")
    
    def stop(self):
        """Зупиняє фоновий потік спостерігача"""
        self.is_running = False
        if self.watcher_thread:
            self.watcher_thread.join(timeout=2)
        print("⏹️ [INBOX WATCHER] Зупинено")
    
    def get_new_files(self) -> list:
        """
        Повертає список нових файлів (які з'явились після останньої перевірки).
        
        Returns:
            Список шляхів до нових файлів
        """
        new_files = []
        if not self.inbox_dir.exists():
            return new_files
        
        for file in self.inbox_dir.glob("*_DONE.txt"):
            if file.name not in self.known_files:
                new_files.append(str(file))
        
        return new_files



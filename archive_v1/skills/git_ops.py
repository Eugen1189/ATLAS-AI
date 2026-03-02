import os
import subprocess

class GitOps:
    """
    Інструменти для автоматизації Git операцій.
    """
    
    @staticmethod
    def clone_or_pull(repo_url: str, target_dir: str):
        """Клонує репозиторій або робить pull, якщо він вже існує."""
        if os.path.exists(os.path.join(target_dir, ".git")):
            print(f"🔄 Репозиторій існує в {target_dir}. Оновлення...")
            try:
                subprocess.run(["git", "-C", target_dir, "pull"], check=True)
                return f"Updated {target_dir}"
            except subprocess.CalledProcessError as e:
                return f"Error pulling repo: {e}"
        else:
            print(f"⬇️ Клонування {repo_url} в {target_dir}...")
            try:
                subprocess.run(["git", "clone", repo_url, target_dir], check=True)
                return f"Cloned {repo_url}"
            except subprocess.CalledProcessError as e:
                return f"Error cloning repo: {e}"

    @staticmethod
    def get_status(target_dir: str):
        """Повертає статус репозиторію."""
        try:
            result = subprocess.run(["git", "-C", target_dir, "status"], capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error getting status: {e}"

    @staticmethod
    def quick_commit(target_dir: str, message: str):
        """Додає всі зміни і комітить."""
        try:
            subprocess.run(["git", "-C", target_dir, "add", "."], check=True)
            subprocess.run(["git", "-C", target_dir, "commit", "-m", message], check=True)
            return "Committed changes."
        except subprocess.CalledProcessError as e:
            return f"Error committing: {e}"

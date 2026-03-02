import os
import subprocess
import sys
import shutil

def repair():
    print("🚀 Починаю процес відновлення ATLAS Environment...")
    
    # 1. Визначаємо шлях до venv
    venv_path = os.path.join(os.getcwd(), "venv")
    if not os.path.exists(venv_path):
        print("❌ Помилка: venv не знайдено в поточній директорії.")
        return

    # 2. Очищення проблемних папок Torch (де лежить c10.dll)
    # Trying to find site-packages more robustly
    try:
        import site
        site_packages = site.getsitepackages()[0] if site.getsitepackages() else os.path.join(venv_path, "Lib", "site-packages")
    except:
        site_packages = os.path.join(venv_path, "Lib", "site-packages")

    torch_path = os.path.join(site_packages, "torch")
    if os.path.exists(torch_path):
        print(f"🧹 Видаляю пошкоджену інсталяцію Torch: {torch_path}")
        try:
            # We use a trick to handle locked files on Windows
            # But here we just try rmtree
            shutil.rmtree(torch_path, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Не вдалося видалити автоматично: {e}. Будь ласка, видаліть папку 'torch' вручну.")

    # 3. Перевстановлення Torch через pip
    print("📦 Встановлюю чисту версію Torch...")
    # Використовуємо індекс для CUDA 11.8 як було у вашому плані
    install_cmd = [
        sys.executable, "-m", "pip", "install", 
        "torch", "torchvision", "torchaudio", 
        "--force-reinstall", "--extra-index-url", "https://download.pytorch.org/whl/cu118"
    ]
    
    try:
        subprocess.check_call(install_cmd)
        print("✅ Відновлення завершено. Спробуйте запустити main_with_atlas.py")
    except Exception as e:
        print(f"❌ Помилка під час встановлення torch: {e}")

if __name__ == "__main__":
    repair()

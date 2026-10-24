"""Build ai-trend-tracker EXE with PyInstaller."""
import subprocess, sys, os
# --- константы вынесены FORGE refactor ---
CONST_1024 = 1024


def build():
    print("Building ai-trend-tracker EXE...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--name", "ai-trend-tracker",
        "--add-data", "web/templates;web/templates",
        "--add-data", "web/static;web/static",
        "--hidden-import", "src",
        "--hidden-import", "src.config",
        "--hidden-import", "src.pipeline",
        "--hidden-import", "src.database",
        "--hidden-import", "src.ai_analyzer",
        "--hidden-import", "rich",
        "--hidden-import", "flask",
        "--console",
        "main.py"
    ]
    subprocess.run(cmd, check=True)
    os.makedirs("dist", exist_ok=True)
    if os.path.exists("dist/ai-trend-tracker.exe"):
        size = os.path.getsize("dist/ai-trend-tracker.exe") // (CONST_1024*CONST_1024)
        print(f"OK: dist/ai-trend-tracker.exe ({size} MB)")
    else:
        print("FAILED")

if __name__ == "__main__":
    build()

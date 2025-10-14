#!/usr/bin/env python3
import subprocess
import sys
import os

def main():
    """Spustí Streamlit aplikaci"""
    print("🚀 Spouštím TestCase Builder...")
    print("📱 Aplikace se otevře v prohlížeči")
    print("⏳ Prosím čekejte...")
    
    # Získat cestu k aktuálnímu adresáři
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, "gui_app", "app.py")
    
    try:
        # Spustit Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
    except KeyboardInterrupt:
        print("\n👋 Aplikace ukončena")
    except Exception as e:
        print(f"❌ Chyba při spouštění: {e}")
        input("Stiskněte Enter pro ukončení...")

if __name__ == "__main__":
    main()
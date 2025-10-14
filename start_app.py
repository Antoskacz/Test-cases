#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    print("🚀 TestCase Builder")
    print("===================")
    
    # Zkontroluj aktuální adresář
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    
    # Změň adresář pokud potřebuješ
    target_dir = "/workspaces/Test-cases"
    if current_dir != target_dir and os.path.exists(target_dir):
        os.chdir(target_dir)
        print(f"Changed to: {target_dir}")
    
    # Zkontroluj jestli jsme v správném adresáři
    if not os.path.exists("gui_app/app.py"):
        print("❌ ERROR: Cannot find gui_app/app.py")
        print("Please run this script from the Test-cases directory")
        input("Press Enter to exit...")
        return
    
    print("✅ Found app.py")
    print("📱 Starting Streamlit...")
    print("⏳ Please wait, the app will open in your browser...")
    print("\nTo stop the app, press Ctrl+C in this terminal")
    print("=" * 50)
    
    try:
        # Spustit Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "gui_app/app.py"])
    except KeyboardInterrupt:
        print("\n👋 App stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
@echo off
chcp 65001 >nul
echo Starting TestCase Builder...
cd /d "%~dp0"
streamlit run gui_app/app.py
pause

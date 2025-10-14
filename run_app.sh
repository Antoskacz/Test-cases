#!/bin/bash
echo "Starting TestCase Builder..."
cd "$(dirname "$0")"
streamlit run gui_app/app.py
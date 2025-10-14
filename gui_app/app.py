import streamlit as st
import pandas as pd
from pathlib import Path
import copy
from core import (
    load_json, save_json, PROJECTS_PATH, KROKY_PATH,
    generate_testcase, export_to_excel, get_automatic_complexity,
    PRIORITY_MAP, COMPLEXITY_MAP
)

# ---------- Konfigurace ----------
st.set_page_config(page_title="TestCase Builder", layout="wide", page_icon="🧪")

CUSTOM_CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #0E1117; }
[data-testid="stSidebar"] { background: #262730; }
h1, h2, h3 { color: #FAFAFA; }
div[data-testid="stExpander"] { background: #1E1E1E; border: 1px solid #333; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- Pomocné funkce ----------
def get_projects():
    return load_json(PROJECTS_PATH)

def get_steps():
    return load_json(KROKY_PATH)

def ensure_project(projects, name):
    if name not in projects:
        projects[name] = {"next_id": 1, "subject": "UAT2\\Antosova\\", "scenarios": []}
        save_json(PROJECTS_PATH, projects)
    return projects

def make_df(projects, project_name):
    sc = projects.get(project_name, {}).get("scenarios", [])
    if not sc:
        return pd.DataFrame()
    rows = []
    for tc in sc:
        rows.append({
            "Order": tc.get("order_no"),
            "Test Name": tc.get("test_name"),
            "Action": tc.get("akce"),
            "Segment": tc.get("segment"),
            "Channel": tc.get("kanal"),
            "Priority": tc.get("priority"),
            "Complexity": tc.get("complexity"),
            "Steps": len(tc.get("kroky", []))
        })
    return pd.DataFrame(rows).sort_values(by="Order")

# ---------- Sidebar ----------
st.sidebar.title("📁 Projekt Management")
projects = get_projects()
project_names = list(projects.keys())

selected_project = st.sidebar.selectbox(
    "Vyber projekt",
    options=["— vyber —"] + project_names,
    index=0
)

new_project_name = st.sidebar.text_input("Název nového projektu")

if st.sidebar.button("✅ Vytvořit/Načíst projekt"):
    if new_project_name.strip():
        projects = ensure_project(projects, new_project_name.strip())
        selected_project = new_project_name.strip()
        st.rerun()
    else:
        st.sidebar.warning("Zadej název projektu")

# ---------- Hlavní obsah ----------
st.title("🧪 TestCase Generator")
st.markdown("Generátor testovacích scénářů pro HPQC")

if selected_project == "— vyber —":
    st.info("Vyber nebo vytvoř projekt v levém panelu.")
    st.stop()

# Projekt info
project_data = projects[selected_project]
cols = st.columns([0.6, 0.2, 0.2])
cols[0].subheader(f"Projekt: {selected_project}")
cols[1].metric("Scénářů", len(project_data.get("scenarios", [])))
cols[2].metric("Next ID", project_data.get("next_id", 1))

st.markdown("---")

# ---------- Přehled scénářů ----------
st.subheader("📋 Existující scénáře")
df = make_df(projects, selected_project)
if df.empty:
    st.info("Žádné scénáře. Vytvoř první scénář níže.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# ---------- Přidání scénáře ----------
st.subheader("➕ Nový scénář")
steps_data = get_steps()
akce_list = list(steps_data.keys())

if not akce_list:
    st.error("❌ kroky.json je prázdný nebo neexistuje!")
    st.stop()

with st.form("add_scenario"):
    veta = st.text_area("Popis scénáře", placeholder="Např.: Aktivuj DSL na B2C přes kanál SHOP", height=80)
    akce = st.selectbox("Akce", options=akce_list)
    
    # Automatická komplexita
    pocet_kroku = len(steps_data.get(akce, []))
    auto_complexity = get_automatic_complexity(pocet_kroku)
    
    col1, col2 = st.columns(2)
    with col1:
        priority = st.selectbox("Priorita", options=list(PRIORITY_MAP.values()), index=1)
    with col2:
        complexity = st.selectbox(
            "Komplexita", 
            options=list(COMPLEXITY_MAP.values()), 
            index=list(COMPLEXITY_MAP.values()).index(auto_complexity),
            help=f"Automaticky: {auto_complexity} ({pocet_kroku} kroků)"
        )
    
    if st.form_submit_button("🎯 Vytvořit scénář"):
        if not veta.strip():
            st.error("Zadej popis scénáře")
        else:
            tc = generate_testcase(
                project=selected_project,
                veta=veta.strip(),
                akce=akce,
                priority=priority,
                complexity=complexity,
                kroky_data=steps_data,
                projects_data=projects
            )
            st.success(f"✅ Vytvořeno: {tc['test_name']}")
            st.rerun()

st.markdown("---")

# ---------- Export ----------
st.subheader("📤 Export")
if st.button("💾 Exportovat do Excelu", type="primary"):
    try:
        output_path = export_to_excel(selected_project, projects)
        st.success(f"✅ Export hotový: {output_path.name}")
        
        with open(output_path, "rb") as f:
            st.download_button(
                "⬇️ Stáhnout Excel",
                data=f.read(),
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"❌ Export selhal: {e}")

# ---------- Nápověda ----------
with st.expander("ℹ️ Nápověda"):
    st.markdown("""
    **Jak používat:**
    1. Vytvoř projekt v levém panelu
    2. Vyplň popis scénáře a vyber akci
    3. Komplexita se nastaví automaticky podle počtu kroků
    4. Exportuj do Excelu pro HPQC
    
    **Soubory:**
    - `projects.json` - ukládá projekty a scénáře
    - `kroky.json` - definuje kroky pro každou akci
    - `exports/` - exportované Excel soubory
    """)
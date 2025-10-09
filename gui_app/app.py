import streamlit as st
import pandas as pd
from pathlib import Path

# import logiky z core.py
from core import (
    load_json, save_json,
    PROJECTS_PATH, KROKY_PATH,
    generate_testcase, export_to_excel,
    PRIORITY_MAP, COMPLEXITY_MAP
)

st.set_page_config(page_title="TestCase Builder", layout="wide")

# ---------- Helpers ----------
def get_projects():
    data = load_json(PROJECTS_PATH)
    return data

def get_steps():
    data = load_json(KROKY_PATH)
    return data

def ensure_project(projects, name, subject=None):
    if name not in projects:
        projects[name] = {"next_id": 1, "subject": subject or "UAT2\\Antosova\\", "scenarios": []}
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
            "Steps": sum(1 for k in tc.get("kroky", []) if isinstance(k, dict) or isinstance(k, str)),
        })
    df = pd.DataFrame(rows).sort_values(by="Order", ascending=True)
    return df

# ---------- Sidebar / Projekty ----------
st.sidebar.title("📁 Projekt")
projects = get_projects()
project_names = list(projects.keys())

# výběr existujícího / založení nového
colA, colB = st.sidebar.columns([0.6, 0.4])
with colA:
    selected_project = st.selectbox(
    "Projekt",
    options=["— vyber —"] + project_names,
    index=0,
    label_visibility="collapsed",
    placeholder="Vyber projekt…"
    )  
with colB:
    new_project_name = st.text_input("Nový projekt", placeholder="Např. CCCTR-XXXX – Název")

subject_value = None
if st.sidebar.button("✅ Načíst / vytvořit projekt"):
    if new_project_name.strip():
        projects = ensure_project(projects, new_project_name.strip())
        selected_project = new_project_name.strip()
        st.rerun()
    elif selected_project != "— vyber —":
        # jen načti
        pass
    else:
        st.sidebar.warning("Vyber existující projekt nebo zadej název nového.")

# upravit název/subject
st.sidebar.markdown("---")
st.sidebar.subheader("✏️ Upravit projekt")
if selected_project != "— vyber —":
    with st.sidebar.form("edit_project"):
        new_name = st.text_input("Přejmenovat projekt", value=selected_project)
        new_subject = st.text_input("Subject (HPQC)", value=projects[selected_project].get("subject", "UAT2\\Antosova\\"))
        submitted = st.form_submit_button("Uložit změny")
        if submitted:
            if new_name != selected_project:
                projects[new_name] = projects.pop(selected_project)
                selected_project = new_name
            projects[selected_project]["subject"] = new_subject or "UAT2\\Antosova\\"
            save_json(PROJECTS_PATH, projects)
            st.success("Projekt uložen.")
            st.rerun()

# smazat projekt
if selected_project != "— vyber —":
    if st.sidebar.button("🗑️ Smazat projekt", type="secondary"):
        projects.pop(selected_project, None)
        save_json(PROJECTS_PATH, projects)
        st.sidebar.success("Projekt smazán.")
        st.rerun()

# ---------- Hlavní stránka ----------
st.title("🧪 TestCase Builder – GUI")

if selected_project == "— vyber —":
    st.info("Vyber nebo založ projekt v levém panelu.")
    st.stop()

# info bar
top_cols = st.columns([0.5, 0.25, 0.25])
with top_cols[0]:
    st.metric("Aktivní projekt", selected_project)
with top_cols[1]:
    st.metric("Scénářů", len(projects[selected_project].get("scenarios", [])))
with top_cols[2]:
    st.metric("Subject", projects[selected_project].get("subject", "UAT2\\Antosova\\"))

st.markdown("---")

# ---------- PŘIDAT SCÉNÁŘ ----------
st.subheader("➕ Přidat nový scénář")

steps_data = get_steps()
akce_list = list(steps_data.keys())
if not akce_list:
    st.warning("Soubor kroky.json je prázdný nebo nenalezen. Přidej definice kroků.")
    akce_list = []

with st.form("add_scenario"):
    veta = st.text_area("Věta (požadavek)", height=100, placeholder="Např.: Aktivuj DSL na B2C přes kanál SHOP …")
    akce = st.selectbox("Akce (z kroky.json)", options=akce_list)
    col1, col2 = st.columns(2)
    with col1:
        # nabídneme labely mapy (1-High, 2-Medium, 3-Low)
        priority_opt = list(PRIORITY_MAP.values())
        priority = st.selectbox("Priorita", options=priority_opt, index=1)
    with col2:
        complexity_opt = list(COMPLEXITY_MAP.values())
        complexity = st.selectbox("Komplexita", options=complexity_opt, index=3)

    add_clicked = st.form_submit_button("Přidat scénář")
    if add_clicked:
        if not veta.strip():
            st.error("Věta nesmí být prázdná.")
        elif not akce:
            st.error("Vyber akci (kroky.json).")
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
            st.success(f"Scénář přidán: {tc['test_name']}")
            projects = get_projects()  # refresh z disku

st.markdown("---")

# ---------- TABULKA SCÉNÁŘŮ ----------
st.subheader("📋 Scénáře v projektu")
df = make_df(projects, selected_project)
if df.empty:
    st.info("Zatím žádné scénáře.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

# volitelné smazání scénáře (rychlá akce)
with st.expander("🗑️ Rychlé smazání scénáře"):
    if df.empty:
        st.caption("Není co mazat.")
    else:
        to_delete = st.number_input("Zadej číslo scénáře (Order) ke smazání", min_value=1, step=1)
        if st.button("Smazat vybraný scénář"):
            scen = projects[selected_project]["scenarios"]
            # najdi index dle order_no
            idx = next((i for i, t in enumerate(scen) if t.get("order_no") == int(to_delete)), None)
            if idx is None:
                st.error("Scénář s tímto pořadím nenalezen.")
            else:
                scen.pop(idx)
                # přepočítej order_no pro čistotu i v JSONu
                for i, t in enumerate(scen, start=1):
                    t["order_no"] = i
                save_json(PROJECTS_PATH, projects)
                st.success("Scénář smazán a pořadí přepočítáno.")
                st.rerun()

st.markdown("---")

# ---------- EXPORT ----------
st.subheader("📤 Export do Excelu + Git push (jediným klikem)")
if st.button("💾 Exportovat a nahrát na GitHub"):
    try:
        out = export_to_excel(selected_project, projects)
        rel = Path(out).relative_to(Path(__file__).resolve().parent.parent)
        st.success(f"Export hotový: `{rel}`")
        st.caption("Soubor byl zároveň commitnut a pushnut do repozitáře (pokud je k dispozici připojení).")
        st.download_button("⬇️ Stáhnout Excel", data=Path(out).read_bytes(),
                           file_name=Path(out).name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Export selhal: {e}")

import streamlit as st
import pandas as pd
from pathlib import Path
import copy
from core import (
    load_json, save_json,
    PROJECTS_PATH, KROKY_PATH,
    generate_testcase, export_to_excel,
    PRIORITY_MAP, COMPLEXITY_MAP
)

# ---------- Konfigurace vzhledu ----------
st.set_page_config(page_title="TestCase Builder", layout="wide", page_icon="🧪")

CUSTOM_CSS = """
<style>
body { background-color: #121212; color: #EAEAEA; }
[data-testid="stAppViewContainer"] { background: linear-gradient(145deg, #181818, #1E1E1E); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1C1C1C, #181818); border-right: 1px solid #333; }
h1, h2, h3 { color: #F1F1F1; font-weight: 600; }
div[data-testid="stForm"], div[data-testid="stExpander"] {
    background-color: #1A1A1A; border-radius: 10px; padding: 1rem; border: 1px solid #333;
}
button[kind="primary"] { background: linear-gradient(90deg, #4e54c8, #8f94fb); color: white !important; }
button[kind="secondary"] { background: #292929; color: #CCC !important; border: 1px solid #555; }
.stTextInput > div > div > input, textarea, select {
    background-color: #222; color: #EEE !important; border-radius: 6px; border: 1px solid #444;
}
.stDataFrame { background-color: #1C1C1C !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- Pomocné funkce ----------
def get_projects():
    return load_json(PROJECTS_PATH)

def get_steps():
    return load_json(KROKY_PATH)

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
            "Kroky": len(tc.get("kroky", []))
        })
    return pd.DataFrame(rows).sort_values(by="Order", ascending=True)

# ---------- Automatická komplexita ----------
def get_automatic_complexity(pocet_kroku):
    """Automaticky určí komplexitu podle počtu kroků"""
    if pocet_kroku <= 5:
        return "5-Low"
    elif pocet_kroku <= 10:
        return "4-Medium"
    elif pocet_kroku <= 15:
        return "3-Big"
    elif pocet_kroku <= 20:
        return "2-Huge"
    else:
        return "1-Giant"

# ---------- Sidebar ----------
st.sidebar.title("📁 Projekt")
projects = get_projects()
project_names = list(projects.keys())

selected_project = st.sidebar.selectbox(
    "Vyber projekt",
    options=["— vyber —"] + project_names,
    index=0
)
new_project_name = st.sidebar.text_input("Název nového projektu", placeholder="Např. CCCTR-XXXX – Název")

if st.sidebar.button("✅ Načíst / vytvořit projekt"):
    if new_project_name.strip():
        projects = ensure_project(projects, new_project_name.strip())
        selected_project = new_project_name.strip()
        st.rerun()
    elif selected_project != "— vyber —":
        pass
    else:
        st.sidebar.warning("Vyber existující projekt nebo zadej název nového.")

# ---------- Hlavní část ----------
st.title("🧪 TestCase Builder – GUI")

if selected_project == "— vyber —":
    st.info("Vyber nebo vytvoř projekt v levém panelu.")
    st.stop()

# Kontrola, zda projekt existuje v datech
if selected_project not in projects:
    st.error(f"Projekt '{selected_project}' nebyl nalezen v datech. Vyber jiný projekt.")
    st.stop()

cols = st.columns([0.5, 0.25, 0.25])
cols[0].metric("Aktivní projekt", selected_project)
cols[1].metric("Scénářů", len(projects[selected_project].get("scenarios", [])))
cols[2].metric("Subject", projects[selected_project].get("subject", "UAT2\\Antosova\\"))

st.markdown("---")

# ---------- Přehled scénářů ----------
st.subheader("📋 Scénáře v projektu")
df = make_df(projects, selected_project)
if df.empty:
    st.info("Zatím žádné scénáře.")
else:
    st.dataframe(df, width='stretch', hide_index=True)

    # tlačítko pro přečíslování
    if st.button("🔢 Přečíslovat scénáře od 001"):
        scen = projects[selected_project]["scenarios"]

        for i, t in enumerate(sorted(scen, key=lambda x: x["order_no"]), start=1):
            nove_cislo = f"{i:03d}"
            t["order_no"] = i

            # Pokud má název testu prefix jako "001_", nahradíme ho novým číslem
            if "_" in t["test_name"]:
                parts = t["test_name"].split("_", 1)
                if parts[0].isdigit() and len(parts[0]) <= 3:
                    t["test_name"] = f"{nove_cislo}_{parts[1]}"
                else:
                    t["test_name"] = f"{nove_cislo}_{t['test_name']}"
            else:
                t["test_name"] = f"{nove_cislo}_{t['test_name']}"

        projects[selected_project]["scenarios"] = scen
        save_json(PROJECTS_PATH, projects)
        st.success("✅ Scénáře a názvy byly přečíslovány.")
        st.rerun()

st.markdown("---")

# ---------- Přidání scénáře ----------
st.subheader("➕ Přidat nový scénář")
steps_data = get_steps()
akce_list = list(steps_data.keys())

with st.form("add_scenario"):
    veta = st.text_area("Věta (požadavek)", height=100, placeholder="Např.: Aktivuj DSL na B2C přes kanál SHOP …")
    akce = st.selectbox("Akce (z kroky.json)", options=akce_list)
    
    # Automatická komplexita
    pocet_kroku = len(steps_data.get(akce, []))
    auto_complexity = get_automatic_complexity(pocet_kroku)
    
    colp, colc = st.columns(2)
    with colp:
        priority = st.selectbox("Priorita", options=list(PRIORITY_MAP.values()), index=1)
    with colc:
        # Zobrazíme automatickou komplexitu, ale umožníme změnu
        complexity = st.selectbox(
            "Komplexita", 
            options=list(COMPLEXITY_MAP.values()), 
            index=list(COMPLEXITY_MAP.values()).index(auto_complexity),
            help=f"Automaticky nastaveno na {auto_complexity} podle {pocet_kroku} kroků"
        )
    
    # Zobrazíme info o automatickém nastavení
    st.info(f"🔍 Akce **{akce}** má **{pocet_kroku} kroků** → automatická komplexita: **{auto_complexity}**")

    if st.form_submit_button("➕ Přidat scénář"):
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
                complexity=complexity,  # Použijeme vybranou komplexitu (může být změněna)
                kroky_data=steps_data,
                projects_data=projects
            )
            st.success(f"✅ Scénář přidán: {tc['test_name']}")
            st.rerun()

st.markdown("---")

# ---------- Úprava scénáře ----------
st.subheader("✏️ Úprava scénáře")
if df.empty:
    st.info("Zatím žádné scénáře pro úpravu.")
else:
    selected_row = st.selectbox(
        "Vyber scénář k úpravě:",
        options=["— žádný —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
        index=0
    )

    if selected_row != "— žádný —":
        idx = int(selected_row.split(" - ")[0])
        scenario_list = projects[selected_project]["scenarios"]
        scenario_index = next((i for i, t in enumerate(scenario_list) if t["order_no"] == idx), None)
        scenario = scenario_list[scenario_index] if scenario_index is not None else None

        if scenario:
            with st.form("edit_scenario"):
                veta = st.text_area("Věta", value=scenario["veta"], height=100)
                akce = st.selectbox("Akce", options=akce_list, index=akce_list.index(scenario["akce"]) if scenario["akce"] in akce_list else 0)
                priority = st.selectbox("Priorita", options=list(PRIORITY_MAP.values()), index=list(PRIORITY_MAP.values()).index(scenario["priority"]))
                complexity = st.selectbox("Komplexita", options=list(COMPLEXITY_MAP.values()), index=list(COMPLEXITY_MAP.values()).index(scenario["complexity"]))
                if st.form_submit_button("💾 Uložit změny"):
                    # přepsání hodnot scénáře
                    scenario["veta"] = veta.strip()
                    scenario["akce"] = akce
                    scenario["priority"] = priority
                    scenario["complexity"] = complexity
                    # DŮLEŽITÉ: Použij deepcopy při přiřazování kroků
                    scenario["kroky"] = copy.deepcopy(steps_data.get(akce, []))
                    # přegenerování test name
                    scenario["test_name"] = scenario["test_name"].split("_")[0] + "_" + veta.strip().replace(" ", "_")
                    # uložení změn
                    projects[selected_project]["scenarios"][scenario_index] = scenario
                    save_json(PROJECTS_PATH, projects)
                    st.success("✅ Změny uloženy a propsány do projektu.")
                    st.rerun()

st.markdown("---")

# ---------- Smazání scénáře ----------
st.subheader("🗑️ Smazání scénáře")
if df.empty:
    st.info("Zatím žádné scénáře pro smazání.")
else:
    to_delete = st.selectbox(
        "Vyber scénář ke smazání:",
        options=["— žádný —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
        index=0
    )
    if to_delete != "— žádný —":
        idx = int(to_delete.split(" - ")[0])
        if st.button("🗑️ Potvrdit smazání scénáře"):
            scen = [t for t in projects[selected_project]["scenarios"] if t.get("order_no") != idx]
            for i, t in enumerate(scen, start=1):
                t["order_no"] = i
            projects[selected_project]["scenarios"] = scen
            save_json(PROJECTS_PATH, projects)
            st.success("Scénář smazán a pořadí přepočítáno.")
            st.rerun()

st.markdown("---")

# ---------- Informace o krocích ----------
with st.expander("📊 Přehled kroků podle akcí"):
    st.subheader("Kroky dostupné v systému")
    steps_data = get_steps()
    
    # Vytvoříme pěkný přehled s kolonkama
    cols = st.columns(2)
    for idx, akce in enumerate(sorted(steps_data.keys())):
        kroky = steps_data[akce]
        pocet_kroku = len(kroky)
        
        with cols[idx % 2]:
            st.metric(
                label=akce,
                value=f"{pocet_kroku} kroků",
                help=f"Klikni pro zobrazení detailů akce {akce}"
            )
    
    st.markdown("---")
    st.caption("💡 Tyto kroky se automaticky přiřazují k scénářům podle vybrané akce")

# ---------- Export ----------
st.subheader("📤 Export do Excelu + Git push (jedním kliknutím)")
if st.button("💾 Exportovat a nahrát na GitHub"):
    try:
        out = export_to_excel(selected_project, projects)
        rel = Path(out).relative_to(Path(__file__).resolve().parent.parent)
        st.success(f"✅ Export hotový: `{rel}`")
        st.download_button("⬇️ Stáhnout Excel", data=Path(out).read_bytes(),
                           file_name=Path(out).name,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Export selhal: {e}")
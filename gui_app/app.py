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

# ZMĚNA: Pouze "Vytvořit projekt"
if st.sidebar.button("✅ Vytvořit projekt"):
    if new_project_name.strip():
        projects = ensure_project(projects, new_project_name.strip())
        selected_project = new_project_name.strip()
        st.rerun()
    else:
        st.sidebar.warning("Zadej název projektu")

# NOVÉ: Tlačítka pro správu projektu (pokud je projekt vybrán)
if selected_project != "— vyber —" and selected_project in projects:
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Správa projektu")
    
    # Upravit název projektu
    with st.sidebar.expander("✏️ Upravit název projektu"):
        new_name = st.text_input("Nový název projektu", value=selected_project)
        if st.button("Uložit nový název"):
            if new_name.strip() and new_name != selected_project:
                projects[new_name] = projects.pop(selected_project)
                selected_project = new_name
                save_json(PROJECTS_PATH, projects)
                st.success("✅ Název projektu změněn")
                st.rerun()
    
    # Upravit subject
    with st.sidebar.expander("📝 Upravit Subject"):
        current_subject = projects[selected_project].get("subject", "UAT2\\Antosova\\")
        new_subject = st.text_input("Nový Subject", value=current_subject)
        if st.button("Uložit Subject"):
            if new_subject.strip():
                projects[selected_project]["subject"] = new_subject.strip()
                save_json(PROJECTS_PATH, projects)
                st.success("✅ Subject změněn")
                st.rerun()
    
    # Smazat projekt
    with st.sidebar.expander("🗑️ Smazat projekt"):
        st.warning(f"Chceš smazat projekt '{selected_project}'?")
        if st.button("ANO, smazat projekt"):
            projects.pop(selected_project)
            save_json(PROJECTS_PATH, projects)
            st.success(f"✅ Projekt '{selected_project}' smazán")
            st.rerun()

# ---------- Hlavní část ----------
st.title("🧪 TestCase Builder – GUI")

if selected_project == "— vyber —":
    st.info("Vyber nebo vytvoř projekt v levém panelu.")
    st.stop()

# Kontrola, zda projekt existuje v datech
if selected_project not in projects:
    st.error(f"Projekt '{selected_project}' nebyl nalezen v datech. Vyber jiný projekt.")
    st.stop()

# NOVÁ HLAVIČKA - STROMOVÁ STRUKTURA
st.subheader("📊 Přehled projektu")

# Základní informace ve sloupcích
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.metric("Aktivní projekt", selected_project)
with col2:
    st.metric("Počet scénářů", len(projects[selected_project].get("scenarios", [])))
with col3:
    st.metric("Next ID", projects[selected_project].get("next_id", 1))

# Subject pod projektem
st.write(f"**Subject:** {projects[selected_project].get('subject', 'UAT2\\\\Antosova\\\\')}")

st.markdown("---")

# ANALÝZA SCÉNÁŘŮ - STROMOVÁ STRUKTURA
scenarios = projects[selected_project].get("scenarios", [])

if scenarios:
    # Shromáždění dat pro analýzu
    segmenty = {}
    technologie = set()
    akce = set()
    
    for scenario in scenarios:
        seg = scenario.get("segment", "NEZNÁMÝ")
        tech = scenario.get("kanal", "NEZNÁMÝ") + " - " + scenario.get("akce", "NEZNÁMÁ")
        act = scenario.get("akce", "NEZNÁMÁ")
        
        if seg not in segmenty:
            segmenty[seg] = {"SHOP": 0, "IL": 0, "celkem": 0}
        
        kanal = scenario.get("kanal", "NEZNÁMÝ")
        if kanal in ["SHOP", "IL"]:
            segmenty[seg][kanal] += 1
        segmenty[seg]["celkem"] += 1
        
        technologie.add(tech)
        akce.add(act)
    
    # ZOBRAZENÍ STROMOVÉ STRUKTURY
    col_analysis, col_scenarios = st.columns([1, 2])
    
    with col_analysis:
        st.subheader("🌳 Analýza scénářů")
        
        # Segmenty a kanály
        with st.expander("📈 Segmenty a kanály", expanded=True):
            for segment, data in segmenty.items():
                st.write(f"**{segment}** ({data['celkem']} scénářů)")
                if data['SHOP'] > 0:
                    st.write(f"  └─ 🏪 SHOP: {data['SHOP']}")
                if data['IL'] > 0:
                    st.write(f"  └─ 📞 IL: {data['IL']}")
                st.write("")
        
        # Technologie
        with st.expander("🔧 Technologie a akce"):
            st.write("**Všechny technologie:**")
            for tech in sorted(technologie):
                st.write(f"• {tech}")
            
            st.write("")
            st.write("**Všechny akce:**")
            for act in sorted(akce):
                st.write(f"• {act}")
    
    with col_scenarios:
        st.subheader("📋 Seznam scénářů")
        
        # Tabulka scénářů
        df = make_df(projects, selected_project)
        if not df.empty:
            # Styly pro lepší čitelnost
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Order": st.column_config.NumberColumn("Číslo", width="small"),
                    "Test Name": st.column_config.TextColumn("Název testu", width="large"),
                    "Action": st.column_config.TextColumn("Akce", width="medium"),
                    "Segment": st.column_config.TextColumn("Segment", width="small"),
                    "Channel": st.column_config.TextColumn("Kanál", width="small"),
                    "Priority": st.column_config.TextColumn("Priorita", width="small"),
                    "Complexity": st.column_config.TextColumn("Komplexita", width="small"),
                    "Kroky": st.column_config.NumberColumn("Kroků", width="small")
                }
            )
            
            # Tlačítko pro přečíslování
            if st.button("🔢 Přečíslovat scénáře od 001", use_container_width=True):
                scen = projects[selected_project]["scenarios"]
                for i, t in enumerate(sorted(scen, key=lambda x: x["order_no"]), start=1):
                    nove_cislo = f"{i:03d}"
                    t["order_no"] = i
                    
                    # Přegenerování názvu s novým číslem
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
        else:
            st.info("Žádné scénáře k zobrazení.")

else:
    # Když nejsou žádné scénáře
    st.info("📝 Projekt zatím neobsahuje žádné scénáře. Vytvoř první scénář v sekci níže.")

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
                complexity=complexity,
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
                    
                    # PŘEGENEROVÁNÍ názvu test case s novými údaji
                    from core import parse_veta
                    segment, kanal, technologie = parse_veta(veta.strip())
                    nove_cislo = f"{scenario['order_no']:03d}"
                    scenario["test_name"] = f"{nove_cislo}_{kanal}_{segment}_{technologie}_{veta.strip().replace(' ', '_')}"
                    
                    # přepsání segmentu a kanálu
                    scenario["segment"] = segment
                    scenario["kanal"] = kanal
                    
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
        kroky = steps_data[akce].get("steps", []) if isinstance(steps_data[akce], dict) else steps_data[akce]
        pocet_kroku = len(kroky)
        popis_akce = steps_data[akce].get("description", "Bez popisu") if isinstance(steps_data[akce], dict) else "Bez popisu"
        
        with cols[idx % 2]:
            # Kontejner pro každou akci
            with st.container():
                # Název akce VELKÝMI písmeny
                st.markdown(f"**{akce.upper()}**")
                
                # Počet kroků v závorce pod názvem
                st.markdown(f"*({pocet_kroku} kroků)*")
                
                # Popis akce - přímo viditelný pod počtem kroků
                st.caption(f"📝 {popis_akce}")
                
                # Náhled všech kroků v popoveru
                with st.popover("👀 Náhled kroků", help=f"Zobrazí všech {pocet_kroku} kroků pro akci {akce}"):
                    if pocet_kroku > 0:
                        st.write(f"**Kroky pro {akce}:**")
                        for i, krok in enumerate(kroky, 1):
                            if isinstance(krok, dict):
                                desc = krok.get('description', '')
                                exp = krok.get('expected', '')
                                st.write(f"**{i}. {desc}**")
                                if exp:
                                    st.write(f"   *Očekávání: {exp}*")
                            else:
                                st.write(f"{i}. {krok}")
                            if i < len(kroky):
                                st.divider()
                    else:
                        st.write("Žádné kroky")
                
                # Oddělovač mezi akcemi
                st.markdown("---")

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
import streamlit as st
import pandas as pd
from pathlib import Path
import copy
from core import (
    load_json, save_json,
    get_user_projects_path, get_user_kroky_path,
    generate_testcase, export_to_excel, parse_veta,
    PRIORITY_MAP, COMPLEXITY_MAP
)

# ---------- Konfigurace vzhledu ----------
st.set_page_config(page_title="TestCase Builder", layout="wide", page_icon="🧪")

# ---------- INICIALIZACE SESSION STATE ----------
if 'username' not in st.session_state:
    st.session_state.username = ""

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

# ---------- UŽIVATELSKÁ AUTENTIZACE ----------
def get_username():
    """Získá nebo nastaví uživatelské jméno"""
    return st.session_state.username

# ---------- Sidebar ----------
st.sidebar.title("👤 Uživatel")

# Výběr uživatele v sidebaru
if not st.session_state.username:
    username = st.sidebar.text_input("Zadejte své uživatelské jméno:", placeholder="Např. jana.novak")
    
    if st.sidebar.button("Pokračovat"):
        if username.strip():
            st.session_state.username = username.strip()
            st.rerun()
        else:
            st.sidebar.error("Zadejte uživatelské jméno")
    
    st.sidebar.info("💡 Každý uživatel má své vlastní projekty a scénáře")
    st.stop()
else:
    # Uživatel je přihlášen - zobrazíme informace
    st.sidebar.write(f"**Přihlášen:** {st.session_state.username}")
    
    # Možnost změnit uživatele
    if st.sidebar.button("🚪 Změnit uživatele"):
        st.session_state.username = ""
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("📁 Projekt")

# Získání uživatelského jména
username = get_username()



# ---------- Pomocné funkce ----------
def get_projects(username: str):
    projects_path = get_user_projects_path(username)
    return load_json(projects_path)

def get_steps(username: str):
    kroky_path = get_user_kroky_path(username)
    return load_json(kroky_path)

def ensure_project(username: str, projects: dict, name: str, subject=None):
    if name not in projects:
        projects[name] = {"next_id": 1, "subject": subject or "UAT2\\Antosova\\", "scenarios": []}
        projects_path = get_user_projects_path(username)
        save_json(projects_path, projects)
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
st.sidebar.title("👤 Uživatel")

# Výběr uživatele v sidebaru
if not st.session_state.username:
    username = st.sidebar.text_input("Zadejte své uživatelské jméno:", placeholder="Např. jana.novak")
    
    if st.sidebar.button("Pokračovat"):
        if username.strip():
            st.session_state.username = username.strip()
            st.rerun()
        else:
            st.sidebar.error("Zadejte uživatelské jméno")
    
    st.sidebar.info("💡 Každý uživatel má své vlastní projekty a scénáře")
    st.stop()
else:
    # Uživatel je přihlášen - zobrazíme informace
    st.sidebar.write(f"**Přihlášen:** {st.session_state.username}")
    
    # Možnost změnit uživatele
    if st.sidebar.button("🚪 Změnit uživatele"):
        st.session_state.username = ""
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("📁 Projekt")

# Získání uživatelského jména
username = get_username()

# Načtení projektů pro daného uživatele
projects = get_projects(username)
project_names = list(projects.keys())

selected_project = st.sidebar.selectbox(
    "Vyber projekt",
    options=["— vyber —"] + project_names,
    index=0
)
new_project_name = st.sidebar.text_input("Název nového projektu", placeholder="Např. CCCTR-XXXX – Název")

if st.sidebar.button("✅ Vytvořit projekt"):
    if new_project_name.strip():
        projects = ensure_project(username, projects, new_project_name.strip())
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
                save_json(get_user_projects_path(username), projects)
                st.success("✅ Název projektu změněn")
                st.rerun()
    
    # Upravit subject
    with st.sidebar.expander("📝 Upravit Subject"):
        current_subject = projects[selected_project].get("subject", "UAT2\\Antosova\\")
        new_subject = st.text_input("Nový Subject", value=current_subject)
        if st.button("Uložit Subject"):
            if new_subject.strip():
                projects[selected_project]["subject"] = new_subject.strip()
                save_json(get_user_projects_path(username), projects)
                st.success("✅ Subject změněn")
                st.rerun()
    
    # Smazat projekt
    with st.sidebar.expander("🗑️ Smazat projekt"):
        st.warning(f"Chceš smazat projekt '{selected_project}'?")
        if st.button("ANO, smazat projekt"):
            projects.pop(selected_project)
            save_json(get_user_projects_path(username), projects)
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

# NOVÁ HLAVIČKA
st.subheader("📊 Přehled projektu")

# Základní informace pod sebou
st.write(f"**Aktivní projekt:** {selected_project}")
st.write(f"**Subject:** {projects[selected_project].get('subject', 'UAT2\\\\Antosova\\\\')}")
st.write(f"**Počet scénářů:** {len(projects[selected_project].get('scenarios', []))}")

st.markdown("---")

# SEZNAM SCÉNÁŘŮ A PŘEČÍSLOVÁNÍ
scenarios = projects[selected_project].get("scenarios", [])

if scenarios:
    st.subheader("📋 Seznam scénářů")
    
    # Tabulka scénářů
    df = make_df(projects, selected_project)
    if not df.empty:
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
            save_json(get_user_projects_path(username), projects)
            st.success("✅ Scénáře a názvy byly přečíslovány.")
            st.rerun()

    st.markdown("---")

    # ANALÝZA SCÉNÁŘŮ - STROMOVÁ STRUKTURA
    st.subheader("🌳 Analýza scénářů")
    
    # Shromáždění dat pro stromovou strukturu
    segment_data = {"B2C": {}, "B2B": {}}
    
    for scenario in scenarios:
        segment = scenario.get("segment", "NEZNÁMÝ")
        kanal = scenario.get("kanal", "NEZNÁMÝ")
        
        # Detekce technologie z názvu test case
        test_name = scenario.get("test_name", "")
        technologie = "DSL"  # výchozí hodnota

        # Detekce technologie z názvu test case - OPRAVENÉ
        if "FIBER" in test_name:
            technologie = "FIBER"
        elif "FWA_BISI" in test_name:  # DŮLEŽITÉ: Nejprve BISI, pak BI
            technologie = "FWA BISI"
        elif "FWA_BI" in test_name:
            technologie = "FWA BI" 
        elif "CABLE" in test_name:
            technologie = "CABLE"
        elif "HLAS" in test_name:
            technologie = "HLAS"
        elif "DSL" in test_name:
            technologie = "DSL"
        
        akce = scenario.get("akce", "NEZNÁMÁ")
        
        if segment not in segment_data:
            segment_data[segment] = {}
        
        if kanal not in segment_data[segment]:
            segment_data[segment][kanal] = {}
            
        if technologie not in segment_data[segment][kanal]:
            segment_data[segment][kanal][technologie] = []
            
        if akce not in segment_data[segment][kanal][technologie]:
            segment_data[segment][kanal][technologie].append(akce)
    
    # VYTVOŘENÍ STROMOVÉ STRUKTURY PODLE TVÉHO NÁVRHU
    col_b2c, col_b2b = st.columns(2)
    
    with col_b2c:
        with st.expander("👥 B2C", expanded=True):
            if "B2C" in segment_data and segment_data["B2C"]:
                for kanal in segment_data["B2C"]:
                    # KANÁL - větší a tučně
                    st.markdown(f"<h4 style='margin-bottom: 5px;'>{kanal}</h4>", unsafe_allow_html=True)
                    
                    for technologie in segment_data["B2C"][kanal]:
                        # TECHNOLOGIE - tučně
                        st.markdown(f"<strong>{technologie}</strong>", unsafe_allow_html=True)
                        
                        # Akce odsazené vedle technologie
                        for akce in segment_data["B2C"][kanal][technologie]:
                            st.write(f"  • {akce}")
                    
                    # Oddělovač mezi kanály
                    if kanal != list(segment_data["B2C"].keys())[-1]:
                        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            else:
                st.write("Žádné B2C scénáře")
    
    with col_b2b:
        with st.expander("🏢 B2B", expanded=True):
            if "B2B" in segment_data and segment_data["B2B"]:
                for kanal in segment_data["B2B"]:
                    # KANÁL - větší a tučně
                    st.markdown(f"<h4 style='margin-bottom: 5px;'>{kanal}</h4>", unsafe_allow_html=True)
                    
                    for technologie in segment_data["B2B"][kanal]:
                        # TECHNOLOGIE - tučně
                        st.markdown(f"<strong>{technologie}</strong>", unsafe_allow_html=True)
                        
                        # Akce odsazené vedle technologie
                        for akce in segment_data["B2B"][kanal][technologie]:
                            st.write(f"  • {akce}")
                    
                    # Oddělovač mezi kanály
                    if kanal != list(segment_data["B2B"].keys())[-1]:
                        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            else:
                st.write("Žádné B2B scénáře")

else:
    # Když nejsou žádné scénáře
    st.info("📝 Projekt zatím neobsahuje žádné scénáře. Vytvoř první scénář v sekci níže.")

st.markdown("---")

# ---------- Přidání scénáře ----------
st.subheader("➕ Přidat nový scénář")
steps_data = get_steps(username)
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
                username=username,
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
if not scenarios:  # Místo df.empty použijeme scenarios
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
                    save_json(get_user_projects_path(username), projects)
                    st.success("✅ Změny uloženy a propsány do projektu.")
                    st.rerun()

st.markdown("---")

# ---------- Smazání scénáře ----------
st.subheader("🗑️ Smazání scénáře")
if not scenarios:  # Místo df.empty použijeme scenarios
    st.info("Zatím žádné scénáře pro smazání.")
else:
    to_delete = st.selectbox(
        "Vyber scénář ke smazání:",
        options=["— žádný —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
        index=0,
        key="delete_selector"  # Přidáme key aby se nepletl s předchozím selectboxem
    )
    if to_delete != "— žádný —":
        idx = int(to_delete.split(" - ")[0])
        if st.button("🗑️ Potvrdit smazání scénáře"):
            scen = [t for t in projects[selected_project]["scenarios"] if t.get("order_no") != idx]
            for i, t in enumerate(scen, start=1):
                t["order_no"] = i
            projects[selected_project]["scenarios"] = scen
            save_json(get_user_projects_path(username), projects)
            st.success("Scénář smazán a pořadí přepočítáno.")
            st.rerun()

st.markdown("---")

# ---------- Informace o krocích ----------
with st.expander("📊 Přehled kroků podle akcí"):
    st.subheader("Kroky dostupné v systému")
    steps_data = get_steps(username)
    
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

st.markdown("---")

# ---------- Export ----------
st.subheader("📤 Export do Excelu + Git push (jedním kliknutím)")
if st.button("💾 Exportovat a nahrát na GitHub"):
    try:
        out = export_to_excel(username, selected_project, projects)
        rel = Path(out).relative_to(Path(__file__).resolve().parent.parent)
        st.success(f"✅ Export hotový: `{rel}`")
        st.download_button("⬇️ Stáhnout Excel", data=Path(out).read_bytes(),
                           file_name=Path(out).name,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Export selhal: {e}")
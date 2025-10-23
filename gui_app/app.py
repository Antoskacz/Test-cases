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



# ---------- Hlavní část - hlavní strana aplikace ----------
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
            save_json(PROJECTS_PATH, projects)
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
    
    # SPRÁVNÁ DETEKCE TECHNOLOGIE z názvu test case
    test_name = scenario.get("test_name", "")
    technologie = "DSL"  # výchozí hodnota
    
    # Detekce technologie z názvu test case
    if "FIBER" in test_name:
        technologie = "FIBER"
    elif "FWA_BISI" in test_name:
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


# ---------- Přidání scénáře ----------
st.subheader("➕ Přidat nový scénář")
steps_data = get_steps()
akce_list = list(steps_data.keys())

with st.form("add_scenario"):
    veta = st.text_area("Věta (požadavek)", height=100, placeholder="Např.: Aktivuj DSL na B2C přes kanál SHOP …")
    akce = st.selectbox("Akce (z kroky.json)", options=akce_list)
    
    # Automatická komplexita - OPRAVENÉ NAČÍTÁNÍ POČTU KROKŮ
    from core import get_steps_from_action
    kroky_pro_akci = get_steps_from_action(akce, steps_data)
    pocet_kroku = len(kroky_pro_akci)
    
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
if not scenarios:
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
                    # DŮLEŽITÉ: Použij správné načtení kroků
                    scenario["kroky"] = get_steps_from_action(akce, steps_data)
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
            save_json(PROJECTS_PATH, projects)
            st.success("Scénář smazán a pořadí přepočítáno.")
            st.rerun()



# ---------- Informace o krocích ----------

# FUNKCE PRO ZOBRAZENÍ AKCE
def zobraz_akci_s_upravou(akce, obsah_akce):
    """Zobrazí akci s možností rychlé editace"""
    
    # Získání kroků a popisu
    if isinstance(obsah_akce, dict) and "steps" in obsah_akce:
        kroky = obsah_akce.get("steps", [])
        popis_akce = obsah_akce.get("description", "Bez popisu")
    else:
        kroky = obsah_akce if isinstance(obsah_akce, list) else []
        popis_akce = "Bez popisu"
    
    pocet_kroku = len(kroky)
    
    # Kontejner pro akci
    with st.container():
        # Hlavička akce s editací
        col_nazev, col_edit = st.columns([3, 1])
        
        with col_nazev:
            st.markdown(f"**{akce.upper()}**")
            st.markdown(f"*({pocet_kroku} kroků)*")
            st.caption(f"📝 {popis_akce}")
        
        with col_edit:
            # Tlačítko pro editaci
            if st.button("✏️ Upravit", key=f"edit_{akce}", use_container_width=True):
                st.session_state[f"edit_akce_{akce}"] = True
        
        # Náhled kroků
        with st.expander(f"👀 Náhled ({pocet_kroku} kroků)", expanded=False):
            if pocet_kroku > 0:
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
        
        # EDITACE AKCE - POUŽIJEME EXPANDER MÍSTO DIALOGU
        if st.session_state.get(f"edit_akce_{akce}", False):
            with st.expander(f"✏️ Editace akce: {akce}", expanded=True):
                st.subheader(f"✏️ Editace akce: {akce}")
                
                # Popis akce
                novy_popis = st.text_input("Popis akce", value=popis_akce, key=f"desc_{akce}")
                
                st.markdown("---")
                st.write("**Správa kroků:**")
                
                # Načtení aktuálních kroků do session state
                if f"kroky_{akce}" not in st.session_state:
                    st.session_state[f"kroky_{akce}"] = kroky.copy()
                
                # Zobrazení a editace kroků
                if st.session_state[f"kroky_{akce}"]:
                    st.write("**Aktuální kroky:**")
                    for i, krok in enumerate(st.session_state[f"kroky_{akce}"]):
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            if isinstance(krok, dict):
                                # Uložení hodnot do session state pro editaci
                                desc_key = f"edit_desc_{akce}_{i}"
                                exp_key = f"edit_exp_{akce}_{i}"
                                
                                if desc_key not in st.session_state:
                                    st.session_state[desc_key] = krok.get('description', '')
                                if exp_key not in st.session_state:
                                    st.session_state[exp_key] = krok.get('expected', '')
                                
                                new_desc = st.text_area(
                                    f"Krok {i+1} - Description", 
                                    value=st.session_state[desc_key],
                                    key=desc_key,
                                    height=80
                                )
                                new_exp = st.text_area(
                                    f"Krok {i+1} - Expected", 
                                    value=st.session_state[exp_key],
                                    key=exp_key, 
                                    height=80
                                )
                                
                                # Aktualizace kroku v session state
                                st.session_state[f"kroky_{akce}"][i] = {
                                    "description": new_desc,
                                    "expected": new_exp
                                }
                            else:
                                text_key = f"edit_text_{akce}_{i}"
                                if text_key not in st.session_state:
                                    st.session_state[text_key] = krok
                                
                                new_text = st.text_area(
                                    f"Krok {i+1}", 
                                    value=st.session_state[text_key],
                                    key=text_key,
                                    height=80
                                )
                                st.session_state[f"kroky_{akce}"][i] = new_text
                        
                        with col2:
                            # Tlačítko pro smazání kroku
                            if st.button("🗑️", key=f"del_{akce}_{i}", use_container_width=True):
                                if i < len(st.session_state[f"kroky_{akce}"]):
                                    # Smazání také session state pro tento krok
                                    desc_key = f"edit_desc_{akce}_{i}"
                                    exp_key = f"edit_exp_{akce}_{i}"
                                    text_key = f"edit_text_{akce}_{i}"
                                    
                                    for key in [desc_key, exp_key, text_key]:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    
                                    st.session_state[f"kroky_{akce}"].pop(i)
                                    st.rerun()
                        
                        st.markdown("---")
                else:
                    st.info("Žádné kroky")
                
                # PŘIDÁNÍ NOVÉHO KROKU
                st.write("**Přidat nový krok:**")
                new_desc = st.text_area("Description*", placeholder="Popis kroku - co se má udělat", key=f"new_desc_{akce}", height=80)
                new_expected = st.text_area("Expected*", placeholder="Očekávaný výsledek - co se má stát", key=f"new_exp_{akce}", height=80)
                
                if st.button("➕ Přidat krok", key=f"add_{akce}", use_container_width=True):
                    if new_desc.strip():
                        st.session_state[f"kroky_{akce}"].append({
                            "description": new_desc.strip(),
                            "expected": new_expected.strip()
                        })
                        st.rerun()
                
                st.markdown("---")
                
                # Tlačítka pro uložení/zrušení
                col_save, col_cancel, col_delete = st.columns([2, 2, 1])
                
                with col_save:
                    if st.button("💾 Uložit změny", key=f"save_{akce}", use_container_width=True, type="primary"):
                        # Uložení změn do kroky.json
                        kroky_data = get_global_steps()
                        
                        kroky_data[akce] = {
                            "description": novy_popis,
                            "steps": st.session_state[f"kroky_{akce}"].copy()
                        }
                        save_global_steps(kroky_data)
                        st.success(f"✅ Akce '{akce}' byla upravena!")
                        
                        # Vyčištění session state
                        st.session_state[f"edit_akce_{akce}"] = False
                        # Vyčištění edit keys
                        for key in list(st.session_state.keys()):
                            if key.startswith(f"edit_desc_{akce}_") or key.startswith(f"edit_exp_{akce}_") or key.startswith(f"edit_text_{akce}_"):
                                del st.session_state[key]
                        
                        # Aktualizace celé aplikace
                        refresh_all_data()
                        st.rerun()
                
                with col_cancel:
                    if st.button("❌ Zrušit", key=f"cancel_{akce}", use_container_width=True):
                        st.session_state[f"edit_akce_{akce}"] = False
                        # Vyčištění session state
                        if f"kroky_{akce}" in st.session_state:
                            del st.session_state[f"kroky_{akce}"]
                        # Vyčištění edit keys
                        for key in list(st.session_state.keys()):
                            if key.startswith(f"edit_desc_{akce}_") or key.startswith(f"edit_exp_{akce}_") or key.startswith(f"edit_text_{akce}_"):
                                del st.session_state[key]
                        st.rerun()
                
                with col_delete:
                    if st.button("🗑️ Smazat", key=f"delete_{akce}", use_container_width=True):
                        # Potvrzení smazání
                        st.session_state[f"confirm_delete_{akce}"] = True
                        st.rerun()
                
                # Potvrzení smazání akce
                if st.session_state.get(f"confirm_delete_{akce}", False):
                    st.error(f"🚨 Opravdu chceš smazat akci '{akce}'?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("ANO, smazat", key=f"yes_delete_{akce}", use_container_width=True):
                            kroky_data = get_global_steps()
                            if akce in kroky_data:
                                del kroky_data[akce]
                                save_global_steps(kroky_data)
                                st.success(f"✅ Akce '{akce}' byla smazána!")
                                
                                # Vyčištění session state
                                st.session_state[f"edit_akce_{akce}"] = False
                                st.session_state[f"confirm_delete_{akce}"] = False
                                if f"kroky_{akce}" in st.session_state:
                                    del st.session_state[f"kroky_{akce}"]
                                # Vyčištění edit keys
                                for key in list(st.session_state.keys()):
                                    if key.startswith(f"edit_desc_{akce}_") or key.startswith(f"edit_exp_{akce}_") or key.startswith(f"edit_text_{akce}_"):
                                        del st.session_state[key]
                                
                                refresh_all_data()
                                st.rerun()
                    with col_no:
                        if st.button("NE, zachovat", key=f"no_delete_{akce}", use_container_width=True):
                            st.session_state[f"confirm_delete_{akce}"] = False
                            st.rerun()
        
        st.markdown("---")

# HLAVNÍ ČÁST - PŘEHLED KROKŮ
with st.expander("📊 Přehled kroků podle akcí"):
    st.subheader("Kroky dostupné v systému")
    steps_data = get_steps()
    
    # Tlačítko pro přidání nové akce
    if st.button("➕ Přidat novou akci", key="add_new_action_main", use_container_width=True):
        st.session_state["add_new_action"] = True
    
    # FORMULÁŘ PRO NOVOU AKCI
    if st.session_state.get("add_new_action", False):
        with st.expander("➕ Přidat novou akci", expanded=True):
            st.subheader("➕ Přidat novou akci")
            
            nova_akce_nazev = st.text_input("Název akce*", placeholder="Např.: Aktivace_DSL", key="new_akce_name")
            nova_akce_popis = st.text_input("Popis akce*", placeholder="Např.: Aktivace DSL služby", key="new_akce_desc")
            
            st.write("**Kroky akce:**")
            
            # Inicializace session state pro kroky
            if 'new_steps' not in st.session_state:
                st.session_state.new_steps = []
            
            # Zobrazení existujících kroků
            if st.session_state.new_steps:
                st.write("**Přidané kroky:**")
                for i, krok in enumerate(st.session_state.new_steps):
                    col_step, col_del = st.columns([4, 1])
                    with col_step:
                        st.text_input("Description*", value=krok['description'], key=f"view_desc_{i}", disabled=True)
                        st.text_input("Expected*", value=krok['expected'], key=f"view_exp_{i}", disabled=True)
                    with col_del:
                        if st.button("🗑️", key=f"del_new_{i}", use_container_width=True):
                            if i < len(st.session_state.new_steps):
                                st.session_state.new_steps.pop(i)
                                st.rerun()
                    st.markdown("---")
            
            # Přidání nového kroku
            st.write("**Přidat nový krok:**")
            new_step_desc = st.text_area("Description*", placeholder="Popis kroku - co se má udělat", key="new_step_desc", height=60)
            new_step_expected = st.text_area("Expected*", placeholder="Očekávaný výsledek - co se má stát", key="new_step_expected", height=60)
            
            col_add, col_clear = st.columns(2)
            with col_add:
                if st.button("➕ Přidat krok", key="add_step_btn", use_container_width=True):
                    if new_step_desc.strip() and new_step_expected.strip():
                        st.session_state.new_steps.append({
                            "description": new_step_desc.strip(),
                            "expected": new_step_expected.strip()
                        })
                        st.rerun()
                    else:
                        st.warning("Vyplňte obě pole pro krok")
            with col_clear:
                if st.button("🗑️ Smazat vše", key="clear_all_btn", use_container_width=True):
                    st.session_state.new_steps = []
                    st.rerun()
            
            # Tlačítka pro uložení/zrušení
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("💾 Uložit novou akci", key="save_new_action", use_container_width=True, type="primary"):
                    if not nova_akce_nazev.strip() or not nova_akce_popis.strip() or not st.session_state.new_steps:
                        st.error("Vyplňte všechny povinné pole (*) a přidejte alespoň jeden krok")
                    else:
                        kroky_data = get_global_steps()
                        kroky_data[nova_akce_nazev.strip()] = {
                            "description": nova_akce_popis.strip(),
                            "steps": st.session_state.new_steps.copy()
                        }
                        save_global_steps(kroky_data)
                        st.success(f"✅ Akce '{nova_akce_nazev}' byla přidána!")
                        # Reset session state
                        st.session_state.new_steps = []
                        st.session_state["add_new_action"] = False
                        # AKTUALIZACE CELÉ APLIKACE
                        refresh_all_data()
                        st.rerun()
            
            with col_cancel:
                if st.button("❌ Zrušit", key="cancel_new_action", use_container_width=True):
                    st.session_state["add_new_action"] = False
                    st.session_state.new_steps = []
                    st.rerun()
    
    st.markdown("---")
    
    # Rozdělení akcí na FIX a ostatní
    fix_akce = []
    ostatni_akce = []
    
    for akce in sorted(steps_data.keys()):
        if "FIX" in akce.upper():
            fix_akce.append(akce)
        else:
            ostatni_akce.append(akce)
    
    # Vytvoříme dva sloupce
    col_fix, col_ostatni = st.columns(2)
    
    with col_fix:
        st.markdown("### 🔧 FIX")
        if fix_akce:
            for akce in fix_akce:
                zobraz_akci_s_upravou(akce, steps_data[akce])
        else:
            st.write("Žádné FIX akce")
    
    with col_ostatni:
        st.markdown("### 📞 Ostatní")
        if ostatni_akce:
            for akce in ostatni_akce:
                zobraz_akci_s_upravou(akce, steps_data[akce])
        else:
            st.write("Žádné ostatní akce")

                
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
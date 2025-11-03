import streamlit as st
import pandas as pd
from pathlib import Path
import copy
import json
from datetime import datetime
from core import (
    load_json, save_json,
    PROJECTS_PATH, KROKY_PATH,
    generate_testcase, export_to_excel,
    PRIORITY_MAP, COMPLEXITY_MAP,
    get_steps_from_action
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

# ---------- Cesty ----------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Bezpečné načítání projektů ----------
def get_projects():
    """Bezpečně načte projekty - chrání před ztrátou dat"""
    try:
        projects = load_json(PROJECTS_PATH)
        # Pokud soubor neexistuje nebo je prázdný, vrátíme základní strukturu
        if not projects:
            return {}
        return projects
    except Exception as e:
        st.error(f"Chyba při načítání projektů: {e}")
        return {}

def save_projects_safely(projects_data):
    """Bezpečně uloží projekty s kontrolou"""
    try:
        save_json(PROJECTS_PATH, projects_data)
        return True
    except Exception as e:
        st.error(f"Chyba při ukládání projektů: {e}")
        return False

# ---------- Pomocné funkce ----------
def get_steps():
    return load_json(KROKY_PATH)

def ensure_project(projects, name, subject=None):
    if name not in projects:
        projects[name] = {"next_id": 1, "subject": subject or "UAT2\\Antosova\\", "scenarios": []}
        save_projects_safely(projects)
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

# ---------- Funkce pro správu akcí ----------
def get_global_steps():
    kroky_path = Path(__file__).resolve().parent.parent / "data" / "kroky.json"
    return load_json(kroky_path)

def save_global_steps(data):
    kroky_path = Path(__file__).resolve().parent.parent / "data" / "kroky.json"
    kroky_path.parent.mkdir(exist_ok=True)
    save_json(kroky_path, data)

def refresh_all_data():
    """Obnoví všechna data v aplikaci po změně kroků"""
    st.rerun()

def check_github_status():
    """Zkontroluje stav GitHub synchronizace"""
    try:
        import subprocess
        # Nejprve zkontrolujeme jestli jsme v git repozitáři
        check_git = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=BASE_DIR)
        if "not a git repository" in check_git.stderr:
            return "❌ Není Git repozitář"
        
        # Zkontrolujeme změny
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=BASE_DIR)
        if result.stdout.strip():
            return "⚠️ Čeká na synchronizaci s GitHub"
        else:
            return "✅ Synchronizováno s GitHub"
    except Exception as e:
        return f"❌ Nelze zkontrolovat: {str(e)}"

def sprava_akci():
    """Jednoduchá a efektivní správa akcí s ukládáním do kroky.json"""
    from core import add_new_action, update_action, delete_action
    
    steps_data = get_steps()
    
    # Tlačítko pro novou akci
    if st.button("➕ Přidat novou akci", key="nova_akce_hlavni", use_container_width=True):
        st.session_state["nova_akce"] = True
        st.session_state["edit_akce"] = None
    
    # Formulář pro NOVOU AKCI
    if st.session_state.get("nova_akce", False):
        st.subheader("➕ Přidat novou akci")
        
        with st.form("nova_akce_formular"):
            nova_akce_nazev = st.text_input("Název akce*", placeholder="Např.: Aktivace_DSL", key="new_akce_name")
            nova_akce_popis = st.text_input("Popis akce*", placeholder="Např.: Aktivace DSL služby", key="new_akce_desc")
            
            st.markdown("---")
            st.write("**Kroky akce:**")
            
            # Inicializace session state pro nové kroky
            if "nove_kroky" not in st.session_state:
                st.session_state["nove_kroky"] = []
            
            # Zobrazení existujících kroků
            if st.session_state["nove_kroky"]:
                st.write("**Přidané kroky:**")
                kroky_k_smazani = []
                
                for i, krok in enumerate(st.session_state["nove_kroky"]):
                    col_krok, col_smazat = st.columns([4, 1])
                    
                    with col_krok:
                        st.text_input(f"Krok {i+1} - Description", 
                                    value=krok['description'], 
                                    key=f"view_desc_{i}", 
                                    disabled=True)
                        st.text_input(f"Krok {i+1} - Expected", 
                                    value=krok['expected'], 
                                    key=f"view_exp_{i}", 
                                    disabled=True)
                    
                    with col_smazat:
                        st.write("")  # Prázdný řádek
                        if st.form_submit_button("🗑️", key=f"del_new_{i}", use_container_width=True):
                            kroky_k_smazani.append(i)
                    
                    st.markdown("---")
                
                # Smazání označených kroků
                for index in sorted(kroky_k_smazani, reverse=True):
                    if index < len(st.session_state["nove_kroky"]):
                        st.session_state["nove_kroky"].pop(index)
                        st.rerun()
            else:
                st.info("Zatím žádné kroky. Přidejte první krok níže.")
            
            # Přidání nového kroku
            st.write("**Přidat nový krok:**")
            new_desc = st.text_area("Description*", key="new_step_desc", height=60, 
                                  placeholder="Popis kroku - co se má udělat")
            new_exp = st.text_area("Expected*", key="new_step_exp", height=60, 
                                 placeholder="Očekávaný výsledek - co se má stát")
            
            if st.form_submit_button("➕ Přidat krok", key="add_step_btn"):
                if new_desc.strip() and new_exp.strip():
                    st.session_state["nove_kroky"].append({
                        "description": new_desc.strip(),
                        "expected": new_exp.strip()
                    })
                    st.rerun()
                else:
                    st.warning("Vyplňte obě pole pro krok")
            
            st.markdown("---")
            
            # Tlačítka pro uložení/zrušení
            col_ulozit, col_zrusit = st.columns(2)
            with col_ulozit:
                if st.form_submit_button("💾 Uložit novou akci", use_container_width=True, type="primary"):
                    if not nova_akce_nazev.strip():
                        st.error("Zadejte název akce")
                    elif not nova_akce_popis.strip():
                        st.error("Zadejte popis akce")
                    elif not st.session_state["nove_kroky"]:
                        st.error("Přidejte alespoň jeden krok")
                    else:
                        try:
                            success = add_new_action(
                                nova_akce_nazev.strip(),
                                nova_akce_popis.strip(),
                                st.session_state["nove_kroky"].copy()
                            )
                            
                            if success:
                                st.success(f"✅ Akce '{nova_akce_nazev}' byla úspěšně přidána a uložena do kroky.json!")
                                # Vyčištění session state
                                st.session_state["nova_akce"] = False
                                st.session_state["nove_kroky"] = []
                                refresh_all_data()
                            else:
                                st.error("❌ Chyba při ukládání akce")
                                
                        except Exception as e:
                            st.error(f"❌ Chyba: {e}")
            
            with col_zrusit:
                if st.form_submit_button("❌ Zrušit", use_container_width=True):
                    st.session_state["nova_akce"] = False
                    if "nove_kroky" in st.session_state:
                        st.session_state["nove_kroky"] = []
                    st.rerun()
    
    st.markdown("---")
    
    # Seznam existujících akcí
    if steps_data:
        st.subheader("📝 Existující akce")
        
        for akce in sorted(steps_data.keys()):
            obsah = steps_data[akce]
            popis = obsah.get("description", "Bez popisu") if isinstance(obsah, dict) else "Bez popisu"
            kroky = obsah.get("steps", []) if isinstance(obsah, dict) else obsah
            pocet_kroku = len(kroky)
            
            col_akce, col_edit, col_smazat = st.columns([3, 1, 1])
            
            with col_akce:
                st.write(f"**{akce}**")
                st.caption(f"{popis} | {pocet_kroku} kroků")
            
            with col_edit:
                if st.button("✏️", key=f"edit_{akce}", help="Upravit akci", use_container_width=True):
                    st.session_state["edit_akce"] = akce
                    st.session_state["nova_akce"] = False
                    st.rerun()
            
            with col_smazat:
                if st.button("🗑️", key=f"delete_{akce}", help="Smazat akci", use_container_width=True):
                    st.session_state["smazat_akci"] = akce
                    st.rerun()
            
            # Potvrzení smazání
            if st.session_state.get("smazat_akci") == akce:
                st.error(f"🚨 Opravdu smazat akci '{akce}'? Tato akce je nevratná!")
                col_ano, col_ne = st.columns(2)
                with col_ano:
                    if st.button("ANO, smazat", key=f"ano_{akce}", use_container_width=True):
                        try:
                            success = delete_action(akce)
                            if success:
                                st.success(f"✅ Akce '{akce}' byla smazána z kroky.json!")
                                st.session_state["smazat_akci"] = None
                                refresh_all_data()
                            else:
                                st.error("❌ Chyba při mazání akce")
                        except Exception as e:
                            st.error(f"❌ Chyba: {e}")
                with col_ne:
                    if st.button("NE, zachovat", key=f"ne_{akce}", use_container_width=True):
                        st.session_state["smazat_akci"] = None
                        st.rerun()
            
            st.markdown("---")
    
    # EDITACE EXISTUJÍCÍ AKCE
    if "edit_akce" in st.session_state and st.session_state["edit_akce"]:
        akce = st.session_state["edit_akce"]
        steps_data_current = get_steps()
        obsah = steps_data_current.get(akce, {})
        popis = obsah.get("description", "") if isinstance(obsah, dict) else ""
        kroky = obsah.get("steps", []) if isinstance(obsah, dict) else obsah
        
        st.subheader(f"✏️ Editace akce: {akce}")
        
        # Inicializace session state pro editované kroky
        if f"edit_kroky_{akce}" not in st.session_state:
            st.session_state[f"edit_kroky_{akce}"] = kroky.copy()
        
        with st.form(f"edit_akce_{akce}"):
            novy_popis = st.text_input("Popis akce*", value=popis, key=f"desc_{akce}")
            
            st.markdown("---")
            st.write("**Kroky akce:**")
            
            # Zobrazení kroků pro editaci
            kroky_k_smazani = []
            for i, krok in enumerate(st.session_state[f"edit_kroky_{akce}"]):
                col_krok, col_smazat = st.columns([4, 1])
                
                with col_krok:
                    if isinstance(krok, dict):
                        desc = st.text_area(f"Krok {i+1} - Description", 
                                          value=krok.get('description', ''),
                                          key=f"desc_{akce}_{i}",
                                          height=60)
                        exp = st.text_area(f"Krok {i+1} - Expected", 
                                         value=krok.get('expected', ''),
                                         key=f"exp_{akce}_{i}",
                                         height=60)
                        # Aktualizace kroku v session state
                        st.session_state[f"edit_kroky_{akce}"][i] = {"description": desc, "expected": exp}
                    else:
                        # Pro starý formát
                        text = st.text_area(f"Krok {i+1}", 
                                          value=krok,
                                          key=f"text_{akce}_{i}",
                                          height=60)
                        st.session_state[f"edit_kroky_{akce}"][i] = text
                
                with col_smazat:
                    st.write("")  # Prázdný řádek pro zarovnání
                    if st.form_submit_button("🗑️", key=f"del_{akce}_{i}", use_container_width=True):
                        kroky_k_smazani.append(i)
                
                st.markdown("---")
            
            # Smazání označených kroků
            for index in sorted(kroky_k_smazani, reverse=True):
                if index < len(st.session_state[f"edit_kroky_{akce}"]):
                    st.session_state[f"edit_kroky_{akce}"].pop(index)
                    st.rerun()
            
            # Přidání nového kroku
            st.write("**Přidat nový krok:**")
            new_desc = st.text_area("Description*", key=f"new_desc_{akce}", height=60, placeholder="Popis kroku...")
            new_exp = st.text_area("Expected*", key=f"new_exp_{akce}", height=60, placeholder="Očekávaný výsledek...")
            
            if st.form_submit_button("➕ Přidat krok", key=f"add_{akce}"):
                if new_desc.strip() and new_exp.strip():
                    st.session_state[f"edit_kroky_{akce}"].append({
                        "description": new_desc.strip(),
                        "expected": new_exp.strip()
                    })
                    st.rerun()
                else:
                    st.warning("Vyplňte obě pole pro krok")
            
            st.markdown("---")
            
            # Tlačítka pro uložení/zrušení
            col_ulozit, col_zrusit = st.columns(2)
            with col_ulozit:
                if st.form_submit_button("💾 Uložit změny", use_container_width=True, type="primary"):
                    if not novy_popis.strip():
                        st.error("Zadejte popis akce")
                    elif not st.session_state[f"edit_kroky_{akce}"]:
                        st.error("Akce musí mít alespoň jeden krok")
                    else:
                        try:
                            success = update_action(
                                akce,
                                novy_popis.strip(),
                                st.session_state[f"edit_kroky_{akce}"].copy()
                            )
                            
                            if success:
                                st.success(f"✅ Akce '{akce}' byla úspěšně upravena a uložena do kroky.json!")
                                st.session_state["edit_akce"] = None
                                if f"edit_kroky_{akce}" in st.session_state:
                                    del st.session_state[f"edit_kroky_{akce}"]
                                refresh_all_data()
                            else:
                                st.error("❌ Akce nebyla nalezena")
                                
                        except Exception as e:
                            st.error(f"❌ Chyba: {e}")
            
            with col_zrusit:
                if st.form_submit_button("❌ Zrušit", use_container_width=True):
                    st.session_state["edit_akce"] = None
                    if f"edit_kroky_{akce}" in st.session_state:
                        del st.session_state[f"edit_kroky_{akce}"]
                    st.rerun()
    
    # Synchronizace s GitHub - PŘESUNUTO SEM
    st.markdown("---")
    st.subheader("🔄 Synchronizace změn s GitHub")
    
    st.write(f"**Stav:** {check_github_status()}")
    
    if st.button("🔄 Synchronizovat změny akcí s GitHub", use_container_width=True):
        try:
            import subprocess
            with st.spinner("Synchronizuji změny akcí s GitHub..."):
                # Nastavení uživatele pokud není nastaven
                try:
                    subprocess.run(["git", "config", "user.email", "testcase-builder@example.com"], 
                                 check=True, cwd=BASE_DIR)
                    subprocess.run(["git", "config", "user.name", "TestCase Builder"], 
                                 check=True, cwd=BASE_DIR)
                except:
                    st.warning("Nelze nastavit Git uživatele, pokračuji...")
                
                # Přidání změn v kroky.json
                result_add = subprocess.run(["git", "add", "kroky.json"], 
                                          capture_output=True, text=True, cwd=BASE_DIR)
                if result_add.returncode != 0:
                    st.error(f"Git add selhal: {result_add.stderr}")
                    st.stop()
                
                # Kontrola zda jsou nějaké změny k commitování
                result_status = subprocess.run(["git", "status", "--porcelain", "kroky.json"], 
                                             capture_output=True, text=True, cwd=BASE_DIR)
                if not result_status.stdout.strip():
                    st.info("Žádné změny v akcích k synchronizaci")
                    st.stop()
                
                # Commit
                result_commit = subprocess.run(
                    ["git", "commit", "-m", "Manuální synchronizace: změny v akcích"], 
                    capture_output=True, text=True, cwd=BASE_DIR
                )
                if result_commit.returncode != 0:
                    st.error(f"Git commit selhal: {result_commit.stderr}")
                    st.stop()
                
                # Pull s rebase
                try:
                    result_pull = subprocess.run(["git", "pull", "--rebase", "--autostash"], 
                                               capture_output=True, text=True, cwd=BASE_DIR)
                    if result_pull.returncode != 0:
                        st.warning(f"Git pull selhal: {result_pull.stderr}")
                except Exception as pull_error:
                    st.warning(f"Git pull selhal: {pull_error}")
                
                # Push
                result_push = subprocess.run(["git", "push"], 
                                           capture_output=True, text=True, cwd=BASE_DIR)
                if result_push.returncode != 0:
                    st.warning(f"Git push selhal: {result_push.stderr}")
                    st.info("Změny byly uloženy lokálně, ale nelze je nahrát na GitHub.")
                else:
                    st.success("✅ Všechny změny akcí byly synchronizovány s GitHub!")
                
                refresh_all_data()
                
        except Exception as e:
            st.error(f"❌ Synchronizace selhala: {e}")
            st.info("Změny byly uloženy lokálně v kroky.json")

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

if st.sidebar.button("✅ Vytvořit projekt"):
    if new_project_name.strip():
        projects = ensure_project(projects, new_project_name.strip())
        selected_project = new_project_name.strip()
        st.rerun()
    else:
        st.sidebar.warning("Zadej název projektu")

if selected_project != "— vyber —" and selected_project in projects:
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Správa projektu")
    
    with st.sidebar.expander("✏️ Upravit název projektu"):
        new_name = st.text_input("Nový název projektu", value=selected_project)
        if st.button("Uložit nový název"):
            if new_name.strip() and new_name != selected_project:
                projects[new_name] = projects.pop(selected_project)
                selected_project = new_name
                save_projects_safely(projects)
                st.success("✅ Název projektu změněn")
                st.rerun()
    
    with st.sidebar.expander("📝 Upravit Subject"):
        current_subject = projects[selected_project].get("subject", "UAT2\\Antosova\\")
        new_subject = st.text_input("Nový Subject", value=current_subject)
        if st.button("Uložit Subject"):
            if new_subject.strip():
                projects[selected_project]["subject"] = new_subject.strip()
                save_projects_safely(projects)
                st.success("✅ Subject změněn")
                st.rerun()
    
    with st.sidebar.expander("🗑️ Smazat projekt"):
        st.warning(f"Chceš smazat projekt '{selected_project}'?")
        if st.button("ANO, smazat projekt"):
            projects.pop(selected_project)
            save_projects_safely(projects)
            st.success(f"✅ Projekt '{selected_project}' smazán")
            st.rerun()

# ---------- Hlavní část ----------
st.title("🧪 TestCase Builder – GUI")

if selected_project == "— vyber —":
    st.info("Vyber nebo vytvoř projekt v levém panelu.")
    st.stop()

if selected_project not in projects:
    st.error(f"Projekt '{selected_project}' nebyl nalezen v datech. Vyber jiný projekt.")
    st.stop()

# NOVÁ HLAVIČKA
st.subheader("📊 Přehled projektu")

# Základní informace pod sebou
st.write(f"**Aktivní projekt:** {selected_project}")
st.write(f"**Subject:** {projects[selected_project].get('subject', 'UAT2\\\\Antosova\\\\')}")
st.write(f"**Počet scénářů:** {len(projects[selected_project].get('scenarios', []))}")
st.write(f"**GitHub stav:** {check_github_status()}")

st.markdown("---")

# ---------- SEZNAM SCÉNÁŘŮ ----------
st.subheader("📋 Seznam scénářů")

scenarios = projects[selected_project].get("scenarios", [])

if scenarios:
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
        
        if st.button("🔢 Přečíslovat scénáře od 001", use_container_width=True):
            scen = projects[selected_project]["scenarios"]
            for i, t in enumerate(sorted(scen, key=lambda x: x["order_no"]), start=1):
                nove_cislo = f"{i:03d}"
                t["order_no"] = i
                
                if "_" in t["test_name"]:
                    parts = t["test_name"].split("_", 1)
                    if parts[0].isdigit() and len(parts[0]) <= 3:
                        t["test_name"] = f"{nove_cislo}_{parts[1]}"
                    else:
                        t["test_name"] = f"{nove_cislo}_{t['test_name']}"
                else:
                    t["test_name"] = f"{nove_cislo}_{t['test_name']}"
            
            projects[selected_project]["scenarios"] = scen
            save_projects_safely(projects)
            st.success("✅ Scénáře a názvy byly přečíslovány.")
            st.rerun()
else:
    st.info("Zatím žádné scénáře. Přidejte první scénář v záložce '➕ Přidat scénáře'.")

st.markdown("---")

# ---------- ANALÝZA SCÉNÁŘŮ ----------
st.subheader("📊 Analýza scénářů")

# Shromáždění dat pro stromovou strukturu
segment_data = {"B2C": {}, "B2B": {}}

for scenario in scenarios:
    segment = scenario.get("segment", "NEZNÁMÝ")
    kanal = scenario.get("kanal", "NEZNÁMÝ")
    
    # SPRÁVNÁ DETEKCE TECHNOLOGIE z názvu test case
    test_name = scenario.get("test_name", "")
    technologie = "DSL"
    
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

# VYTVOŘENÍ STROMOVÉ STRUKTURY
col_b2c, col_b2b = st.columns(2)

with col_b2c:
    with st.expander("👥 B2C", expanded=True):
        if "B2C" in segment_data and segment_data["B2C"]:
            for kanal in segment_data["B2C"]:
                st.markdown(f"<h4 style='margin-bottom: 5px;'>{kanal}</h4>", unsafe_allow_html=True)
                
                for technologie in segment_data["B2C"][kanal]:
                    st.markdown(f"<strong>{technologie}</strong>", unsafe_allow_html=True)
                    
                    for akce in segment_data["B2C"][kanal][technologie]:
                        st.write(f"  • {akce}")
                
                if kanal != list(segment_data["B2C"].keys())[-1]:
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        else:
            st.write("Žádné B2C scénáře")

with col_b2b:
    with st.expander("🏢 B2B", expanded=True):
        if "B2B" in segment_data and segment_data["B2B"]:
            for kanal in segment_data["B2B"]:
                st.markdown(f"<h4 style='margin-bottom: 5px;'>{kanal}</h4>", unsafe_allow_html=True)
                
                for technologie in segment_data["B2B"][kanal]:
                    st.markdown(f"<strong>{technologie}</strong>", unsafe_allow_html=True)
                    
                    for akce in segment_data["B2B"][kanal][technologie]:
                        st.write(f"  • {akce}")
                
                if kanal != list(segment_data["B2B"].keys())[-1]:
                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        else:
            st.write("Žádné B2B scénáře")

st.markdown("---")

# ---------- PŘEHLED KROKŮ PODLE AKCÍ ----------
with st.expander("📋 Přehled kroků podle akcí", expanded=False):
    st.subheader("Kroky dostupné v systému")
    
    steps_data = get_steps()
    
    if not steps_data:
        st.info("Žádné akce nebyly nalezeny.")
    else:
        for akce in sorted(steps_data.keys()):
            obsah_akce = steps_data[akce]
            
            if isinstance(obsah_akce, dict) and "steps" in obsah_akce:
                kroky = obsah_akce.get("steps", [])
                popis_akce = obsah_akce.get("description", "Bez popisu")
            else:
                kroky = obsah_akce if isinstance(obsah_akce, list) else []
                popis_akce = "Bez popisu"
            
            pocet_kroku = len(kroky)
            
            with st.container():
                col_nazev, col_info = st.columns([3, 1])
                
                with col_nazev:
                    st.markdown(f"**{akce}**")
                    st.caption(f"📝 {popis_akce}")
                
                with col_info:
                    st.caption(f"{pocet_kroku} kroků")
                
                with st.expander(f"👀 Zobrazit kroky ({pocet_kroku})", expanded=False):
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
                
                st.markdown("---")

st.markdown("---")

# VYTVOŘÍME ZÁLOŽKY PRO SPRÁVU SCÉNÁŘŮ A AKCÍ
tab1, tab2, tab3, tab4 = st.tabs(["➕ Přidat scénáře", "🔧 Správa akcí", "📤 Export", "🔍 Diagnostika"])

with tab1:
    # ---------- Přidání scénáře ----------
    st.subheader("➕ Přidat nový scénář")
    steps_data = get_steps()
    akce_list = list(steps_data.keys())

    with st.form("add_scenario"):
        veta = st.text_area("Věta (požadavek)", height=100, placeholder="Např.: Aktivuj DSL na B2C přes kanál SHOP …")
        akce = st.selectbox("Akce (z kroky.json)", options=akce_list)
        
        kroky_pro_akci = get_steps_from_action(akce, steps_data)
        pocet_kroku = len(kroky_pro_akci)
        
        auto_complexity = get_automatic_complexity(pocet_kroku)
        
        colp, colc = st.columns(2)
        with colp:
            priority = st.selectbox("Priorita", options=list(PRIORITY_MAP.values()), index=1)
        with colc:
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
                        scenario["veta"] = veta.strip()
                        scenario["akce"] = akce
                        scenario["priority"] = priority
                        scenario["complexity"] = complexity
                        scenario["kroky"] = get_steps_from_action(akce, steps_data)
                        
                        # OPRAVA: Zachováme strukturu názvu, pouze aktualizujeme větu
                        current_name_parts = scenario["test_name"].split("_")
                        if len(current_name_parts) >= 5:
                            # Formát: 001_SHOP_B2C_DSL_věta
                            # Zachováme číslo, kanál, segment, technologii a aktualizujeme větu
                            new_test_name = f"{current_name_parts[0]}_{current_name_parts[1]}_{current_name_parts[2]}_{current_name_parts[3]}_{veta.strip()}"
                        else:
                            # Pokud formát není standardní, vytvoříme nový název
                            segment, kanal, technologie = parse_veta(veta.strip())
                            new_test_name = f"{current_name_parts[0]}_{kanal}_{segment}_{technologie}_{veta.strip()}"
                        
                        scenario["test_name"] = new_test_name
                        
                        projects[selected_project]["scenarios"][scenario_index] = scenario
                        save_projects_safely(projects)
                        st.success("✅ Změny uloženy a propsány do projektu.")
                        st.rerun()

    st.markdown("---")

    # ---------- Smazání scénáře ----------
    st.subheader("🗑️ Smazání scénáře")
    if not scenarios:
        st.info("Zatím žádné scénáře pro smazání.")
    else:
        to_delete = st.selectbox(
            "Vyber scénář ke smazání:",
            options=["— žádný —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
            index=0,
            key="delete_selector"
        )
        if to_delete != "— žádný —":
            idx = int(to_delete.split(" - ")[0])
            if st.button("🗑️ Potvrdit smazání scénáře"):
                scen = [t for t in projects[selected_project]["scenarios"] if t.get("order_no") != idx]
                for i, t in enumerate(scen, start=1):
                    t["order_no"] = i
                projects[selected_project]["scenarios"] = scen
                save_projects_safely(projects)
                st.success("Scénář smazán a pořadí přepočítáno.")
                st.rerun()

with tab2:
    st.subheader("🔧 Správa akcí a kroků")
    st.info("Zde můžete spravovat všechny akce a jejich kroky. Změny se projeví okamžitě v celé aplikaci.")
    
    sprava_akci()

with tab3:
    st.subheader("📤 Export projektu")
    
    st.info("Exportuje všechny scénáře projektu do Excelu pro stažení do PC.")
    
    if st.button("💾 Exportovat do Excelu", use_container_width=True, type="primary"):
        try:
            with st.spinner("Exportuji do Excelu..."):
                # Získání dat z exportu
                export_result = export_to_excel(selected_project, projects)
                
                # Vytvoření bezpečného názvu souboru
                safe_project_name = "".join(c for c in selected_project if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_project_name = safe_project_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                file_name = f"testcases_{safe_project_name}.xlsx"
                
                # Zpracování výsledku exportu
                if isinstance(export_result, str):
                    # ✅ Export do dočasného souboru
                    with open(export_result, "rb") as file:
                        file_data = file.read()
                    
                    st.success("✅ Export hotový! Soubor je připraven ke stažení.")
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Stáhnout Excel soubor",
                        data=file_data,
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    # Úklid - smazání dočasného souboru
                    try:
                        import os
                        os.unlink(export_result)
                    except:
                        pass
                        
                else:
                    # ✅ Export do BytesIO (paměť)
                    st.success("✅ Export hotový! Soubor je připraven ke stažení.")
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Stáhnout Excel soubor",
                        data=export_result.getvalue(),
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
        except Exception as e:
            st.error(f"Export selhal: {e}")
            
            # ✅ JEDNODUŠŠÍ ALTERNATIVA - přímý export bez souboru
            try:
                st.info("🔄 Zkouším alternativní export...")
                
                projects_data = get_projects()
                project_data = projects_data[selected_project]
                rows = []

                for tc in project_data["scenarios"]:
                    for i, krok in enumerate(tc.get("kroky", []), start=1):
                        desc = ""
                        exp = ""

                        if isinstance(krok, dict):
                            desc = krok.get("description", "")
                            exp = krok.get("expected", "")
                        elif isinstance(krok, str):
                            desc = krok
                            exp = ""

                        rows.append({
                            "Project": selected_project,
                            "Subject": project_data.get("subject", "UAT2\\Antosova\\"),
                            "System/Application": "Siebel_CZ",
                            "Description": f"Segment: {tc['segment']}\nKanál: {tc['kanal']}\nAkce: {tc['akce']}",
                            "Type": "Manual",
                            "Test Phase": "4-User Acceptance",
                            "Test: Test Phase": "4-User Acceptance",
                            "Test Priority": tc["priority"],
                            "Test Complexity": tc["complexity"],
                            "Test Name": tc["test_name"],
                            "Step Name (Design Steps)": str(i),
                            "Description (Design Steps)": desc,
                            "Expected (Design Steps)": exp
                        })

                df = pd.DataFrame(rows)
                
                # ✅ PŘÍMÝ EXPORT DO BYTESIO
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Test Cases')
                output.seek(0)
                
                # Bezpečný název souboru
                safe_name = "".join(c for c in selected_project if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                file_name = f"testcases_{safe_name}.xlsx"
                
                st.success("✅ Alternativní export úspěšný! Soubor je připraven ke stažení.")
                
                st.download_button(
                    label="⬇️ Stáhnout Excel soubor (alternativní metoda)",
                    data=output.getvalue(),
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            except Exception as alt_error:
                st.error(f"Alternativní export také selhal: {alt_error}")
    
    st.markdown("---")
    
    st.subheader("ℹ️ Informace o exportu")
    st.write("""
    **Co export obsahuje:**
    - Všechny scénáře projektu
    - Kroky jednotlivých scénářů
    - Metadata (priorita, komplexita, segment, kanál)
    
    **Co se stane po exportu:**
    1. Data se exportují přímo do paměti
    2. Soubor je připraven ke stažení
    3. **Žádné ukládání na disk** - pouze download
    """)


with tab4:
    st.subheader("🔍 Diagnostika systému")
    st.info("Tato záložka slouží pro diagnostiku problémů se synchronizací a ukládáním dat.")
    
    if st.button("🔄 Spustit diagnostiku", use_container_width=True):
        import subprocess
        import os
        
        st.markdown("---")
        st.subheader("📊 Výsledky diagnostiky")
        
        # 1. Informace o kroky.json
        st.write("### 📁 Informace o kroky.json")
        kroky_cesta = BASE_DIR / "kroky.json"
        st.write(f"**Cesta:** `{kroky_cesta}`")
        st.write(f"**Existuje:** `{kroky_cesta.exists()}`")
        
        if kroky_cesta.exists():
            st.write(f"**Velikost:** `{os.path.getsize(kroky_cesta)} bytes`")
            st.write(f"**Poslední změna:** `{datetime.fromtimestamp(os.path.getmtime(kroky_cesta))}`")
            
            # Načteme a zobrazíme počet akcí
            try:
                with open(kroky_cesta, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.write(f"**Počet akcí v souboru:** `{len(data)}`")
                st.write("**Názvy akcí:**")
                for akce in list(data.keys())[:10]:  # Prvních 10 akcí
                    st.write(f"  - {akce}")
                if len(data) > 10:
                    st.write(f"  - ... a dalších {len(data) - 10} akcí")
            except Exception as e:
                st.error(f"Chyba při čtení kroky.json: {e}")
        
        # 2. Git stav
        st.markdown("---")
        st.write("### 🔧 Git stav")
        
        # Git status kroky.json
        result_status = subprocess.run(["git", "status", "-s", "kroky.json"], 
                                     capture_output=True, text=True, cwd=BASE_DIR)
        status_output = result_status.stdout.strip()
        st.write(f"**Status kroky.json:** `{status_output or 'Žádné změny'}`")
        
        # Git diff kroky.json
        result_diff = subprocess.run(["git", "diff", "kroky.json"], 
                                   capture_output=True, text=True, cwd=BASE_DIR)
        diff_output = result_diff.stdout.strip()
        if diff_output:
            st.write("**Změny v kroky.json:**")
            st.code(diff_output)
        else:
            st.write("**Žádné změny v kroky.json podle Gitu**")
        
        # Celkový Git status
        result_all = subprocess.run(["git", "status", "-s"], 
                                  capture_output=True, text=True, cwd=BASE_DIR)
        all_changes = result_all.stdout.strip()
        if all_changes:
            st.write("**Všechny změny v repozitáři:**")
            st.code(all_changes)
        else:
            st.write("**Žádné změny v celém repozitáři**")
        
        # 3. Test synchronizace
        st.markdown("---")
        st.write("### 🧪 Test synchronizace")
        
        # Vytvoříme testovací změnu
        test_content = "Testovací změna pro diagnostiku"
        try:
            # Přidáme komentář do kroky.json
            with open(kroky_cesta, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                data['_diagnostika_test'] = test_content
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
            
            st.success("✅ Testovací změna přidána do kroky.json")
            
            # Zkontrolujeme Git status
            result_test = subprocess.run(["git", "status", "-s", "kroky.json"], 
                                       capture_output=True, text=True, cwd=BASE_DIR)
            if result_test.stdout.strip():
                st.success("✅ Git detekuje změny v kroky.json")
                st.code(result_test.stdout.strip())
                
                # Ukážeme jak synchronizovat
                st.write("**Návod na synchronizaci:**")
                st.code("""
git add kroky.json
git commit -m "Testovací změna"
git push
                """)
            else:
                st.error("❌ Git NEDETEKUJE změny v kroky.json!")
                st.info("""
**Možné příčiny:**
1. Soubor kroky.json není v Git repozitáři
2. Gitignore blokuje soubor
3. Problém s oprávněními
                """)
            
            # Uklidíme - odstraníme testovací změnu
            with open(kroky_cesta, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                if '_diagnostika_test' in data:
                    del data['_diagnostika_test']
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.truncate()
            
        except Exception as e:
            st.error(f"❌ Test selhal: {e}")
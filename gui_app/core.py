import json
import pandas as pd
import copy
import subprocess
from pathlib import Path

# ---------- Cesty ----------
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_PATH = BASE_DIR / "projects.json"
KROKY_PATH = BASE_DIR / "kroky.json"
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# ---------- Statické mapy ----------
PRIORITY_MAP = {
    "1": "1-High",
    "2": "2-Medium", 
    "3": "3-Low"
}

COMPLEXITY_MAP = {
    "1": "1-Giant",
    "2": "2-Huge",
    "3": "3-Big",
    "4": "4-Medium",
    "5": "5-Low"
}

# ---------- Funkce práce se soubory ----------
def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Funkce pro správu kroků ----------
def save_kroky_data(data):
    """Uloží data do kroky.json a provede git commit + push"""
    try:
        # Uložení do souboru
        save_json(KROKY_PATH, data)
        
        # Git operace
        subprocess.run(["git", "add", str(KROKY_PATH)], check=True)
        subprocess.run(["git", "commit", "-m", "Auto update kroky.json"], check=True)
        
        # Nejprve pull s rebase
        try:
            subprocess.run(["git", "pull", "--rebase"], check=True)
        except subprocess.CalledProcessError:
            print("⚠️ Git pull --rebase selhal, pokračujeme bez něj")
            
        subprocess.run(["git", "push"], check=True)
        print("✅ Kroky.json uložen a změny nahrány na GitHub")
        
    except Exception as e:
        print(f"⚠️ Git operace selhala: {e}")
        # I když git selže, soubor se uloží lokálně
        save_json(KROKY_PATH, data)

def add_new_action(akce_nazev, akce_popis, kroky):
    """Přidá novou akci do kroky.json"""
    kroky_data = get_steps()
    
    kroky_data[akce_nazev] = {
        "description": akce_popis,
        "steps": kroky
    }
    
    save_kroky_data(kroky_data)
    return True

def update_action(akce_nazev, akce_popis, kroky):
    """Aktualizuje existující akci v kroky.json"""
    kroky_data = get_steps()
    
    if akce_nazev in kroky_data:
        kroky_data[akce_nazev] = {
            "description": akce_popis,
            "steps": kroky
        }
        
        save_kroky_data(kroky_data)
        return True
    else:
        return False

def delete_action(akce_nazev):
    """Smaže akci z kroky.json"""
    kroky_data = get_steps()
    
    if akce_nazev in kroky_data:
        del kroky_data[akce_nazev]
        save_kroky_data(kroky_data)
        return True
    else:
        return False

# ---------- Nová funkce načítání kroků ----------
def get_steps():
    """Vrací novou kopii dat z kroky.json - zachovává nový formát"""
    if not KROKY_PATH.exists():
        return {}
    with open(KROKY_PATH, "r", encoding="utf-8") as f:
        return copy.deepcopy(json.load(f))

# ---------- Pomocná funkce pro získání kroků z akce ----------
def get_steps_from_action(akce, kroky_data):
    """Získá kroky z akce bez ohledu na formát"""
    if akce not in kroky_data:
        return []
    
    obsah = kroky_data[akce]
    if isinstance(obsah, dict) and "steps" in obsah:
        # Nový formát: {"description": "...", "steps": [...]}
        return obsah["steps"]
    elif isinstance(obsah, list):
        # Starý formát: [...]
        return obsah
    else:
        return []

# ---------- Generování názvu test casu ----------
def parse_veta(veta: str):
    """Z věty vytáhne klíčové údaje: segment, kanál, technologii"""
    veta_low = veta.lower()
    segment = "B2C" if "b2c" in veta_low else "B2B" if "b2b" in veta_low else "NA"
    kanal = "SHOP" if "shop" in veta_low else "IL" if "il" in veta_low else "NA"

    # ROZŠÍŘENÉ A OPRAVENÉ MAPOVÁNÍ TECHNOLOGIÍ
    technologie_map = {
        "dsl": "DSL",
        "vdsl": "DSL", 
        "adsl": "DSL",
        "fwa bi": "FWA_BI",
        "fwa indoor": "FWA_BI",
        "fwa bisi": "FWA_BISI",
        "fwa outdoor": "FWA_BISI",
        "fiber": "FIBER",
        "optin": "FIBER",
        "opticky internet": "FIBER",
        "optika": "FIBER",
        "ftth": "FIBER",
        "cable": "CABLE",
        "hlas": "HLAS",
        "hlasovy": "HLAS",
        "mobil": "HLAS",
        "next tarif": "HLAS",
        "tarif": "HLAS",
        "voice": "HLAS"
    }
    
    technologie = "X"
    
    # DŮLEŽITÉ: Nejprve kontrolujeme delší řetězce, pak kratší
    for k, v in sorted(technologie_map.items(), key=lambda x: len(x[0]), reverse=True):
        if k in veta_low:
            technologie = v
            break
            
    return segment, kanal, technologie

# ---------- Generování test casu ----------
def generate_testcase(project, veta, akce, priority, complexity, kroky_data, projects_data):
    """Vytvoří nový test case a uloží ho do projektu"""
    if project not in projects_data:
        projects_data[project] = {"next_id": 1, "subject": "UAT2\\Antosova\\", "scenarios": []}
    
    project_data = projects_data[project]
    
    # AUTOMATICKÉ ČÍSLOVÁNÍ - najdeme nejvyšší existující order_no
    if project_data["scenarios"]:
        max_order = max([scenario["order_no"] for scenario in project_data["scenarios"]])
        order_no = max_order + 1
    else:
        order_no = 1
    
    project_data["next_id"] = order_no + 1
    nove_cislo = f"{order_no:03d}"

    segment, kanal, technologie = parse_veta(veta)
    test_name = f"{nove_cislo}_{kanal}_{segment}_{technologie}_{veta.strip()}"

    # Načtení kroků podle akce - POUŽÍVÁME POMOCNOU FUNKCI
    kroky = get_steps_from_action(akce, kroky_data)

    tc = {
        "order_no": order_no,
        "test_name": test_name,
        "akce": akce,
        "segment": segment,
        "kanal": kanal,
        "priority": priority,
        "complexity": complexity,
        "veta": veta,
        "kroky": copy.deepcopy(kroky)  # Hluboká kopie kroků
    }

    project_data["scenarios"].append(tc)
    save_json(PROJECTS_PATH, projects_data)
    return tc

# ---------- Export do Excelu ----------
def export_to_excel(project_name, projects_data):
    """Exportuje test casy daného projektu do Excelu a provede git push"""
    project_data = projects_data[project_name]
    rows = []

    for tc in project_data["scenarios"]:
        # Debug info
        print(f"Export scénáře: Akce='{tc['akce']}', Počet kroků={len(tc.get('kroky', []))}")
        
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
                "Project": project_name,
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
    output_path = EXPORT_DIR / f"testcases_{project_name.replace(' ', '_')}.xlsx"
    df.to_excel(output_path, index=False)

    # Git operace (bez pádu při chybě)
    try:
        subprocess.run(["git", "add", str(output_path)], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto export {project_name}"], check=True)
        
        # Nejprve zkusíme pull s rebase, ale pokud selže, pokračujeme
        try:
            subprocess.run(["git", "pull", "--rebase"], check=True)
        except subprocess.CalledProcessError:
            print("⚠️ Git pull --rebase selhal, pokračujeme bez něj")
            
        subprocess.run(["git", "push"], check=True)
        print("✅ Export a git push úspěšný")
    except Exception as e:
        print("⚠️ Git operace selhala:", e)

    print(f"✅ Exportováno do: {output_path}")
    return output_path
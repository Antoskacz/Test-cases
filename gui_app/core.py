import json
import pandas as pd
import copy
import subprocess
from pathlib import Path

# ---------- Cesty ----------
BASE_DIR = Path(__file__).resolve().parent.parent
USERS_DIR = BASE_DIR / "users"
USERS_DIR.mkdir(exist_ok=True)

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

# ---------- Uživatelské cesty ----------
def get_user_projects_path(username: str) -> Path:
    user_dir = USERS_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir / "projects.json"

def get_user_kroky_path(username: str) -> Path:
    user_dir = USERS_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir / "kroky.json"

def get_user_export_dir(username: str) -> Path:
    user_export_dir = USERS_DIR / username / "exports"
    user_export_dir.mkdir(exist_ok=True)
    return user_export_dir

# ---------- Funkce práce se soubory ----------
def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Načítání kroků ----------
def get_steps(username: str):
    kroky_path = get_user_kroky_path(username)
    return load_json(kroky_path)

# ---------- Parsování věty ----------
def parse_veta(veta: str):
    veta_low = veta.lower()
    segment = "B2C" if "b2c" in veta_low else "B2B" if "b2b" in veta_low else "NA"
    kanal = "SHOP" if "shop" in veta_low else "IL" if "il" in veta_low else "NA"

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
        "opticka": "FIBER",
        "ftth": "FIBER",
        "cable": "CABLE",
        "kabelova": "CABLE",
        "hlas": "HLAS",
        "hlasovy": "HLAS",
        "mobil": "HLAS", 
        "next tarif": "HLAS",
        "tarif": "HLAS",
        "voice": "HLAS"
    }
    
    technologie = "NA"
    for k, v in sorted(technologie_map.items(), key=lambda x: len(x[0]), reverse=True):
        if k in veta_low:
            technologie = v
            break
            
    return segment, kanal, technologie

# ---------- Generování test casu ----------
def generate_testcase(username: str, project: str, veta: str, akce: str, priority: str, complexity: str, kroky_data: dict, projects_data: dict):
    if project not in projects_data:
        projects_data[project] = {"next_id": 1, "subject": "UAT2\\Antosova\\", "scenarios": []}
    
    project_data = projects_data[project]
    
    # Automatické číslování
    if project_data["scenarios"]:
        max_order = max([scenario["order_no"] for scenario in project_data["scenarios"]])
        order_no = max_order + 1
    else:
        order_no = 1
    
    project_data["next_id"] = order_no + 1
    
    nove_cislo = f"{order_no:03d}"

    segment, kanal, technologie = parse_veta(veta)
    test_name = f"{nove_cislo}_{kanal}_{segment}_{technologie}_{veta.strip().replace(' ', '_')}"

    # Načtení kroků podle akce - OPRAVENÉ
    if akce in kroky_data:
        kroky = kroky_data[akce]
        # Pokud jsou kroky ve slovníku, vezmi pole "steps"
        if isinstance(kroky, dict) and "steps" in kroky:
            kroky = copy.deepcopy(kroky["steps"])
        else:
            kroky = copy.deepcopy(kroky)
    else:
        kroky = []
        print(f"⚠️ Akce '{akce}' nebyla nalezena v kroky.json")
    
    tc = {
        "order_no": order_no,
        "test_name": test_name,
        "akce": akce,
        "segment": segment,
        "kanal": kanal,
        "priority": priority,
        "complexity": complexity,
        "veta": veta,
        "kroky": kroky
    }

    project_data["scenarios"].append(tc)
    
    # Uložení pod uživatelskou složku
    projects_path = get_user_projects_path(username)
    save_json(projects_path, projects_data)
    return tc

# ---------- Export do Excelu ----------
def export_to_excel(username: str, project_name: str, projects_data: dict):
    if project_name not in projects_data:
        raise ValueError(f"Projekt {project_name} neexistuje")
        
    project_data = projects_data[project_name]
    rows = []

    for tc in project_data["scenarios"]:
        for i, krok in enumerate(tc.get("kroky", []), start=1):
            desc = ""
            exp = ""

            if isinstance(krok, dict):
                desc = krok.get('description', '')
                exp = krok.get('expected', '')
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

    if not rows:
        raise ValueError("Žádné scénáře k exportu")

    df = pd.DataFrame(rows)
    output_path = get_user_export_dir(username) / f"testcases_{project_name.replace(' ', '_')}.xlsx"
    df.to_excel(output_path, index=False)

    # Git operace
    try:
        subprocess.run(["git", "add", str(output_path)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Auto export {project_name} pro {username}"], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print("✅ Export a git push úspěšný")
    except Exception as e:
        print("⚠️ Git operace selhala:", e)

    print(f"✅ Exportováno do: {output_path}")
    return output_path
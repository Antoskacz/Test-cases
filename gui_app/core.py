import json
import pandas as pd
import copy
import subprocess
from pathlib import Path

# ---------- Cesty ----------
BASE_DIR = Path(__file__).resolve().parent
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

# ---------- Funkce práce se soubory ----------
def load_json(path: Path):
    """Načte JSON soubor, vrátí prázdný dict pokud neexistuje"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Chyba při načítání {path}: {e}")
        return {}

def save_json(path: Path, data):
    """Uloží data do JSON souboru"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Chyba při ukládání {path}: {e}")
        return False

# ---------- Načítání kroků ----------
def get_steps():
    """Vrací novou kopii dat z kroky.json"""
    return load_json(KROKY_PATH)

# ---------- Parsování věty ----------
def parse_veta(veta: str):
    """Z věty vytáhne klíčové údaje: segment, kanál, technologii"""
    veta_low = veta.lower()
    segment = "B2C" if "b2c" in veta_low else "B2B" if "b2b" in veta_low else "NA"
    kanal = "SHOP" if "shop" in veta_low else "IL" if "il" in veta_low else "NA"

    technologie_map = {
        "dsl": "DSL",
        "fwa bi": "FWA_BI", 
        "fwa bisi": "FWA_BISI",
        "fiber": "FIBER",
        "cable": "CABLE",
        "hlas": "HLAS",
        "hlasovy": "HLAS"
    }
    technologie = "NA"
    for k, v in technologie_map.items():
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
    order_no = project_data["next_id"]
    nove_cislo = f"{order_no:03d}"

    segment, kanal, technologie = parse_veta(veta)
    test_name = f"{nove_cislo}_{kanal}_{segment}_{technologie}_{veta.strip().replace(' ', '_')}"

    # Načtení kroků podle akce
    if akce in kroky_data:
        kroky = copy.deepcopy(kroky_data[akce])
    else:
        kroky = []

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
    project_data["next_id"] += 1
    save_json(PROJECTS_PATH, projects_data)
    return tc

# ---------- Export do Excelu ----------
def export_to_excel(project_name, projects_data):
    """Exportuje test casy daného projektu do Excelu"""
    if project_name not in projects_data:
        raise ValueError(f"Projekt {project_name} neexistuje")
        
    project_data = projects_data[project_name]
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
    output_path = EXPORT_DIR / f"testcases_{project_name.replace(' ', '_')}.xlsx"
    df.to_excel(output_path, index=False)

    # Git operace (volitelné)
    try:
        subprocess.run(["git", "add", str(output_path)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Auto export {project_name}"], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print("✅ Export a git push úspěšný")
    except Exception as e:
        print("⚠️ Git operace selhala:", e)

    print(f"✅ Exportováno do: {output_path}")
    return output_path
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

# ---------- Nová funkce načítání kroků ----------
def get_steps():
    """Vrací novou kopii dat z kroky.json (každé volání načte čerstvá data)"""
    if not KROKY_PATH.exists():
        return {}
    with open(KROKY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return copy.deepcopy(data)  # hluboká kopie celé struktury

# ---------- Generování názvu test casu ----------
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
    project_data = projects_data[project]
    order_no = project_data["next_id"]
    nove_cislo = f"{order_no:03d}"

    segment, kanal, technologie = parse_veta(veta)
    test_name = f"{nove_cislo}_{kanal}_{segment}_{technologie}_{veta.strip().replace(' ', '_')}"

    # --- přesné přiřazení kroků podle akce z roletky ---
    if akce in kroky_data:
        kroky = copy.deepcopy(kroky_data[akce])
        print(f"✅ Načteny kroky pro akci: {akce} ({len(kroky)} kroků)")
    else:
        print(f"⚠️ Akce '{akce}' nebyla nalezena v kroky.json. Používám prázdný seznam.")
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
                "Step #": i,
                "Step Name (Design Steps)": f"{tc['test_name']}_STEP{i}",
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
        subprocess.run(["git", "pull", "--rebase"], check=True)
        subprocess.run(["git", "push"], check=True)
    except Exception as e:
        print("⚠️ Git operace selhala:", e)

    print(f"✅ Exportováno do: {output_path}")
    return output_path
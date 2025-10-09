import json
import pandas as pd
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORTS_DIR = BASE_DIR / "exports"
PROJECTS_PATH = BASE_DIR / "projekty.json"
KROKY_PATH = BASE_DIR / "kroky.json"

SYSTEM_APPLICATION = "Siebel_CZ"
TYPE = "Manual"
TEST_PHASE = "4-User Acceptance"
TEST_TEST_PHASE = "4-User Acceptance"
PRIORITY_MAP = {"1": "1-High", "2": "2-Medium", "3": "3-Low"}
COMPLEXITY_MAP = {"1": "1-Giant", "2": "2-Huge", "3": "3-Big", "4": "4-Medium", "5": "5-Low"}


def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_kanal(veta):
    t = veta.lower()
    if "shop" in t:
        return "SHOP"
    if "il" in t:
        return "IL"
    return "UNKNOWN"


def extract_segment(veta):
    t = veta.lower()
    if "b2c" in t:
        return "B2C"
    if "b2b" in t:
        return "B2B"
    return "UNKNOWN"


def extract_service(veta):
    t = veta.lower()
    if "hlas" in t or "voice" in t:
        return "HLAS"
    if "fwa" in t and "bisi" in t:
        return "FWA_BISI"
    if "fwa" in t and "bi" in t:
        return "FWA_BI"
    for key in ["dsl", "fiber", "cable"]:
        if key in t:
            return key.upper()
    if "fwa" in t:
        return "FWA"
    return "UNKNOWN"


def build_test_name(poradi: int, veta: str) -> str:
    kanal = extract_kanal(veta)
    segment = extract_segment(veta)
    service = extract_service(veta)
    return f"{poradi:03d}_{kanal}_{segment}_{service}_{veta.strip().capitalize()}"


def generate_testcase(project, veta, akce, priority, complexity, kroky_data, projects_data):
    if project not in projects_data:
        projects_data[project] = {"next_id": 1, "subject": "UAT2\\Antosova\\", "scenarios": []}

    pid = projects_data[project]["next_id"]
    projects_data[project]["next_id"] += 1

    test_name = build_test_name(pid, veta)
    kanal = extract_kanal(veta)
    segment = extract_segment(veta)

    tc = {
        "order_no": pid,
        "test_name": test_name,
        "akce": akce,
        "kanal": kanal,
        "segment": segment,
        "priority": priority,
        "complexity": complexity,
        "veta": veta,
        "kroky": kroky_data.get(akce, []).copy(),
    }

    projects_data[project]["scenarios"].append(tc)
    save_json(PROJECTS_PATH, projects_data)
    return tc


def export_to_excel(project, projects_data):
    EXPORTS_DIR.mkdir(exist_ok=True)
    output_path = EXPORTS_DIR / f"testcases_{project.replace(' ', '_')}.xlsx"

    scenarios = sorted(projects_data[project]["scenarios"], key=lambda x: x["order_no"])
    subject = projects_data[project].get("subject", "UAT2\\Antosova\\")

    rows = []
    for new_order, tc in enumerate(scenarios, start=1):
        new_test_name = build_test_name(new_order, tc.get("veta", tc["test_name"]))
        for i, krok in enumerate(tc["kroky"], start=1):
            rows.append({
                "Project": project,
                "System/Application": SYSTEM_APPLICATION,
                "Subject": subject,
                "Description": f"Segment: {tc['segment']}\nKanal: {tc['kanal']}\nAkce: {tc['akce']}",
                "Type": TYPE,
                "Test Phase": TEST_PHASE,
                "Test: Test Phase": TEST_TEST_PHASE,
                "Test Priority": tc["priority"],
                "Test Complexity": tc["complexity"],
                "Test Name": new_test_name,
                "Step Name (Design Steps)": str(i),
                "Description (Design Steps)": krok.get("description", ""),
                "Expected (Design Steps)": krok.get("expected", "TODO: doplnit očekávání")
            })

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)

    # Git push
    try:
        subprocess.run(["git", "add", str(output_path)], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto export {project}"], check=False)
        subprocess.run(["git", "pull", "--rebase"], check=False)
        subprocess.run(["git", "push"], check=True)
        print(f"✅ Exportováno a nahráno: {output_path}")
    except Exception as e:
        print(f"⚠️ Git push selhal: {e}")

    return output_path

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
        print(f"✅ Kroky.json uložen lokálně ({len(data)} akcí)")
        
        # Git operace - s lepší chybovou handling
        try:
            # Nejprve zkontrolujeme jestli jsme v git repozitáři
            check_git = subprocess.run(["git", "status"], capture_output=True, text=True)
            if "not a git repository" in check_git.stderr:
                print("⚠️ Není Git repozitář - přeskočeno")
                return
            
            # Nastavení uživatele pokud není nastaven
            try:
                subprocess.run(["git", "config", "user.email", "testcase-builder@example.com"], check=True)
                subprocess.run(["git", "config", "user.name", "TestCase Builder"], check=True)
                print("✅ Git uživatel nastaven")
            except:
                print("⚠️ Nelze nastavit Git uživatele")
            
            # Přidání souboru
            result_add = subprocess.run(["git", "add", str(KROKY_PATH)], 
                                      capture_output=True, text=True)
            if result_add.returncode != 0:
                print(f"⚠️ Git add selhal: {result_add.stderr}")
                return
            print("✅ Git add úspěšný")
            
            # Commit - pouze pokud jsou změny
            result_status = subprocess.run(["git", "status", "--porcelain"], 
                                         capture_output=True, text=True)
            if not result_status.stdout.strip():
                print("ℹ️ Žádné změny k commitování")
                return
            
            result_commit = subprocess.run(["git", "commit", "-m", "Auto update: změny v akcích a krocích"], 
                                         capture_output=True, text=True)
            if result_commit.returncode != 0:
                print(f"⚠️ Git commit selhal: {result_commit.stderr}")
                return
            print("✅ Git commit úspěšný")
            
            # Nejprve pull s rebase
            try:
                result_pull = subprocess.run(["git", "pull", "--rebase", "--autostash"], 
                                           capture_output=True, text=True)
                if result_pull.returncode != 0:
                    print(f"⚠️ Git pull selhal: {result_pull.stderr}")
            except Exception as pull_error:
                print(f"⚠️ Git pull selhal: {pull_error}")
                
            # Push
            result_push = subprocess.run(["git", "push"], 
                                       capture_output=True, text=True)
            if result_push.returncode != 0:
                print(f"⚠️ Git push selhal: {result_push.stderr}")
                return
            
            print("✅ Kroky.json uložen a změny nahrány na GitHub")
            
        except Exception as git_error:
            print(f"⚠️ Git operace selhala: {git_error}")
            print("ℹ️ Data byla uložena lokálně, ale GitHub synchronizace selhala")
            
    except Exception as e:
        print(f"❌ Chyba při ukládání: {e}")
        # I když vše selže, soubor se uloží lokálně
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

    # Git operace s lepším error handling
    try:
        # Kontrola git repozitáře
        check_result = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=BASE_DIR)
        if "not a git repository" in check_result.stderr:
            print("⚠️ Není Git repozitář - export pouze lokální")
            return output_path

        # Nastavení uživatele
        try:
            subprocess.run(["git", "config", "user.email", "testcase-builder@example.com"], 
                         check=True, cwd=BASE_DIR)
            subprocess.run(["git", "config", "user.name", "TestCase Builder"], 
                         check=True, cwd=BASE_DIR)
        except:
            print("⚠️ Nelze nastavit Git uživatele")

        # Přidání souboru
        subprocess.run(["git", "add", str(output_path)], check=True, cwd=BASE_DIR)
        
        # Commit pouze pokud jsou změny
        status_result = subprocess.run(["git", "status", "--porcelain"], 
                                     capture_output=True, text=True, cwd=BASE_DIR)
        if status_result.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"Auto export {project_name}"], 
                         check=True, cwd=BASE_DIR)
            
            # Pull s autostash
            try:
                subprocess.run(["git", "pull", "--rebase", "--autostash"], 
                             check=True, cwd=BASE_DIR)
            except subprocess.CalledProcessError:
                print("⚠️ Git pull selhal, pokračujeme bez něj")
                
            # Push
            subprocess.run(["git", "push"], check=True, cwd=BASE_DIR)
            print("✅ Export a git push úspěšný")
        else:
            print("ℹ️ Žádné změny k commitování")
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git operace selhala: {e}")
        print("ℹ️ Export byl uložen lokálně")
    except Exception as e:
        print(f"⚠️ Neočekávaná chyba: {e}")

    print(f"✅ Exportováno do: {output_path}")
    return output_path



# ---------- Funkce pro opravu duplicitních kroků ----------
def oprav_duplicitni_kroky():
    """Opraví duplicitní kroky v kroky.json"""
    kroky_data = get_steps()
    opraveno = False
    
    for akce, kroky in kroky_data.items():
        puvodni_pocet = len(kroky)
        
        # Odstranění duplicitních kroků
        jedinecne_kroky = []
        videne_popisy = set()
        
        for krok in kroky:
            popis = krok.get('description', '')
            # Pokud jsme tento popis ještě neviděli, přidáme krok
            if popis not in videne_popisy:
                jedinecne_kroky.append(krok)
                videne_popisy.add(popis)
        
        nove_kroky = jedinecne_kroky
        novy_pocet = len(nove_kroky)
        
        if puvodni_pocet != novy_pocet:
            kroky_data[akce] = nove_kroky
            opraveno = True
            print(f"🔧 Opravena akce '{akce}': {puvodni_pocet} → {novy_pocet} kroků")
    
    if opraveno:
        # Ulož opravená data
        with open(KROKY_PATH, 'w', encoding='utf-8') as f:
            json.dump(kroky_data, f, ensure_ascii=False, indent=2)
        print("✅ Kroky.json byl opraven!")
    else:
        print("✅ Žádné duplicity nebyly nalezeny.")
    
    return kroky_data
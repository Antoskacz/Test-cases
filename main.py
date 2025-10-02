
import json
import pandas as pd
from pathlib import Path

KROKY_PATH = Path("kroky.json")

def nacti_kroky():
    with open(KROKY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def uloz_kroky(kroky):
    with open(KROKY_PATH, "w", encoding="utf-8") as f:
        json.dump(kroky, f, ensure_ascii=False, indent=2)

def generuj_testcase(veta, kroky_data):
    # Zjednodušený rozklad věty
    slova = veta.lower().split()
    akce = next((k for k in kroky_data if k.lower() in veta.lower()), None)
    if not akce:
        print("‼️ Nenalezena žádná známá akce ve větě.")
        return None, []

    test_name = f"TC_{akce}_{'_'.join(slova[:5])}"
    kroky = kroky_data[akce]
    return test_name, kroky

def exportuj_excel(vystupy):
    rows = []
    for tc in vystupy:
        for i, krok in enumerate(tc["kroky"], start=1):
            rows.append({
                "Test Name": tc["test_name"],
                "Operation": tc["akce"],
                "Step #": i,
                "Description (Design Steps)": krok,
                "Expected (Design Steps)": "TODO: doplnit očekávání"
            })
    df = pd.DataFrame(rows)
    df.to_excel("vystup.xlsx", index=False)
    print("✅ Exportováno do vystup.xlsx")

def menu():
    kroky_data = nacti_kroky()
    vystupy = []

    while True:
        print("\n--- MENU ---")
        print("1. Zadat novou větu")
        print("2. Zobrazit / Upravit kroky")
        print("3. Exportovat do Excelu")
        print("4. Konec")
        volba = input("Zvol možnost: ")

        if volba == "1":
            veta = input("Zadej větu: ")
            test_name, kroky = generuj_testcase(veta, kroky_data)
            if test_name:
                vystupy.append({
                    "test_name": test_name,
                    "akce": test_name.split("_")[1],
                    "kroky": kroky
                })
                print(f"✅ Vygenerován test case: {test_name}")
        elif volba == "2":
            print("Aktuální kroky podle klíčových slov:")
            for akce, kroky in kroky_data.items():
                print(f"\n🔸 {akce}:")
                for i, krok in enumerate(kroky, start=1):
                    print(f"  {i}. {krok}")
            akce = input("\nZadej název akce pro úpravu (nebo Enter pro návrat): ").strip()
            if akce in kroky_data:
                print(f"Editace kroků pro {akce}:")
                nove_kroky = []
                while True:
                    krok = input(" - nový krok (nebo Enter pro ukončení): ")
                    if not krok:
                        break
                    nove_kroky.append(krok)
                if nove_kroky:
                    kroky_data[akce] = nove_kroky
                    uloz_kroky(kroky_data)
                    print("✅ Kroky uloženy.")
        elif volba == "3":
            exportuj_excel(vystupy)
        elif volba == "4":
            break
        else:
            print("Neplatná volba.")

if __name__ == "__main__":
    menu()

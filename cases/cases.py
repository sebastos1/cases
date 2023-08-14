import os
import json
import sqlite3
import requests
from termcolor import colored

def generate_databases():
    db.execute("DROP TABLE IF EXISTS cases")
    db.execute("DROP TABLE IF EXISTS skins")
    db.execute('''CREATE TABLE IF NOT EXISTS cases (
        name TEXT,
        cost REAL,
        key_cost REAL,
        roi REAL,
        avg_return REAL,
        knives TEXT
        )''')
    db.execute('''CREATE TABLE IF NOT EXISTS skins (
        name TEXT,
        case_name TEXT,
        rarity TEXT
        )''')
    db.commit()

def update(url, file):
    generate_databases()
    content = requests.get(url).json()
    case_count, global_skin_count = 0, 0

    for case in content["Cases"]:
        print(f'Adding {case["Name"]}')
        knives = []

        for marketplace in case["MarketPlaces"]:
            if marketplace["Name"] == "Steam":
                skin_count = 0

                for skin in marketplace["Skins"]:
                    if skin["Rarity"] == "Special":
                        knives.append(skin["Name"])
                        specials = db.execute(f'SELECT * FROM skins WHERE name = "{skin["Name"]}"').fetchone()
                        if specials:
                            new_cases = specials[1] + ", " + case["Name"]
                            db.execute(f'UPDATE skins SET case_name = "{new_cases}" WHERE name = "{skin["Name"]}"')
                            continue

                    print(f'  Adding {skin["Name"]}')
                    db.execute(f'''INSERT INTO skins (name, case_name, rarity) VALUES ("{skin["Name"]}", "{case["Name"]}", "{skin["Rarity"]}")''')
                    skin_count += 1

                db.execute(f'''INSERT INTO cases (name, cost, key_cost, roi, avg_return, knives) VALUES (
                    "{case["Name"]}", {case["Cost"]},{case["KeyCost"]},{marketplace["Average"]["ROI"]},{marketplace["Average"]["Return"]},"{', '.join(knives)}"
                )''')
                global_skin_count += skin_count
                case_count += 1
    print(f'Added {case_count} cases and {global_skin_count} skins')
    db.commit()

def print_grade(item, grade):
    match grade:
        case "Consumer":
            print(colored(item, "white"))
        case "Industrial":
            print(colored(item, "light_blue"))
        case "Milspec":
            print(colored(item, "blue"))
        case "Restricted":
            print(colored(item, "magenta"))
        case "Classified":
            print(colored(item, "light_red"))
        case "Covert":
            print(colored(item, "red"))
        case "Special":
            print(colored(item, "yellow"))
        case other: 
            print(item)

grade_order = {
    "Consumer": 0,
    "Industrial": 1,
    "Milspec": 2,
    "Restricted": 3,
    "Classified": 4,
    "Covert": 5,
    "Special": 6
}

def roi_list(highlighted = None, sort_by_roi = True):
    cases = db.execute("SELECT * FROM cases ORDER BY roi DESC").fetchall()

    # Find the maximum lengths of each column
    max_name_length = max(len(case[0]) for case in cases)
    max_price_length = max(len(str(round(case[1], 2))) for case in cases)
    max_roi_length = max(len(str(round(case[3], 2))) for case in cases)

    if sort_by_roi:
        cases = sorted(cases, key=lambda x: x[3], reverse=True)
        print("Sorting by ROI")
    else:
        cases = sorted(cases, key=lambda x: x[1])
        print("Sorting by price")
    print(f"\n\n{'Name'.ljust(max_name_length)} | {'PRICE'.ljust(max_price_length)}   | {'ROI'.ljust(max_roi_length)}  | 100$ | Knives")

    for case in cases:
        knives = case[5].split(", ")
        knife_types = [knife.split(" | ")[0] for knife in knives]
        knife_types = list(dict.fromkeys(knife_types))
        name, roi = case[0], round(case[3], 1)
        price = round(case[1], 1)

        #cases for 100 usd
        tot_cost = case[1] + case[2]
        cases_for_100 = int(100 / tot_cost)

        print(f"{name.ljust(max_name_length)} | {str(price).ljust(max_roi_length)}$  | {str(roi).ljust(max_roi_length)}% | {str(cases_for_100).rjust(4)} | ", end="")
        knives = ', '.join(knife_types)

        if highlighted and highlighted in knives:
            print(colored(knives, "yellow"))
        elif not highlighted and "Knife" in knives:
            print(colored(knives, "yellow"))
        else:
            print(knives)

    choice = input("\nHighlight knife? Or type 'toggle' to swap sorting method.\n>")
    if choice == "toggle":
        print(not sort_by_roi)
        roi_list(sort_by_roi = not sort_by_roi, highlighted = highlighted if highlighted else None)
    knife = db.execute(f"SELECT * FROM skins WHERE name LIKE '%{choice}%'").fetchone()
    if knife:
        knife = knife[0].split(" | ")
        roi_list(highlighted = knife[0], sort_by_roi = sort_by_roi)
    

def main():
    while True:
        print("\n\n\n==== SKINS & CASES ====")
        print("1. MAIN PAGE")
        print("2. Skin search")
        print("3. Case contents")
        print("5. Update")
        print("6. Exit")
        menu_choice = input(">")

        if menu_choice == "1":
            roi_list()

        elif menu_choice == "2":
            print("\n\n\n==== SKIN SEARCH ====")
            print("Type in search term:")
            choice = input(">")

            skins = db.execute(f"SELECT * FROM skins WHERE name LIKE '%{choice}%'").fetchall()
            sorted_skins = sorted(skins, key=lambda x: grade_order[x[2]])
            for skin in sorted_skins:
                print_grade(skin[0], skin[2])
                cases = skin[1].split(", ")
                skin_str = "    Found in:\n      "
                output_str = skin_str + "\n      ".join(cases)
                print(output_str)

        elif menu_choice == "3":
            print("Select case")
            cases = db.execute("SELECT * FROM cases ORDER BY roi DESC").fetchall()
            for i, case in enumerate(cases):
                print(f"{1+i}. {case[0]}")
            choice = input(">")
            skins = []
            try:
                case = cases[int(choice)-1]
                skins = db.execute(f"SELECT * FROM skins WHERE case_name LIKE '%{case[0]}%'").fetchall()
            except:
                case = db.execute(f"SELECT * FROM cases WHERE name LIKE '%{choice}%'").fetchone()
                if case:
                    skins = db.execute(f"SELECT * FROM skins WHERE case_name LIKE '%{case[0]}%'").fetchall()
                else:
                    print("Invalid choice")
                    continue
            print(f"\n\n\n==== {case[0]} ====")
            sorted_skins = sorted(skins, key=lambda x: grade_order[x[2]])
            for skin in sorted_skins:
                if case[0] in skin[1].split(", "):
                    print_grade(skin[0], skin[2])

        # elif menu_choice == "4":


        elif menu_choice == "5":
            update("https://raw.githubusercontent.com/jonese1234/Csgo-Case-Data/master/latest.json", "cases.json")

        elif menu_choice == "6":
            db.close()
            break

        else:
            input("Invalid choice, press enter to try again.")

os.system('color') # allows text to be colored
global db
db = sqlite3.connect("./games.db")
update("https://raw.githubusercontent.com/jonese1234/Csgo-Case-Data/master/latest.json", "cases.json")
main()
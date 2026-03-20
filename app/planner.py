"""Wochenplan-Logik: Rezepte einlesen, Plan generieren, Einkaufsliste erstellen."""

import os
import re
import random
from pathlib import Path

from app.settings import get_kochzeiten, get_tage_reihenfolge, TAGE_KURZ, TAGE_LANG

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Supermarkt-Abteilungen: Zutat-Keywords -> Bereich
# Reihenfolge entspricht typischem Supermarkt-Rundgang
ABTEILUNGEN_REIHENFOLGE = [
    "Obst & Gemuese",
    "Frische & Kuehlung",
    "Fleisch & Wurst",
    "Brot & Backwaren",
    "Milchprodukte & Kaese",
    "Eier",
    "Konserven & Fertigprodukte",
    "Nudeln, Reis & Getreide",
    "Oel, Essig & Saucen",
    "Gewuerze & Kraeuter",
    "Tiefkuehlprodukte",
    "Getraenke",
    "Sonstiges",
]

ZUTAT_ABTEILUNG = {
    # Obst & Gemuese
    "paprika": "Obst & Gemuese", "tomate": "Obst & Gemuese", "tomaten": "Obst & Gemuese",
    "kirschtomaten": "Obst & Gemuese", "zwiebel": "Obst & Gemuese", "zwiebeln": "Obst & Gemuese",
    "knoblauch": "Obst & Gemuese", "karotte": "Obst & Gemuese", "karotten": "Obst & Gemuese",
    "zucchini": "Obst & Gemuese", "aubergine": "Obst & Gemuese", "brokkoli": "Obst & Gemuese",
    "gurke": "Obst & Gemuese", "lauch": "Obst & Gemuese", "ingwer": "Obst & Gemuese",
    "zitrone": "Obst & Gemuese", "kopfsalat": "Obst & Gemuese", "salat": "Obst & Gemuese",
    "rucola": "Obst & Gemuese", "champignons": "Obst & Gemuese", "pilze": "Obst & Gemuese",
    "fruehlingszwiebeln": "Obst & Gemuese", "zuckerschoten": "Obst & Gemuese",
    "kartoffel": "Obst & Gemuese", "kartoffeln": "Obst & Gemuese",
    "chilischote": "Obst & Gemuese", "apfelmus": "Obst & Gemuese",
    # Frische & Kuehlung
    "schmand": "Frische & Kuehlung", "sahne": "Frische & Kuehlung",
    "tortilla": "Frische & Kuehlung", "wraps": "Frische & Kuehlung",
    "flammkuchen": "Frische & Kuehlung", "spaetzle": "Frische & Kuehlung",
    "mozzarella": "Frische & Kuehlung",
    # Fleisch & Wurst
    "hackfleisch": "Fleisch & Wurst", "haehnchen": "Fleisch & Wurst",
    "putenbrust": "Fleisch & Wurst", "pute": "Fleisch & Wurst",
    "rindfleisch": "Fleisch & Wurst", "speck": "Fleisch & Wurst",
    "schweineschnitzel": "Fleisch & Wurst", "schnitzel": "Fleisch & Wurst",
    # Brot & Backwaren
    "brot": "Brot & Backwaren", "baguette": "Brot & Backwaren",
    "fladenbrot": "Brot & Backwaren", "broetchen": "Brot & Backwaren",
    # Milchprodukte & Kaese
    "milch": "Milchprodukte & Kaese", "butter": "Milchprodukte & Kaese",
    "parmesan": "Milchprodukte & Kaese", "kaese": "Milchprodukte & Kaese",
    "gouda": "Milchprodukte & Kaese", "emmentaler": "Milchprodukte & Kaese",
    "feta": "Milchprodukte & Kaese", "kokosmilch": "Konserven & Fertigprodukte",
    # Eier
    "eier": "Eier", "ei": "Eier",
    # Konserven & Fertigprodukte
    "dose": "Konserven & Fertigprodukte", "dosen": "Konserven & Fertigprodukte",
    "gehackte tomaten": "Konserven & Fertigprodukte",
    "kidneybohnen": "Konserven & Fertigprodukte", "mais": "Konserven & Fertigprodukte",
    "oliven": "Konserven & Fertigprodukte", "tomatenmark": "Konserven & Fertigprodukte",
    "gewuerzgurken": "Konserven & Fertigprodukte",
    "gemueesebruehe": "Konserven & Fertigprodukte", "bruehe": "Konserven & Fertigprodukte",
    "rinderbruehe": "Konserven & Fertigprodukte",
    "currypaste": "Konserven & Fertigprodukte", "fischsauce": "Konserven & Fertigprodukte",
    # Nudeln, Reis & Getreide
    "spaghetti": "Nudeln, Reis & Getreide", "nudeln": "Nudeln, Reis & Getreide",
    "fusilli": "Nudeln, Reis & Getreide", "pasta": "Nudeln, Reis & Getreide",
    "reis": "Nudeln, Reis & Getreide", "risotto": "Nudeln, Reis & Getreide",
    "lasagneplatten": "Nudeln, Reis & Getreide", "mehl": "Nudeln, Reis & Getreide",
    "semmelbr": "Nudeln, Reis & Getreide",
    # Oel, Essig & Saucen
    "olivenoel": "Oel, Essig & Saucen", "oel": "Oel, Essig & Saucen",
    "sesamoel": "Oel, Essig & Saucen", "sojasauce": "Oel, Essig & Saucen",
    "balsamico": "Oel, Essig & Saucen", "rotweinessig": "Oel, Essig & Saucen",
    "senf": "Oel, Essig & Saucen", "ketchup": "Oel, Essig & Saucen",
    "mayonnaise": "Oel, Essig & Saucen", "weisswein": "Oel, Essig & Saucen",
    "zucker": "Oel, Essig & Saucen",
    # Gewuerze & Kraeuter
    "salz": "Gewuerze & Kraeuter", "pfeffer": "Gewuerze & Kraeuter",
    "oregano": "Gewuerze & Kraeuter", "basilikum": "Gewuerze & Kraeuter",
    "petersilie": "Gewuerze & Kraeuter", "schnittlauch": "Gewuerze & Kraeuter",
    "koriander": "Gewuerze & Kraeuter", "rosmarin": "Gewuerze & Kraeuter",
    "thymian": "Gewuerze & Kraeuter", "paprikapulver": "Gewuerze & Kraeuter",
    "muskatnuss": "Gewuerze & Kraeuter", "chilipulver": "Gewuerze & Kraeuter",
    "kreuzkuemmel": "Gewuerze & Kraeuter", "kuemmel": "Gewuerze & Kraeuter",
    "sesam": "Gewuerze & Kraeuter", "muskat": "Gewuerze & Kraeuter",
    # Tiefkuehlprodukte
    "tiefgekuehlt": "Tiefkuehlprodukte", "erbsen": "Tiefkuehlprodukte",
    "pommes": "Tiefkuehlprodukte",
}


def zutat_zu_abteilung(zutat_text):
    """Ordnet eine Zutat einer Supermarkt-Abteilung zu."""
    text = zutat_text.lower()
    # Laengere Keys zuerst pruefen (z.B. "gehackte tomaten" vor "tomaten")
    for key in sorted(ZUTAT_ABTEILUNG.keys(), key=len, reverse=True):
        if key in text:
            return ZUTAT_ABTEILUNG[key]
    return "Sonstiges"


def parse_nichtverwenden():
    """Liest nichtverwenden.md und gibt eine Liste ausgeschlossener Zutaten zurueck."""
    datei = DATA_DIR / "nichtverwenden.md"
    ausschluss = []
    if datei.exists():
        for line in datei.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("- "):
                ausschluss.append(line[2:].strip().lower())
    return ausschluss


def parse_laden():
    """Liest laden.md und gibt eine Liste der Geschaefte zurueck."""
    datei = DATA_DIR / "laden.md"
    laeden = []
    if datei.exists():
        for line in datei.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("-"):
                laeden.append(line.lstrip("- ").strip())
    return laeden


def parse_rezept(filepath):
    """Parst eine Rezept-Markdown-Datei."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    rezept = {
        "name": "",
        "zubereitungszeit": 30,
        "portionen": 4,
        "tags": [],
        "zutaten": [],
        "zubereitung": [],
        "datei": filepath.name,
    }

    for line in lines:
        if line.startswith("# "):
            rezept["name"] = line[2:].strip()
            break

    for line in lines:
        line = line.strip()
        if line.startswith("- zubereitungszeit:"):
            try:
                rezept["zubereitungszeit"] = int(line.split(":")[1].strip())
            except ValueError:
                pass
        elif line.startswith("- portionen:"):
            try:
                rezept["portionen"] = int(line.split(":")[1].strip())
            except ValueError:
                pass
        elif line.startswith("- tags:"):
            rezept["tags"] = [t.strip() for t in line.split(":")[1].split(",")]

    in_zutaten = False
    in_zubereitung = False
    for line in lines:
        if line.strip().startswith("## Zutaten"):
            in_zutaten = True
            in_zubereitung = False
            continue
        elif line.strip().startswith("## Zubereitung"):
            in_zutaten = False
            in_zubereitung = True
            continue
        elif line.strip().startswith("## "):
            in_zutaten = False
            in_zubereitung = False
            continue

        if in_zutaten and line.strip().startswith("- "):
            rezept["zutaten"].append(line.strip()[2:].strip())
        elif in_zubereitung and line.strip():
            step = re.sub(r"^\d+\.\s*", "", line.strip())
            if step:
                rezept["zubereitung"].append(step)

    return rezept


def lade_alle_rezepte():
    """Liest alle Rezepte aus data/rezepte/."""
    rezepte_dir = DATA_DIR / "rezepte"
    rezepte = []
    if rezepte_dir.exists():
        for f in sorted(rezepte_dir.glob("*.md")):
            rezepte.append(parse_rezept(f))
    return rezepte


def filter_rezepte(rezepte, ausschluss):
    """Filtert Rezepte die ausgeschlossene Zutaten enthalten."""
    gefiltert = []
    for r in rezepte:
        zutaten_text = " ".join(r["zutaten"]).lower()
        if not any(a in zutaten_text for a in ausschluss):
            gefiltert.append(r)
    return gefiltert


def generiere_wochenplan():
    """Generiert einen Wochenplan mit passenden Rezepten pro Tag."""
    max_zeit = get_kochzeiten()
    ausschluss = parse_nichtverwenden()
    laeden = parse_laden()
    alle_rezepte = lade_alle_rezepte()
    rezepte = filter_rezepte(alle_rezepte, ausschluss)

    tage_kurz, tage_lang = get_tage_reihenfolge()

    plan = []
    verwendete = set()

    for i, tag_kurz in enumerate(tage_kurz):
        tag_lang = tage_lang[i]
        max_min = max_zeit[tag_kurz]

        passend = [
            r for r in rezepte
            if r["zubereitungszeit"] <= max_min
            and tag_kurz in r["tags"]
            and r["name"] not in verwendete
        ]

        if not passend:
            passend = [
                r for r in rezepte
                if r["zubereitungszeit"] <= max_min
                and r["name"] not in verwendete
            ]

        if not passend:
            passend = [r for r in rezepte if r["name"] not in verwendete]

        if passend:
            rezept = random.choice(passend)
            verwendete.add(rezept["name"])
        else:
            rezept = None

        plan.append({
            "tag": tag_lang,
            "tag_kurz": tag_kurz,
            "max_zeit": max_min,
            "rezept": rezept,
        })

    # Einkaufsliste nach Abteilungen gruppiert
    einkaufsliste_raw = {}
    for eintrag in plan:
        if eintrag["rezept"]:
            for zutat in eintrag["rezept"]["zutaten"]:
                if zutat not in einkaufsliste_raw:
                    einkaufsliste_raw[zutat] = []
                einkaufsliste_raw[zutat].append(eintrag["tag"])

    # Nach Abteilungen sortieren
    abteilungen = {}
    for zutat, tage in einkaufsliste_raw.items():
        abt = zutat_zu_abteilung(zutat)
        if abt not in abteilungen:
            abteilungen[abt] = []
        abteilungen[abt].append((zutat, tage))

    # Innerhalb jeder Abteilung alphabetisch sortieren
    for abt in abteilungen:
        abteilungen[abt].sort(key=lambda x: x[0].lower())

    # Nach Supermarkt-Rundgang sortieren
    einkaufsliste_gruppiert = []
    for abt in ABTEILUNGEN_REIHENFOLGE:
        if abt in abteilungen:
            einkaufsliste_gruppiert.append((abt, abteilungen[abt]))

    # Flache Liste fuer PDF-Kompatibilitaet
    einkaufsliste_flat = []
    for abt, zutaten in einkaufsliste_gruppiert:
        einkaufsliste_flat.extend(zutaten)

    return {
        "plan": plan,
        "einkaufsliste": einkaufsliste_flat,
        "einkaufsliste_gruppiert": einkaufsliste_gruppiert,
        "laeden": laeden,
        "ausschluss": ausschluss,
    }

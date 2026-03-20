"""Wochenplan-Logik: Rezepte einlesen, Plan generieren, Einkaufsliste erstellen."""

import os
import re
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TAGE_LANG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

# Arbeitszeiten -> verfuegbare Kochzeit abends
# Mo (7-18) = erst ab 18 Uhr -> max 25 min
# Di (7-13) = ab 13 Uhr frei -> max 45 min
# Mi (7-16) = ab 16 Uhr -> max 35 min
# Do (7-19) = erst ab 19 Uhr -> max 25 min
# Fr (7-16) = ab 16 Uhr -> max 35 min
# Sa = ganzer Tag frei -> max 90 min
# So = ganzer Tag frei -> max 90 min
DEFAULT_MAX_ZEIT = {
    "Mo": 25, "Di": 45, "Mi": 35, "Do": 25, "Fr": 35, "Sa": 90, "So": 90
}


def parse_zeit_datei():
    """Liest wochenplan_zeit.md und berechnet max Kochzeit pro Tag."""
    zeitdatei = DATA_DIR / "wochenplan_zeit.md"
    max_zeit = dict(DEFAULT_MAX_ZEIT)

    if not zeitdatei.exists():
        return max_zeit

    for line in zeitdatei.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        for tag in TAGE_KURZ:
            if line.startswith(tag):
                match = re.search(r"\((\d+)-(\d+)\)", line)
                if match:
                    start, end = int(match.group(1)), int(match.group(2))
                    feierabend = end
                    if feierabend >= 18:
                        max_zeit[tag] = 25
                    elif feierabend >= 16:
                        max_zeit[tag] = 35
                    elif feierabend >= 13:
                        max_zeit[tag] = 45
                    else:
                        max_zeit[tag] = 60
                else:
                    max_zeit[tag] = 90
    return max_zeit


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

    # Name aus erster Ueberschrift
    for line in lines:
        if line.startswith("# "):
            rezept["name"] = line[2:].strip()
            break

    # Metadaten
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

    # Zutaten (Bereich zwischen ## Zutaten und naechste ##)
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
    max_zeit = parse_zeit_datei()
    ausschluss = parse_nichtverwenden()
    laeden = parse_laden()
    alle_rezepte = lade_alle_rezepte()
    rezepte = filter_rezepte(alle_rezepte, ausschluss)

    plan = []
    verwendete = set()

    for i, tag_kurz in enumerate(TAGE_KURZ):
        tag_lang = TAGE_LANG[i]
        max_min = max_zeit[tag_kurz]

        # Passende Rezepte finden (Tag-Match + Zeitlimit)
        passend = [
            r for r in rezepte
            if r["zubereitungszeit"] <= max_min
            and tag_kurz in r["tags"]
            and r["name"] not in verwendete
        ]

        # Fallback: nur nach Zeit filtern
        if not passend:
            passend = [
                r for r in rezepte
                if r["zubereitungszeit"] <= max_min
                and r["name"] not in verwendete
            ]

        # Noch ein Fallback: irgendein unbenutztes Rezept
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

    # Einkaufsliste zusammenstellen
    einkaufsliste = {}
    for eintrag in plan:
        if eintrag["rezept"]:
            for zutat in eintrag["rezept"]["zutaten"]:
                if zutat not in einkaufsliste:
                    einkaufsliste[zutat] = []
                einkaufsliste[zutat].append(eintrag["tag"])

    # Sortierte Einkaufsliste
    einkaufsliste_sortiert = sorted(einkaufsliste.items(), key=lambda x: x[0].lower())

    return {
        "plan": plan,
        "einkaufsliste": einkaufsliste_sortiert,
        "laeden": laeden,
        "ausschluss": ausschluss,
    }

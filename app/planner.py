"""Wochenplan-Logik: Rezepte einlesen, Plan generieren, Einkaufsliste erstellen."""

import os
import re
import random
from pathlib import Path

from app.settings import get_kochzeiten, get_tage_reihenfolge, TAGE_KURZ, TAGE_LANG

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


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

    einkaufsliste = {}
    for eintrag in plan:
        if eintrag["rezept"]:
            for zutat in eintrag["rezept"]["zutaten"]:
                if zutat not in einkaufsliste:
                    einkaufsliste[zutat] = []
                einkaufsliste[zutat].append(eintrag["tag"])

    einkaufsliste_sortiert = sorted(einkaufsliste.items(), key=lambda x: x[0].lower())

    return {
        "plan": plan,
        "einkaufsliste": einkaufsliste_sortiert,
        "laeden": laeden,
        "ausschluss": ausschluss,
    }

"""Einstellungen laden und speichern (JSON-basiert)."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "data" / "einstellungen.json"

TAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TAGE_LANG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

DEFAULT_SETTINGS = {
    "starttag": "Mo",
    "personen": 4,
    "arbeitszeiten": {
        "Mo": "7-18",
        "Di": "7-13",
        "Mi": "7-16",
        "Do": "7-19",
        "Fr": "7-16",
        "Sa": "",
        "So": "",
    },
}


def lade_einstellungen():
    """Liest Einstellungen aus JSON, erstellt Default falls nicht vorhanden."""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            # Defaults fuer fehlende Keys
            for key, val in DEFAULT_SETTINGS.items():
                if key not in data:
                    data[key] = val
            if isinstance(data.get("arbeitszeiten"), dict):
                for tag in TAGE_KURZ:
                    if tag not in data["arbeitszeiten"]:
                        data["arbeitszeiten"][tag] = DEFAULT_SETTINGS["arbeitszeiten"].get(tag, "")
            return data
        except (json.JSONDecodeError, KeyError):
            pass
    return dict(DEFAULT_SETTINGS)


def speichere_einstellungen(data):
    """Speichert Einstellungen als JSON."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def berechne_kochzeit(arbeitszeit_str):
    """Berechnet max Kochzeit aus Arbeitszeit-String wie '7-18'."""
    arbeitszeit_str = arbeitszeit_str.strip()
    if not arbeitszeit_str:
        return 90  # Frei -> viel Zeit

    parts = arbeitszeit_str.split("-")
    if len(parts) != 2:
        return 90

    try:
        feierabend = int(parts[1])
    except ValueError:
        return 90

    if feierabend >= 18:
        return 25
    elif feierabend >= 16:
        return 35
    elif feierabend >= 13:
        return 45
    else:
        return 60


def get_kochzeiten():
    """Gibt dict mit max Kochzeit pro Tag zurueck."""
    settings = lade_einstellungen()
    zeiten = {}
    for tag in TAGE_KURZ:
        az = settings["arbeitszeiten"].get(tag, "")
        zeiten[tag] = berechne_kochzeit(az)
    return zeiten


def get_tage_reihenfolge():
    """Gibt Tage in der richtigen Reihenfolge ab Starttag zurueck."""
    settings = lade_einstellungen()
    starttag = settings.get("starttag", "Mo")
    if starttag not in TAGE_KURZ:
        starttag = "Mo"
    start_idx = TAGE_KURZ.index(starttag)
    kurz = TAGE_KURZ[start_idx:] + TAGE_KURZ[:start_idx]
    lang = TAGE_LANG[start_idx:] + TAGE_LANG[:start_idx]
    return kurz, lang

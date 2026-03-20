import os
import json
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response

from app.planner import generiere_wochenplan, lade_alle_rezepte, parse_nichtverwenden, filter_rezepte
from app.pdf_generator import einkaufsliste_pdf, rezept_pdf
from app.settings import lade_einstellungen, speichere_einstellungen, TAGE_KURZ, TAGE_LANG

# ── App ──────────────────────────────────────────────
app = FastAPI(
    title="essenplaner",
    description="Wochenplaner für Mahlzeiten mit Einkaufsliste",
    version="1.0.0",
)

# ── Static & Templates ───────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ── DEV_MODE (Bug-Melde-Modus) ───────────────────────
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# ── Aktuellen Plan im Speicher halten ────────────────
_aktueller_plan = None


def _get_plan(neu=False):
    global _aktueller_plan
    if _aktueller_plan is None or neu:
        _aktueller_plan = generiere_wochenplan()
    return _aktueller_plan


# ── Routes ───────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    daten = _get_plan()
    settings = lade_einstellungen()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "plan": daten["plan"],
        "einkaufsliste": daten["einkaufsliste"],
        "laeden": daten["laeden"],
        "personen": settings.get("personen", 4),
    })


@app.get("/api/neu", response_class=HTMLResponse)
async def neuer_plan(request: Request):
    daten = _get_plan(neu=True)
    settings = lade_einstellungen()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "plan": daten["plan"],
        "einkaufsliste": daten["einkaufsliste"],
        "laeden": daten["laeden"],
        "personen": settings.get("personen", 4),
    })


# ── Einkaufsliste PDF ───────────────────────────────
@app.get("/api/einkaufsliste.pdf")
async def einkaufsliste_download():
    daten = _get_plan()
    pdf_bytes = einkaufsliste_pdf(daten["einkaufsliste"], daten["laeden"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=einkaufsliste.pdf"},
    )


# ── Rezept-Detailseite ──────────────────────────────
@app.get("/rezept/{dateiname}", response_class=HTMLResponse)
async def rezept_detail(request: Request, dateiname: str):
    alle = lade_alle_rezepte()
    ausschluss = parse_nichtverwenden()
    rezepte = filter_rezepte(alle, ausschluss)

    rezept = None
    for r in rezepte:
        if r["datei"] == dateiname:
            rezept = r
            break

    if not rezept:
        for r in alle:
            if r["datei"] == dateiname:
                rezept = r
                break

    if not rezept:
        return HTMLResponse("<h1>Rezept nicht gefunden</h1>", status_code=404)

    return templates.TemplateResponse("rezept.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "rezept": rezept,
    })


# ── Rezept PDF ──────────────────────────────────────
@app.get("/api/rezept/{dateiname}/pdf")
async def rezept_pdf_download(dateiname: str):
    alle = lade_alle_rezepte()
    rezept = None
    for r in alle:
        if r["datei"] == dateiname:
            rezept = r
            break

    if not rezept:
        return Response("Rezept nicht gefunden", status_code=404)

    pdf_bytes = rezept_pdf(rezept)
    safe_name = urllib.parse.quote(rezept["name"].replace(" ", "_"))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}.pdf"},
    )


# ── Einstellungen ────────────────────────────────
@app.get("/einstellungen", response_class=HTMLResponse)
async def einstellungen_seite(request: Request):
    settings = lade_einstellungen()
    return templates.TemplateResponse("einstellungen.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "settings": settings,
        "tage_kurz": TAGE_KURZ,
        "tage_lang": TAGE_LANG,
    })


@app.post("/einstellungen", response_class=HTMLResponse)
async def einstellungen_speichern(request: Request):
    form = await request.form()
    settings = lade_einstellungen()

    settings["starttag"] = form.get("starttag", "Mo")
    try:
        settings["personen"] = max(1, int(form.get("personen", 4)))
    except (ValueError, TypeError):
        settings["personen"] = 4
    for tag in TAGE_KURZ:
        settings["arbeitszeiten"][tag] = form.get(f"zeit_{tag}", "").strip()

    speichere_einstellungen(settings)

    # Plan neu generieren
    _get_plan(neu=True)

    return templates.TemplateResponse("einstellungen.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "settings": settings,
        "tage_kurz": TAGE_KURZ,
        "tage_lang": TAGE_LANG,
        "gespeichert": True,
    })


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Bug-Report API (nur bei DEV_MODE) ────────────────
@app.post("/api/bug-report")
async def bug_report(request: Request):
    if not DEV_MODE:
        return {"error": "Bug-Reporting ist deaktiviert"}

    data = await request.json()
    bug_dir = os.path.join(BASE_DIR, "..", "data", "bugs")
    os.makedirs(bug_dir, exist_ok=True)

    filename = f"bug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(bug_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"status": "ok", "file": filename}

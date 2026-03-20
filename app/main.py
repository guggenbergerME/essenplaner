import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.planner import generiere_wochenplan

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


# ── Routes ───────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    daten = generiere_wochenplan()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "plan": daten["plan"],
        "einkaufsliste": daten["einkaufsliste"],
        "laeden": daten["laeden"],
    })


@app.get("/api/neu", response_class=HTMLResponse)
async def neuer_plan(request: Request):
    """Generiert einen neuen zufaelligen Wochenplan."""
    daten = generiere_wochenplan()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "plan": daten["plan"],
        "einkaufsliste": daten["einkaufsliste"],
        "laeden": daten["laeden"],
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

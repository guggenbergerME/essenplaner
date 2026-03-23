import os
import json
import time
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.planner import generiere_wochenplan, lade_alle_rezepte, parse_nichtverwenden, filter_rezepte, skaliere_rezept
from app.pdf_generator import einkaufsliste_pdf, rezept_pdf, wochenplan_pdf
from app.settings import lade_einstellungen, speichere_einstellungen, TAGE_KURZ, TAGE_LANG
from app.database import (
    init_db, ensure_admin_user, create_user, get_user_by_email, get_user_by_id,
    get_all_users, delete_user, update_user_password, confirm_user,
    save_favorit, get_favoriten, get_favorit, delete_favorit,
)
from app.auth import (
    hash_password, verify_password, generate_password,
    create_session_token, verify_session_token,
    is_admin_email, verify_admin, SESSION_COOKIE,
    ADMIN_EMAIL, ADMIN_PASSWORD,
)
from app.email_service import send_password_email

# ── Security-Header-Middleware ────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
        return response


# ── App ──────────────────────────────────────────────
app = FastAPI(
    title="essenplaner",
    description="Wochenplaner für Mahlzeiten mit Einkaufsliste",
    version="2.0.0",
)
app.add_middleware(SecurityHeadersMiddleware)

# ── Static & Templates ───────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ── DEV_MODE (Bug-Melde-Modus) ───────────────────────
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# ── Rate-Limiting (allgemein) ─────────────────────────
# {key: [timestamp, ...]}
_rate_store: dict[str, list[float]] = {}


def _check_rate_limit(key: str, max_attempts: int, window: int) -> bool:
    """True = erlaubt, False = gesperrt. key = z.B. 'login:1.2.3.4'"""
    now = time.time()
    attempts = _rate_store.get(key, [])
    attempts = [t for t in attempts if now - t < window]
    if len(attempts) >= max_attempts:
        _rate_store[key] = attempts
        return False
    attempts.append(now)
    _rate_store[key] = attempts
    return True


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ── Datenbank initialisieren ─────────────────────────
init_db()
if ADMIN_EMAIL and ADMIN_PASSWORD:
    ensure_admin_user(ADMIN_EMAIL, hash_password(ADMIN_PASSWORD))

# ── Aktuellen Plan im Speicher halten ────────────────
_aktueller_plan = None


def _get_plan(neu=False):
    global _aktueller_plan
    if _aktueller_plan is None or neu:
        _aktueller_plan = generiere_wochenplan()
    return _aktueller_plan


# ── Auth-Hilfsfunktionen ────────────────────────────

def _get_current_user(request: Request):
    """Gibt den aktuellen Nutzer zurück oder None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    data = verify_session_token(token)
    if not data:
        return None
    return get_user_by_id(data["user_id"])


def _require_login(request: Request):
    """Gibt den Nutzer zurück oder None (für Redirect)."""
    return _get_current_user(request)


def _is_admin(user):
    """Prüft ob ein Nutzer der Admin ist."""
    return user and is_admin_email(user["email"])


# ── Oeffentliche Routen ──────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_seite(request: Request):
    user = _get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "dev_mode": DEV_MODE,
    })


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    # Rate-Limiting: max. 10 Login-Versuche pro IP / 15 Minuten
    if not _check_rate_limit(f"login:{_client_ip(request)}", 10, 900):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "Zu viele Anmeldeversuche. Bitte warte 15 Minuten.",
        })

    form = await request.form()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "E-Mail oder Passwort falsch.",
        })

    if not user["is_active"]:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "Dein Konto wurde deaktiviert.",
        })

    token = create_session_token(user["id"])
    # Erster Login → Passwort-Pflicht
    ziel = "/passwort-setzen" if not user.get("confirmed") else "/"
    response = RedirectResponse(ziel, status_code=303)
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=60 * 60 * 24 * 30,
        httponly=True, samesite="lax",
    )
    return response


@app.get("/registrieren", response_class=HTMLResponse)
async def registrieren_seite(request: Request):
    user = _get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("registrieren.html", {
        "request": request,
        "dev_mode": DEV_MODE,
    })


@app.post("/registrieren", response_class=HTMLResponse)
async def registrieren(request: Request):
    form = await request.form()

    # ── Honeypot: verstecktes Feld muss leer bleiben ──
    if form.get("website", ""):
        # Bot erkannt – Erfolg vortäuschen ohne etwas zu tun
        return templates.TemplateResponse("registrieren.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "erfolg": True,
            "email": form.get("email", ""),
        })

    # ── Rate-Limiting pro IP: max. 5 Registrierungen/IP/Stunde ──
    if not _check_rate_limit(f"reg:{_client_ip(request)}", 5, 3600):
        return templates.TemplateResponse("registrieren.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "Zu viele Registrierungsversuche. Bitte versuche es später erneut.",
        })

    email = form.get("email", "").strip().lower()

    if not email or "@" not in email:
        return templates.TemplateResponse("registrieren.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "Bitte gib eine gültige E-Mail-Adresse ein.",
        })

    # Prüfen ob E-Mail schon registriert
    existing = get_user_by_email(email)
    if existing:
        return templates.TemplateResponse("registrieren.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "Diese E-Mail ist bereits registriert.",
        })

    # Einmal-Passwort generieren und senden
    password = generate_password()
    pw_hash = hash_password(password)

    if not create_user(email, pw_hash):
        return templates.TemplateResponse("registrieren.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": "Registrierung fehlgeschlagen. Bitte versuche es erneut.",
        })

    send_password_email(email, password)

    return templates.TemplateResponse("registrieren.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "erfolg": True,
        "email": email,
    })


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ── Startseite (oeffentlich) / Wochenplan (eingeloggt) ─

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = _get_current_user(request)

    # Eingeloggt: Wochenplan anzeigen
    if user:
        daten = _get_plan()
        settings = lade_einstellungen()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "user": user,
            "is_admin": _is_admin(user),
            "plan": daten["plan"],
            "einkaufsliste": daten["einkaufsliste"],
            "einkaufsliste_gruppiert": daten["einkaufsliste_gruppiert"],
            "laeden": daten["laeden"],
            "personen": settings.get("personen", 4),
        })

    # Nicht eingeloggt: Startseite mit Beispielplan
    beispiel = generiere_wochenplan()
    return templates.TemplateResponse("startseite.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "beispiel_plan": beispiel["plan"],
    })


@app.get("/api/neu", response_class=HTMLResponse)
async def neuer_plan(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    daten = _get_plan(neu=True)
    settings = lade_einstellungen()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "plan": daten["plan"],
        "einkaufsliste": daten["einkaufsliste"],
        "einkaufsliste_gruppiert": daten["einkaufsliste_gruppiert"],
        "laeden": daten["laeden"],
        "personen": settings.get("personen", 4),
    })


# ── Wochenplan Komplett-PDF ────────────────────────
@app.get("/api/wochenplan.pdf")
async def wochenplan_download(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    daten = _get_plan()
    settings = lade_einstellungen()
    personen = settings.get("personen", 4)
    pdf_bytes = wochenplan_pdf(daten["plan"], daten["einkaufsliste_gruppiert"], daten["laeden"], personen)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=wochenplan.pdf"},
    )


# ── Einkaufsliste PDF ───────────────────────────────
@app.get("/api/einkaufsliste.pdf")
async def einkaufsliste_download(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    daten = _get_plan()
    pdf_bytes = einkaufsliste_pdf(daten["einkaufsliste_gruppiert"], daten["laeden"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=einkaufsliste.pdf"},
    )


# ── Rezept-Detailseite ──────────────────────────────
@app.get("/rezept/{dateiname}", response_class=HTMLResponse)
async def rezept_detail(request: Request, dateiname: str):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

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

    settings = lade_einstellungen()
    personen = settings.get("personen", 4)
    rezept = skaliere_rezept(rezept, personen)

    return templates.TemplateResponse("rezept.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "rezept": rezept,
    })


# ── Rezept PDF ──────────────────────────────────────
@app.get("/api/rezept/{dateiname}/pdf")
async def rezept_pdf_download(request: Request, dateiname: str):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    alle = lade_alle_rezepte()
    rezept = None
    for r in alle:
        if r["datei"] == dateiname:
            rezept = r
            break

    if not rezept:
        return Response("Rezept nicht gefunden", status_code=404)

    settings = lade_einstellungen()
    personen = settings.get("personen", 4)
    rezept = skaliere_rezept(rezept, personen)

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
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    settings = lade_einstellungen()
    return templates.TemplateResponse("einstellungen.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "settings": settings,
        "tage_kurz": TAGE_KURZ,
        "tage_lang": TAGE_LANG,
    })


@app.post("/einstellungen", response_class=HTMLResponse)
async def einstellungen_speichern(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

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
        "user": user,
        "is_admin": _is_admin(user),
        "settings": settings,
        "tage_kurz": TAGE_KURZ,
        "tage_lang": TAGE_LANG,
        "gespeichert": True,
    })


# ── Passwort-Validierung ─────────────────────────

import re as _re

def _validate_password(pw: str) -> str | None:
    """Gibt None zurück wenn ok, sonst Fehlermeldung."""
    if len(pw) < 8:
        return "Das Passwort muss mindestens 8 Zeichen lang sein."
    if not _re.search(r"[A-Z]", pw):
        return "Das Passwort muss mindestens einen Großbuchstaben enthalten."
    if not _re.search(r"[a-z]", pw):
        return "Das Passwort muss mindestens einen Kleinbuchstaben enthalten."
    if not _re.search(r"\d", pw):
        return "Das Passwort muss mindestens eine Zahl enthalten."
    if not _re.search(r"[^A-Za-z0-9]", pw):
        return "Das Passwort muss mindestens ein Sonderzeichen enthalten."
    return None


# ── Passwort setzen (Erster Login) ───────────────

@app.get("/passwort-setzen", response_class=HTMLResponse)
async def passwort_setzen_seite(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("confirmed"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("passwort_setzen.html", {
        "request": request,
        "dev_mode": DEV_MODE,
    })


@app.post("/passwort-setzen", response_class=HTMLResponse)
async def passwort_setzen(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.get("confirmed"):
        return RedirectResponse("/", status_code=303)

    form = await request.form()
    neues_pw = form.get("neues_passwort", "")
    neues_pw2 = form.get("neues_passwort2", "")

    fehler = _validate_password(neues_pw)
    if not fehler and neues_pw != neues_pw2:
        fehler = "Die Passwörter stimmen nicht überein."

    if fehler:
        return templates.TemplateResponse("passwort_setzen.html", {
            "request": request,
            "dev_mode": DEV_MODE,
            "fehler": fehler,
        })

    update_user_password(user["id"], hash_password(neues_pw))
    confirm_user(user["id"])
    return RedirectResponse("/", status_code=303)


# ── Passwort aendern ─────────────────────────────

@app.get("/passwort-aendern", response_class=HTMLResponse)
async def passwort_aendern_seite(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("passwort_aendern.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
    })


@app.post("/passwort-aendern", response_class=HTMLResponse)
async def passwort_aendern(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    altes_pw = form.get("altes_passwort", "")
    neues_pw = form.get("neues_passwort", "")
    neues_pw2 = form.get("neues_passwort2", "")

    ctx = {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
    }

    if not verify_password(altes_pw, user["password_hash"]):
        ctx["fehler"] = "Das aktuelle Passwort ist falsch."
        return templates.TemplateResponse("passwort_aendern.html", ctx)

    fehler = _validate_password(neues_pw)
    if not fehler and neues_pw != neues_pw2:
        fehler = "Die neuen Passwörter stimmen nicht überein."
    if fehler:
        ctx["fehler"] = fehler
        return templates.TemplateResponse("passwort_aendern.html", ctx)

    update_user_password(user["id"], hash_password(neues_pw))
    ctx["erfolg"] = True
    return templates.TemplateResponse("passwort_aendern.html", ctx)


# ── Favoriten ────────────────────────────────────

@app.post("/api/favorit/speichern")
async def favorit_speichern(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        name = f"Wochenplan vom {datetime.now().strftime('%d.%m.%Y')}"

    daten = _get_plan()
    # Plan-Daten serialisierbar machen
    plan_data = {
        "plan": daten["plan"],
        "einkaufsliste": daten["einkaufsliste"],
        "einkaufsliste_gruppiert": daten["einkaufsliste_gruppiert"],
        "laeden": daten["laeden"],
    }
    save_favorit(user["id"], name, plan_data)
    return RedirectResponse("/favoriten", status_code=303)


@app.get("/favoriten", response_class=HTMLResponse)
async def favoriten_seite(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    favs = get_favoriten(user["id"])
    return templates.TemplateResponse("favoriten.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "favoriten": favs,
    })


@app.get("/favorit/{favorit_id}", response_class=HTMLResponse)
async def favorit_anzeigen(request: Request, favorit_id: int):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    fav = get_favorit(favorit_id, user["id"])
    if not fav:
        return RedirectResponse("/favoriten", status_code=303)

    settings = lade_einstellungen()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "plan": fav["plan_data"]["plan"],
        "einkaufsliste": fav["plan_data"]["einkaufsliste"],
        "einkaufsliste_gruppiert": fav["plan_data"]["einkaufsliste_gruppiert"],
        "laeden": fav["plan_data"]["laeden"],
        "personen": settings.get("personen", 4),
        "favorit_name": fav["name"],
    })


@app.post("/favorit/{favorit_id}/loeschen")
async def favorit_loeschen(request: Request, favorit_id: int):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    delete_favorit(favorit_id, user["id"])
    return RedirectResponse("/favoriten", status_code=303)


# ── Monatsplan ────────────────────────────────────

@app.get("/monatsplan", response_class=HTMLResponse)
async def monatsplan_seite(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("monatsplan.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "wochen": None,
    })


@app.post("/monatsplan", response_class=HTMLResponse)
async def monatsplan_generieren(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    wochen = []
    for i in range(4):
        plan = generiere_wochenplan()
        wochen.append({
            "nummer": i + 1,
            "plan": plan["plan"],
            "einkaufsliste_gruppiert": plan["einkaufsliste_gruppiert"],
            "laeden": plan["laeden"],
        })

    settings = lade_einstellungen()
    return templates.TemplateResponse("monatsplan.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
        "wochen": wochen,
        "personen": settings.get("personen", 4),
    })


@app.get("/api/monatsplan.pdf")
async def monatsplan_pdf_download(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.pdf_generator import monatsplan_pdf
    wochen = []
    for i in range(4):
        plan = generiere_wochenplan()
        wochen.append({
            "nummer": i + 1,
            "plan": plan["plan"],
            "einkaufsliste_gruppiert": plan["einkaufsliste_gruppiert"],
            "laeden": plan["laeden"],
        })

    settings = lade_einstellungen()
    personen = settings.get("personen", 4)
    pdf_bytes = monatsplan_pdf(wochen, personen)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=monatsplan.pdf"},
    )


# ── Admin-Bereich ────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_seite(request: Request):
    user = _require_login(request)
    if not user or not _is_admin(user):
        return RedirectResponse("/", status_code=303)

    users = get_all_users()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": True,
        "users": users,
    })


@app.post("/admin/user/{user_id}/loeschen")
async def admin_user_loeschen(request: Request, user_id: int):
    user = _require_login(request)
    if not user or not _is_admin(user):
        return RedirectResponse("/", status_code=303)

    # Admin kann sich nicht selbst löschen
    if user_id == user["id"]:
        return RedirectResponse("/admin", status_code=303)

    delete_user(user_id)
    return RedirectResponse("/admin", status_code=303)


# ── Rechtliche Seiten ─────────────────────────────

@app.get("/impressum", response_class=HTMLResponse)
async def impressum(request: Request):
    user = _get_current_user(request)
    return templates.TemplateResponse("impressum.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
    })


@app.get("/datenschutz", response_class=HTMLResponse)
async def datenschutz(request: Request):
    user = _get_current_user(request)
    return templates.TemplateResponse("datenschutz.html", {
        "request": request,
        "dev_mode": DEV_MODE,
        "user": user,
        "is_admin": _is_admin(user),
    })


# ── Health ────────────────────────────────────────

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

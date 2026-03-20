# essenplaner

Wochenplaner für Mahlzeiten mit Einkaufsliste.

## Schnellinstallation

```bash
git clone https://github.com/guggenbergerME/essenplaner.git /tmp/essenplaner_setup && \
  bash /tmp/essenplaner_setup/setup/setup.sh
```

## Entwicklung

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 80
```

## Technologie

- **Backend:** Python / FastAPI
- **Frontend:** Jinja2 Templates
- **Datenbank:** SQLite
- **Container:** Docker Compose

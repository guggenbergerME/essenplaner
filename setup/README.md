# essenplaner – Setup

## Erstinstallation

```bash
git clone https://github.com/guggenbergerME/essenplaner.git /tmp/essenplaner_setup && \
  bash /tmp/essenplaner_setup/setup/setup.sh
```

Das Setup-Skript führt folgende Schritte aus:
1. System aktualisieren
2. Abhängigkeiten installieren (curl, git, sudo)
3. Docker installieren (falls nicht vorhanden)
4. Projekt nach `/opt/essenplaner` klonen
5. Docker Container starten

## Update

```bash
bash /opt/essenplaner/setup/update.sh
```

Das Update-Skript:
1. Zieht die neueste Version von GitHub
2. Baut die Docker Container neu
3. Räumt alte Docker Images auf

## Konfiguration

| Variable | Wert |
|----------|------|
| Install-Dir | `/opt/essenplaner` |
| Admin-User | `admin` |
| Admin-E-Mail | `admin@guggbyte.com` |
| HTTP-Port | `80` |

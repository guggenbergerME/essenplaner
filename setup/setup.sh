#!/bin/bash
# ══════════════════════════════════════════════════════
# essenplaner – Erstinstallation
# ══════════════════════════════════════════════════════
set -e

PROJEKT="essenplaner"
REPO="guggenbergerME/essenplaner"
INSTALL_DIR="/opt/essenplaner"
ADMIN_USER="admin"
ADMIN_EMAIL="admin@guggbyte.com"

echo "══════════════════════════════════════════════════"
echo "  $PROJEKT – Setup"
echo "══════════════════════════════════════════════════"

# ── Systemaktualisierung ─────────────────────────────
echo "[1/5] System aktualisieren..."
apt update && apt upgrade -y

# ── Abhängigkeiten ───────────────────────────────────
echo "[2/5] Abhängigkeiten installieren..."
apt install -y curl git sudo

# ── Docker ───────────────────────────────────────────
echo "[3/5] Docker installieren..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "  Docker bereits installiert."
fi

# ── Projekt klonen ───────────────────────────────────
echo "[4/5] Projekt einrichten..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  Verzeichnis $INSTALL_DIR existiert bereits."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone "https://github.com/$REPO.git" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── Container starten ────────────────────────────────
echo "[5/5] Docker Container starten..."
cd "$INSTALL_DIR/docker"
docker compose up -d --build

echo ""
echo "══════════════════════════════════════════════════"
echo "  $PROJEKT erfolgreich installiert!"
echo "══════════════════════════════════════════════════"
echo ""
echo "  URL:    http://$(hostname -I | awk '{print $1}')"
echo "  Admin:  $ADMIN_USER / $ADMIN_EMAIL"
echo ""

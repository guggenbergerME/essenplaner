#!/bin/bash
# ══════════════════════════════════════════════════════
# essenplaner – Update
# ══════════════════════════════════════════════════════
set -e

PROJEKT="essenplaner"
INSTALL_DIR="/opt/essenplaner"

echo "══════════════════════════════════════════════════"
echo "  $PROJEKT – Update"
echo "══════════════════════════════════════════════════"

cd "$INSTALL_DIR"

# ── Neueste Version holen ────────────────────────────
echo "[1/3] Neueste Version herunterladen..."
git pull origin main

# ── Container neu bauen ──────────────────────────────
echo "[2/3] Container neu bauen..."
cd "$INSTALL_DIR/docker"
docker compose up -d --build

# ── Aufräumen ────────────────────────────────────────
echo "[3/3] Alte Images aufräumen..."
docker image prune -f

echo ""
echo "══════════════════════════════════════════════════"
echo "  $PROJEKT erfolgreich aktualisiert!"
echo "══════════════════════════════════════════════════"
echo ""
echo "  URL: http://$(hostname -I | awk '{print $1}')"
echo ""

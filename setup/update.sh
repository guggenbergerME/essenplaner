#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  essenplaner – Update-Skript
#  Aktualisiert Code und startet Docker-Stack neu.
# ============================================================

INSTALL_DIR="/opt/essenplaner"

# ---------- Hilfsfunktionen ----------

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
err()   { echo -e "\033[1;31m[ERR]\033[0m   $*"; exit 1; }

# ---------- Root-Check ----------

if [[ $EUID -ne 0 ]]; then
  err "Dieses Skript muss als root ausgefuehrt werden."
fi

[[ -d "${INSTALL_DIR}/.git" ]] || err "${INSTALL_DIR} ist kein Git-Repository. Bitte zuerst setup.sh ausfuehren."

echo ""
echo "=============================================="
echo "  essenplaner – Update"
echo "=============================================="
echo ""

# ---------- Aktuelle Version ----------

CURRENT=$(git -C "${INSTALL_DIR}" rev-parse --short HEAD)
info "Aktuelle Version: ${CURRENT}"

# ---------- Code aktualisieren (.env bleibt erhalten) ----------

info "Code wird aktualisiert ..."
git -C "${INSTALL_DIR}" fetch origin
git -C "${INSTALL_DIR}" branch --set-upstream-to=origin/master master 2>/dev/null || true
REMOTE=$(git -C "${INSTALL_DIR}" rev-parse --short origin/master 2>/dev/null \
         || git -C "${INSTALL_DIR}" rev-parse --short origin/main)

if [[ "${CURRENT}" == "${REMOTE}" ]]; then
  ok "Bereits auf dem neuesten Stand (${CURRENT})."
else
  git -C "${INSTALL_DIR}" pull --ff-only
  NEW=$(git -C "${INSTALL_DIR}" rev-parse --short HEAD)
  ok "Code aktualisiert: ${CURRENT} -> ${NEW}"
fi

# ---------- Docker-Stack neu starten ----------

info "Docker-Stack wird neu gebaut ..."
cd "${INSTALL_DIR}"
docker compose up -d --build --force-recreate --remove-orphans
ok "Docker-Stack neugestartet."

# ---------- Fertig ----------

echo ""
echo "=============================================="
echo "  Update abgeschlossen!"
echo "=============================================="
echo ""
echo "  Logs anzeigen:"
echo "  cd ${INSTALL_DIR} && docker compose logs -f"
echo ""

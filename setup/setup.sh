#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  essenplaner – Automatisches Setup-Skript
#  Wochenplaner fuer Mahlzeiten mit Einkaufsliste
#  Fuer Debian 12 / Ubuntu 24.04 LXC Container mit Docker
# ============================================================

INSTALL_DIR="/opt/essenplaner"

# ---------- Hilfsfunktionen ----------

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
err()   { echo -e "\033[1;31m[ERR]\033[0m   $*"; exit 1; }

get_default_ip() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1
}

prompt_value() {
  local varname="$1" prompt="$2" default="$3"
  read -rp "  ${prompt} [${default}]: " value
  value="${value:-$default}"
  eval "$varname=\"$value\""
}

prompt_secret() {
  local varname="$1" prompt="$2"
  while true; do
    read -rsp "  ${prompt}: " value
    echo ""
    if [[ -n "$value" ]]; then
      eval "$varname=\"$value\""
      return
    fi
    warn "Darf nicht leer sein."
  done
}

prompt_required() {
  local varname="$1" prompt="$2"
  while true; do
    read -rp "  ${prompt}: " value
    if [[ -n "$value" ]]; then
      eval "$varname=\"$value\""
      return
    fi
    warn "Darf nicht leer sein."
  done
}

# ---------- Root-Check ----------

if [[ $EUID -ne 0 ]]; then
  err "Dieses Skript muss als root ausgefuehrt werden."
fi

echo ""
echo "=============================================="
echo "  essenplaner – Setup"
echo "  Wochenplaner fuer Mahlzeiten mit Einkaufsliste"
echo "=============================================="
echo ""

# ---------- Einstellungen abfragen ----------

DEFAULT_IP=$(get_default_ip)

info "Bitte gib die gewuenschten Einstellungen ein:"
echo ""

prompt_value SERVER_IP   "IP-Adresse des Servers"  "${DEFAULT_IP}"
prompt_value SERVER_PORT "Web-Port"                 "80"

if [[ "$SERVER_PORT" == "80" ]]; then
  APP_URL="http://${SERVER_IP}"
else
  APP_URL="http://${SERVER_IP}:${SERVER_PORT}"
fi

echo ""
prompt_value ADMIN_USERNAME "Admin-Benutzername" "admin"
prompt_required ADMIN_EMAIL_INPUT "Admin-E-Mail"
ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=\n' | head -c 16)

echo ""
info "Zusammenfassung:"
echo "  Server-IP : ${SERVER_IP}"
echo "  Port      : ${SERVER_PORT}"
echo "  URL       : ${APP_URL}"
echo "  Admin     : ${ADMIN_USERNAME}"
echo ""
read -rp "Weiter? (j/n) [j]: " CONFIRM
CONFIRM="${CONFIRM:-j}"
[[ "$CONFIRM" =~ ^[jJyY]$ ]] || { info "Abgebrochen."; exit 0; }

# ---------- System aktualisieren ----------

info "System wird aktualisiert ..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq ca-certificates curl gnupg git
ok "System aktualisiert."

# ---------- Docker installieren ----------

if ! command -v docker &>/dev/null; then
  info "Docker wird installiert ..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  ok "Docker installiert."
else
  ok "Docker ist bereits installiert."
fi

# ---------- Docker-Logging konfigurieren ----------

info "Docker-Logging wird konfiguriert ..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'DAEMON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
DAEMON
systemctl restart docker
ok "Docker-Logging konfiguriert."

# ---------- Repository klonen ----------

REPO_URL="https://github.com/guggenbergerME/essenplaner.git"

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  warn "Vorherige Installation gefunden – Stack wird gestoppt ..."
  [[ -f "${INSTALL_DIR}/.env" ]] && cp "${INSTALL_DIR}/.env" /tmp/essenplaner_env_backup
  (cd "${INSTALL_DIR}" && docker compose down 2>/dev/null) || true
  git -C "${INSTALL_DIR}" pull --ff-only
  [[ -f /tmp/essenplaner_env_backup ]] && mv /tmp/essenplaner_env_backup "${INSTALL_DIR}/.env"
  ok "Repository aktualisiert."
else
  [[ -d "${INSTALL_DIR}" ]] && rm -rf "${INSTALL_DIR}"
  info "Repository wird geklont ..."
  git clone "${REPO_URL}" "${INSTALL_DIR}"
  ok "Repository geklont."
fi

# ---------- Datenverzeichnisse anlegen ----------

info "Datenverzeichnisse werden angelegt ..."
mkdir -p "${INSTALL_DIR}/data"
ok "Datenverzeichnisse erstellt."

# ---------- .env erstellen ----------

if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
  info ".env wird erstellt ..."
  SECRET_KEY=$(openssl rand -hex 32)

  cat > "${INSTALL_DIR}/.env" << ENV
# ============================================================
#  essenplaner – Konfiguration
#  Erstellt am: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================

## ===== Netzwerk =====
APP_PORT=${SERVER_PORT}
APP_URL=${APP_URL}

## ===== Auth =====
SECRET_KEY=${SECRET_KEY}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_EMAIL=${ADMIN_EMAIL_INPUT}

ENV

  chmod 600 "${INSTALL_DIR}/.env"
  ok ".env erstellt."
else
  ok ".env bleibt erhalten."
fi

# ---------- Docker Stack starten ----------

info "Docker Stack wird gebaut und gestartet ..."
cd "${INSTALL_DIR}"
docker compose up -d --build
ok "Docker Stack gestartet."

# ---------- Fertig ----------

echo ""
echo "=============================================="
echo "  essenplaner wurde erfolgreich installiert!"
echo "=============================================="
echo ""
echo "  Web-Oberflaeche : ${APP_URL}"
echo "  Installationsort: ${INSTALL_DIR}"
echo ""
echo "  Admin-Benutzer  : ${ADMIN_USERNAME}"
echo "  Admin-Passwort  : ${ADMIN_PASSWORD}"
echo ""
echo "  Logs anzeigen:"
echo "  cd ${INSTALL_DIR} && docker compose logs -f"
echo ""

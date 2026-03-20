<a name="top"></a>

# Server Setup – essenplaner

Standardisierte Einrichtung fuer essenplaner auf Proxmox LXC Container.

---

## Proxmox LXC Container erstellen

Auf dem **Proxmox Host** in der Shell ausfuehren:

```bash
pct create 130 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname essenplaner \
  --storage local-lvm \
  --rootfs local-lvm:10 \
  --cores 2 \
  --memory 2048 \
  --swap 1024 \
  --net0 name=eth0,bridge=vmbr1,ip=192.168.2.130/16,gw=192.168.2.1,firewall=1 \
  --nameserver 1.1.1.1 \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --onboot 1 \
  --start 0
```

Docker-Unterstuetzung in der LXC-Konfiguration aktivieren:

```bash
cat >> /etc/pve/lxc/130.conf << 'EOF'
lxc.apparmor.profile: unconfined
lxc.cgroup.devices.allow: a
lxc.cap.drop:
lxc.mount.auto: proc:rw sys:rw
EOF
```

Container starten:

```bash
pct start 130
```

---

## SSH-Zugang aktivieren

Im frisch gestarteten **Debian LXC Container** als root ausfuehren (z.B. ueber die Proxmox-Konsole):

```bash
apt update && apt install -y openssh-server && \
  sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
  systemctl enable ssh && systemctl restart ssh
```

Danach ist der Container per SSH erreichbar:

```bash
ssh root@192.168.2.130
```

---

## GitHub CLI einrichten und mit Repository verbinden

Auf dem frischen **Debian 12** LXC Container als root ausfuehren:

```bash
apt update && apt install -y curl git ca-certificates gnupg && \
install -m 0755 -d /etc/apt/keyrings && \
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  -o /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
chmod a+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] \
  https://cli.github.com/packages stable main" \
  > /etc/apt/sources.list.d/github-cli.list && \
apt update && apt install -y gh && \
gh auth login --hostname github.com --git-protocol https --web=false
```

Bei der Authentifizierung wird ein **Personal Access Token (classic)** abgefragt.

### Token erstellen

1. [https://github.com/settings/tokens](https://github.com/settings/tokens) oeffnen
2. **Generate new token** → **Generate new token (classic)**
3. **Note:** z.B. `LXC essenplaner`
4. **Expiration:** nach Bedarf (z.B. 90 days)
5. **Scopes** ankreuzen: `repo` und `read:org`
6. **Generate token** klicken und den Token kopieren
7. Den Token im Terminal einfuegen wenn `Paste your authentication token:` erscheint

---

## Repository klonen und Setup ausfuehren

```bash
git clone https://github.com/guggenbergerME/essenplaner.git /tmp/essenplaner_setup && \
  bash /tmp/essenplaner_setup/setup/setup.sh
```

---

## Update eines bestehenden Dienstes

```bash
bash /opt/essenplaner/setup/update.sh
```

Oder manuell:

```bash
cd /opt/essenplaner
docker compose down
git pull
docker compose up -d --build
```

> **Hinweis:** `.env` und Datenverzeichnisse sind in `.gitignore` – sie werden durch `git pull` nicht ueberschrieben.

---

## Nuetzliche Befehle

```bash
cd /opt/essenplaner
docker compose ps            # Status anzeigen
docker compose logs -f       # Logs verfolgen
docker compose down          # Stack stoppen
docker compose up -d         # Stack starten
docker compose up -d --build # Stack neu bauen und starten
```

---

## Netzwerk

| Eigenschaft | Wert |
|-------------|------|
| CT-ID | 130 |
| Hostname | essenplaner |
| IP-Adresse | 192.168.2.130 |
| Gateway | 192.168.2.1 |
| HTTP-Port | 80 |

---

[↑ Top](#top)

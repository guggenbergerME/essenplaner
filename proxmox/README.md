# Proxmox Container – essenplaner

## Container erstellen

```bash
pct create 130 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname essenplaner \
  --memory 512 \
  --swap 256 \
  --cores 1 \
  --rootfs local-lvm:4 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.2.130/24,gw=192.168.2.1 \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1 \
  --start 1
```

## Container starten & einrichten

```bash
pct start 130
pct enter 130
```

### Docker installieren

```bash
apt update && apt upgrade -y
apt install -y curl git sudo

curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### Anwendung installieren

```bash
git clone https://github.com/guggenbergerME/essenplaner.git /tmp/essenplaner_setup && \
  bash /tmp/essenplaner_setup/setup/setup.sh
```

## Netzwerk

| Eigenschaft | Wert |
|-------------|------|
| CT-ID | 130 |
| Hostname | essenplaner |
| IP-Adresse | 192.168.2.130 |
| Gateway | 192.168.2.1 |
| HTTP-Port | 80 |

## Zugriff

- **Web:** http://192.168.2.130
- **SSH:** `ssh root@192.168.2.130` (Passwort: qwerqwer)

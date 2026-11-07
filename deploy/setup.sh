#!/usr/bin/env bash
# One-shot setup for a fresh Vultr Cloud Compute VM (Ubuntu 24.04, 2 vCPU / 4 GB recommended).
#
#   curl -fsSL https://raw.githubusercontent.com/Abrar5510/triage/main/deploy/setup.sh | sudo bash
#   sudo nano /opt/triage/.env          # set VULTR_INFERENCE_API_KEY
#   sudo systemctl restart triage
#
# Installs Docker + gVisor (runsc), Caddy (automatic HTTPS), uv, and runs Triage as a systemd service.
# Without a DOMAIN env var the app is served at https://<public-ip>.sslip.io.
set -euo pipefail

REPO="${REPO:-https://github.com/Abrar5510/triage.git}"
APP=/opt/triage
IP="$(curl -fsS http://169.254.169.254/v1/interface/0/ipv4/address 2>/dev/null || hostname -I | awk '{print $1}')"
DOMAIN="${DOMAIN:-${IP//./-}.sslip.io}"

echo "==> packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -yq ca-certificates curl gnupg git ufw docker.io debian-keyring debian-archive-keyring apt-transport-https

echo "==> gVisor"
curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor --yes -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" \
  > /etc/apt/sources.list.d/gvisor.list
apt-get update -q && apt-get install -yq runsc
runsc install            # registers the runsc runtime in /etc/docker/daemon.json
systemctl restart docker
docker run --rm --runtime=runsc hello-world >/dev/null && echo "gVisor OK"

echo "==> Caddy"
curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -q && apt-get install -yq caddy

echo "==> app"
id triage >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/triage --shell /usr/sbin/nologin triage
usermod -aG docker triage   # the orchestrator launches sandboxes; it never runs untrusted code itself
if [ -d "$APP/.git" ]; then git -C "$APP" pull --ff-only; else git clone "$REPO" "$APP"; fi
[ -f "$APP/.env" ] || cp "$APP/.env.example" "$APP/.env"
chmod 600 "$APP/.env"
chown -R triage:triage "$APP"
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin INSTALLER_NO_MODIFY_PATH=1 sh
sudo -u triage bash -c "cd $APP && uv venv -q -p 3.12 .venv && uv pip install -q -p .venv -e ."
docker pull -q python:3.12-slim

cp "$APP/deploy/triage.service" /etc/systemd/system/triage.service
systemctl daemon-reload
systemctl enable --now triage

sed "s/__DOMAIN__/$DOMAIN/" "$APP/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl restart caddy

echo "==> firewall"
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable

echo
echo "Triage is up at https://$DOMAIN"
grep -q '^VULTR_INFERENCE_API_KEY=.\+' "$APP/.env" || echo "Next: put your key in $APP/.env and run: systemctl restart triage"

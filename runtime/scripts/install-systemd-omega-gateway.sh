#!/usr/bin/env bash
set -euo pipefail

# Installs the Rust omega-gateway as a systemd *system* service.
# Requires sudo (will prompt).
#
# Usage:
#   cd OmegA-Sovereign/rust/omega-rust
#   ./scripts/install-systemd-omega-gateway.sh
#
# Expects an existing env file at:
#   /home/mega/.omega/gateway.env
# This script copies it to:
#   /etc/omega/omega-gateway.env
#
# Supabase note:
#   Ensure the pgvector schema exists before pointing OMEGA_DB_URL at Supabase:
#   ./scripts/supabase_memory_schema.sql (run in Supabase SQL editor)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "$ROOT_DIR/Cargo.toml" ]]; then
  echo "error: run from OmegA-Sovereign/rust/omega-rust" >&2
  exit 1
fi

ENV_SRC="/home/mega/.omega/gateway.env"
if [[ ! -f "$ENV_SRC" ]]; then
  echo "error: missing env file: $ENV_SRC" >&2
  echo "Create it (must include OMEGA_DB_URL=postgres...) then re-run." >&2
  exit 1
fi

echo "[1/5] Building release binary..."
cargo build --release -p omega-gateway

BIN_SRC="$ROOT_DIR/target/release/omega-gateway"
if [[ ! -x "$BIN_SRC" ]]; then
  echo "error: missing built binary: $BIN_SRC" >&2
  exit 1
fi

RUN_USER="${SUDO_USER:-$USER}"
WORK_DIR="/var/lib/omega"

echo "[2/5] Installing binary to /usr/local/bin/omega-gateway (sudo)..."
sudo install -Dm755 "$BIN_SRC" /usr/local/bin/omega-gateway

echo "[3/5] Installing env to /etc/omega/omega-gateway.env (sudo)..."
sudo mkdir -p /etc/omega
sudo install -m600 "$ENV_SRC" /etc/omega/omega-gateway.env

# Ensure port is set (GatewayConfig defaults to 8787, but make it explicit for deploys).
if ! sudo rg -q '^OMEGA_PORT=' /etc/omega/omega-gateway.env 2>/dev/null; then
  echo "OMEGA_PORT=8787" | sudo tee -a /etc/omega/omega-gateway.env >/dev/null
fi

echo "[4/5] Preparing runtime directory $WORK_DIR (sudo)..."
sudo mkdir -p "$WORK_DIR"
sudo chown "$RUN_USER:$RUN_USER" "$WORK_DIR"

echo "[5/5] Installing systemd unit + starting service (sudo)..."
tmp_unit="$(mktemp)"
sed "s/^User=.*/User=${RUN_USER}/" "$ROOT_DIR/omega-gateway.service.systemd" >"$tmp_unit"
sudo install -m644 "$tmp_unit" /etc/systemd/system/omega-gateway.service
rm -f "$tmp_unit"
sudo systemctl daemon-reload
sudo systemctl enable --now omega-gateway

echo
echo "Installed. Tail logs with:"
echo "  sudo journalctl -u omega-gateway -f"

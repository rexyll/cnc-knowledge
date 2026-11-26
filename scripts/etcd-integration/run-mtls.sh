#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/scripts/etcd-integration/compose-mtls.yaml"
PROJECT_NAME="cnc-knowledge-etcd-mtls-itest"
CERT_DIR="/tmp/cnc-etcd-mtls-certs"
DIAG_DIR="/tmp/ch17-etcd-mtls-runner"
rm -rf "$CERT_DIR"
mkdir -p "$CERT_DIR" "$DIAG_DIR"
export ETCD_MTLS_CERT_DIR="$CERT_DIR"

cd "$ROOT_DIR"
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 2
fi
docker compose version >/dev/null
command -v openssl >/dev/null
python3 -m pip install -r requirements-ch17-etcd-integration.txt

cleanup() {
  docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps --all \
    > "$DIAG_DIR/compose-ps.txt" 2>&1 || true
  docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" logs --no-color \
    > "$DIAG_DIR/etcd-mtls-cluster.log" 2>&1 || true
  docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v --remove-orphans || true
  rm -rf "$CERT_DIR"
}
trap cleanup EXIT INT TERM

# Test-only ephemeral CA, server identity and client identity. Never committed.
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 2 \
  -keyout "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" \
  -subj "/CN=cnc-knowledge-etcd-mtls-test-ca" >/dev/null 2>&1
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
  -subj "/CN=etcd-server" >/dev/null 2>&1
cat > "$CERT_DIR/server.ext" <<'EOF'
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:etcd1,DNS:etcd2,DNS:etcd3,IP:127.0.0.1
EOF
openssl x509 -req -sha256 -days 2 -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/server.crt" -extfile "$CERT_DIR/server.ext" >/dev/null 2>&1
openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout "$CERT_DIR/client.key" -out "$CERT_DIR/client.csr" \
  -subj "/CN=cnc-knowledge-etcd-test-client" >/dev/null 2>&1
cat > "$CERT_DIR/client.ext" <<'EOF'
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF
openssl x509 -req -sha256 -days 2 -in "$CERT_DIR/client.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial \
  -out "$CERT_DIR/client.crt" -extfile "$CERT_DIR/client.ext" >/dev/null 2>&1
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 2 \
  -keyout "$CERT_DIR/untrusted-ca.key" -out "$CERT_DIR/untrusted-ca.crt" \
  -subj "/CN=cnc-knowledge-untrusted-test-ca" >/dev/null 2>&1

export ETCD_MTLS_ENDPOINTS="https://127.0.0.1:23891,https://127.0.0.1:23892,https://127.0.0.1:23893"
export ETCD_MTLS_CA="$CERT_DIR/ca.crt"
export ETCD_MTLS_CLIENT_CERT="$CERT_DIR/client.crt"
export ETCD_MTLS_CLIENT_KEY="$CERT_DIR/client.key"
export ETCD_MTLS_UNTRUSTED_CA="$CERT_DIR/untrusted-ca.crt"

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d

python3 - <<'PY'
import os
import time
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client

endpoints = [item.strip() for item in os.environ["ETCD_MTLS_ENDPOINTS"].split(",") if item.strip()]
deadline = time.monotonic() + 120
last_error = None
while time.monotonic() < deadline:
    clients = []
    try:
        for endpoint in endpoints:
            client = Etcd3gwV3Client(
                [endpoint], timeout=2.0,
                ca_cert=os.environ["ETCD_MTLS_CA"],
                cert_cert=os.environ["ETCD_MTLS_CLIENT_CERT"],
                cert_key=os.environ["ETCD_MTLS_CLIENT_KEY"],
            )
            clients.append(client)
            client.status()
        members = clients[0].members()
        if len(members) == 3:
            print("READY: all three etcd mTLS members respond; membership size=3")
            break
        last_error = RuntimeError(f"expected 3 members, got {len(members)}")
    except Exception as exc:
        last_error = exc
    finally:
        for client in clients:
            client.close()
    time.sleep(2)
else:
    raise SystemExit(f"etcd mTLS cluster did not become ready within 120s: {last_error}")
PY

ETCD_INTEGRATION=1 python3 -m unittest discover \
  -s tests \
  -p 'test_*mtls_etcd_integration.py' \
  -v

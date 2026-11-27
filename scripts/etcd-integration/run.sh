#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/scripts/etcd-integration/compose.yaml"
PROJECT_NAME="cnc-knowledge-etcd-itest"
KEEP_CLUSTER="$(printenv ETCD_KEEP_CLUSTER || true)"

cd "$ROOT_DIR"
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 2
fi
docker compose version >/dev/null
python3 -m pip install -r requirements-ch17-etcd-integration.txt

cleanup() {
  if [[ "$KEEP_CLUSTER" != "1" ]]; then
    docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v
  else
    echo "ETCD_KEEP_CLUSTER=1: leaving the three-node cluster running"
  fi
}
trap cleanup EXIT INT TERM

docker compose --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d

export ETCD_ENDPOINTS="http://127.0.0.1:23791,http://127.0.0.1:23792,http://127.0.0.1:23793"
python3 - <<'PY'
import os
import time
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client

endpoints = [item.strip() for item in os.environ["ETCD_ENDPOINTS"].split(",") if item.strip()]
deadline = time.monotonic() + 120
last_error = None
while time.monotonic() < deadline:
    clients = []
    try:
        for endpoint in endpoints:
            client = Etcd3gwV3Client([endpoint], timeout=2.0)
            clients.append(client)
            client.status()
        members = clients[0].members()
        if len(members) == 3:
            print("READY: all three etcd v3 members respond; membership size=3")
            break
        last_error = RuntimeError(f"expected 3 members, got {len(members)}")
    except Exception as exc:
        last_error = exc
    finally:
        for client in clients:
            client.close()
    time.sleep(2)
else:
    raise SystemExit(f"etcd cluster did not become ready within 120s: {last_error}")
PY

for test_file in \
  test_spare_parts_provider_authority_store_etcd_integration.py \
  test_spare_parts_provider_authority_store_member_outage_etcd_integration.py \
  test_spare_parts_provider_authority_store_quorum_loss_etcd_integration.py \
  test_spare_parts_provider_authority_store_network_partition_etcd_integration.py \
  test_spare_parts_provider_authority_store_lease_partition_etcd_integration.py \
  test_spare_parts_provider_authority_store_lease_revoke_partition_etcd_integration.py \
  test_spare_parts_provider_authority_store_lease_watch_recovery_etcd_integration.py
do
  ETCD_INTEGRATION=1 python3 -m unittest discover -s tests -p "$test_file" -v
done

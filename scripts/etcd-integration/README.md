# Three-node etcd v3 integration environment

This directory contains an opt-in disposable three-node etcd v3 integration
environment for the HTTP Gateway driver, authority-store adapter, Watch
stream, and Unified Admission/Coordinator business state machine.

## Run

Prerequisites: Docker Engine with the Compose plugin, Python 3.12, and network
access to pull quay.io/coreos/etcd:v3.7.0 and the pinned Python dependency.

From the repository root:

    bash scripts/etcd-integration/run.sh

The runner installs the optional client dependency, starts three independent
etcd 3.7.0 members with separate named data volumes, waits for all three
client endpoints and cluster membership, then runs the opt-in live integration modules. These include low-level
Range/Txn/Lease/Watch transport checks and business-level Unified Coordinator
checks using the same schema-v2 aggregate through two independent HTTP clients. The default exit handler removes the containers and volumes.
Set ETCD_KEEP_CLUSTER=1 to retain them for inspection.

The live test modules are excluded from ordinary CI execution unless
ETCD_INTEGRATION=1 is set. The Unified Coordinator suite creates a unique key
namespace per test and uses only the disposable Compose cluster; its synthetic
Provider control plane remains in-memory. The default repository workflow tests the adapter
mapping with a fake gateway transport; it does not launch Docker or claim a
live etcd integration result.

## Manual one-member outage check

The cluster uses host ports 23791, 23792 and 23793. With the cluster running:

    docker compose --project-name cnc-knowledge-etcd-itest -f scripts/etcd-integration/compose.yaml stop etcd1
    ETCD_ENDPOINTS=http://127.0.0.1:23792,http://127.0.0.1:23793 ETCD_INTEGRATION=1 python3 -m unittest discover -s tests -p 'test_*etcd_integration.py' -v
    docker compose --project-name cnc-knowledge-etcd-itest -f scripts/etcd-integration/compose.yaml start etcd1

A three-member cluster retains a majority while one member is stopped. This
does not prove tolerance of two failed members, quorum recovery under load,
disk corruption, long network partitions, clock drift, or leader-election
latency. Do not run the stop command against any non-disposable or production
cluster.

## Driver boundary

Etcd3gwV3Client implements v3 KV Range, Txn and Lease Grant/KeepAlive/Revoke
through the etcd HTTP gRPC-gateway. Safe read-only requests may move to another
configured endpoint after a transport failure. Mutating requests are sent
once; a lost Txn, LeaseGrant or LeaseRevoke response is not automatically
retried because its outcome may be unknown.

The driver intentionally does not implement normalized Watch. The etcd3gw
Watch helper yields decoded events but does not expose the complete server
response envelope needed by the existing Watch contract: response
header/revision, created, canceled, compact revision and fragment state.
The existing Watch recovery path therefore remains unavailable through this
driver. Do not treat a simplified event stream as sufficient for safe
revision-cursor advancement or compaction recovery.

This Compose topology is for disposable local development only: plaintext
HTTP, no authentication/RBAC, no mTLS, fixed ports, and no production
availability/security configuration. Use an approved secured deployment
profile before any real coordinator data or authority is introduced.

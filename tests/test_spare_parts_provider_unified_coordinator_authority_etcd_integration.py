from __future__ import annotations

import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.spare_parts_backup_storage_adapter import ProviderTaskContext
from scripts.spare_parts_fencing_attestation import Ed25519PrivateKeySigner
from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreDelete,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_coordinator_authority import (
    CoordinatorAuthorityConflictError,
    CoordinatorAuthorityStaleLeaderError,
    sign_distributed_fencing_proof,
)
from scripts.spare_parts_provider_distributed_fencing import (
    DistributedObjectFencingControlPlane,
    InMemoryConditionalObjectControlStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client
from scripts.spare_parts_provider_unified_admission_store import StoreBackedProviderAdmissionCoordinator
from scripts.spare_parts_provider_unified_coordinator_authority import StoreBackedCoordinatorAuthority


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_ENDPOINTS to run against live etcd v3",
)
class EtcdUnifiedCoordinatorAuthorityLiveTests(unittest.TestCase):
    """Run the Unified Coordinator business state machine against disposable real etcd."""

    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip() for item in os.environ.get("ETCD_ENDPOINTS", "").split(",") if item.strip()
        ]
        if not cls.endpoints:
            raise RuntimeError("ETCD_ENDPOINTS must provide etcd HTTP gateway endpoints")

    def setUp(self):
        self.prefix = f"/cnc-knowledge-it/{uuid4().hex}/unified/".encode("ascii")
        scheduler_type = type("IsolatedAdmissionScheduler", (StoreBackedProviderAdmissionCoordinator,), {
            "_PREFIX": self.prefix, "_STATE_KEY": self.prefix + b"scheduler/state",
        })
        authority_type = type("IsolatedCoordinatorAuthority", (StoreBackedCoordinatorAuthority,), {
            "_LEADER_KEY": self.prefix + b"coordinator/leader",
        })
        self.driver_a = Etcd3gwV3Client(self.endpoints, timeout=2.0)
        self.driver_b = Etcd3gwV3Client(self.endpoints, timeout=2.0)
        self.store_a = EtcdV3CoordinatorAuthorityStore(self.driver_a)
        self.store_b = EtcdV3CoordinatorAuthorityStore(self.driver_b)
        opts = {
            "global_limits": {"read": 2, "write": 4, "multipart": 2, "inventory": 1},
            "max_waiters": 8,
            "clock_fn": time.time,
        }
        self.scheduler_a = scheduler_type(self.store_a, **opts)
        self.scheduler_b = scheduler_type(self.store_b, **opts)
        self.authority_a = authority_type(self.scheduler_a, clock_fn=time.time)
        self.authority_b = authority_type(self.scheduler_b, clock_fn=time.time)
        self.leader = self.authority_a.claim_leadership("live-leader-a", ttl_seconds=30)
        self.signer = Ed25519PrivateKeySigner(
            key_id="live-test-kid-v1", private_key=Ed25519PrivateKey.generate()
        )
        self.control_store = InMemoryConditionalObjectControlStore()
        self.provider = DistributedObjectFencingControlPlane(
            self.control_store,
            trusted_ed25519_public_keys={"live-test-kid-v1": self.signer.public_key_raw()},
            trusted_issuers={"live-test-coordinator"},
            clock_fn=time.time,
        )
        self.leases = []
        self.request_ids = []
        self.scope = "tenants/tenant-A/cnc/ch17/spares/live-it"

    def tearDown(self):
        try:
            entry, _ = self.store_a.linearizable_get(self.scheduler_a._STATE_KEY)
            state = self.scheduler_a._decode(entry) if entry else None
            backend_ids = set()
            if isinstance(state, dict):
                for row in state.get("active", {}).values():
                    if isinstance(row, dict) and row.get("backend_lease_id"):
                        backend_ids.add(int(row["backend_lease_id"]))
                leader = (state.get("coordinator") or {}).get("leader")
                if isinstance(leader, dict) and leader.get("backend_lease_id"):
                    backend_ids.add(int(leader["backend_lease_id"]))
            for lease_id in backend_ids:
                try:
                    self.store_a.lease_revoke(lease_id)
                except Exception:
                    pass
            keys = {self.scheduler_a._STATE_KEY, self.authority_a._LEADER_KEY}
            keys.update(self.scheduler_a._lease_key(lease.lease_id) for lease in self.leases)
            keys.update(self.scheduler_a._request_key(item) for item in self.request_ids)
            self.store_a.transact([], [AuthorityStoreDelete(key) for key in sorted(keys)])
        except Exception:
            pass
        for driver in (getattr(self, "driver_a", None), getattr(self, "driver_b", None)):
            if driver is not None:
                driver.close()

    def acquire(self, request_id):
        self.request_ids.append(request_id)
        lease = self.scheduler_a.acquire(
            task=ProviderTaskContext(f"task-{request_id}", "tenant-A"),
            domain="write", owner_id="owner-tenant-A", lease_ttl_seconds=120,
            timeout_seconds=0, check_task=lambda _: None, request_id=request_id,
        )
        self.leases.append(lease)
        return lease

    def activate_with_provider(self, lease, idem="activate-live"):
        op = self.authority_a.prepare_activation(
            self.leader, lease, scope=self.scope, idempotency_key=idem
        )
        proof = sign_distributed_fencing_proof(
            self.authority_a, self.leader, op, lease,
            issuer_id="live-test-coordinator", signer=self.signer, clock_fn=time.time,
        )
        record = self.provider.activate_lease(self.scope, fencing_attestation=proof)
        generation = self.control_store.read_control(self.scope)[0]
        return self.authority_a.confirm_activation(
            self.leader, scope=self.scope, fencing_token=op.fencing_token,
            idempotency_key=idem, observed_provider_state=record["lease_state"],
            observed_high_water_token=record["high_water_token"],
            observed_lease_id=record["lease_id"], provider_generation=generation,
        )

    def test_real_etcd_executes_activation_publish_revocation_and_admission_guard(self):
        lease = self.acquire("live-full-lifecycle-request")
        activation = self.activate_with_provider(lease)
        self.assertEqual((activation.state, activation.fencing_token), ("ACTIVE", 1))
        publish = self.authority_a.allocate_operation_sequence(
            self.leader, lease, scope=self.scope, idempotency_key="publish-live-1",
            manifest_key=f"{self.scope}/staging/1/manifest.json", manifest_sha256="a" * 64,
        )
        proof = sign_distributed_fencing_proof(
            self.authority_a, self.leader, publish, lease,
            issuer_id="live-test-coordinator", signer=self.signer, clock_fn=time.time,
        )
        receipt = self.provider.publish_commit(self.scope, fencing_attestation=proof)
        generation = self.control_store.read_control(self.scope)[0]
        committed = self.authority_b.confirm_publish(
            self.leader, scope=self.scope, idempotency_key="publish-live-1",
            observed_provider_state="ACTIVE", observed_fencing_token=receipt.fencing_token,
            observed_operation_sequence=receipt.operation_sequence,
            observed_idempotency_key=receipt.idempotency_key,
            observed_manifest_key=receipt.manifest_key,
            observed_manifest_sha256=receipt.manifest_sha256, provider_generation=generation,
        )
        self.assertEqual(committed.state, "COMMITTED")
        revoke = self.authority_b.prepare_revocation(
            self.leader, lease, scope=self.scope, fencing_token=activation.fencing_token,
            idempotency_key="revoke-live-1",
        )
        revoke_proof = sign_distributed_fencing_proof(
            self.authority_b, self.leader, revoke, lease,
            issuer_id="live-test-coordinator", signer=self.signer, clock_fn=time.time,
        )
        revoked_record = self.provider.revoke_lease(self.scope, fencing_attestation=revoke_proof)
        generation = self.control_store.read_control(self.scope)[0]
        revoked = self.authority_a.confirm_revocation(
            self.leader, scope=self.scope, fencing_token=revoke.fencing_token,
            idempotency_key="revoke-live-1",
            observed_provider_state=revoked_record["lease_state"],
            observed_high_water_token=revoked_record["high_water_token"],
            observed_lease_id=revoked_record["lease_id"], provider_generation=generation,
        )
        self.assertEqual(revoked.state, "REVOKED")
        state_entry, _ = self.store_a.linearizable_get(self.scheduler_a._STATE_KEY)
        state = self.scheduler_a._decode(state_entry)
        self.assertEqual(state["coordinator"]["scopes"][self.scope]["lease_state"], "REVOKED")
        self.assertEqual(len(state["coordinator"]["operations"]), 3)
        self.assertTrue(self.scheduler_a.release(lease))
        with self.assertRaises(CoordinatorAuthorityConflictError):
            self.authority_b.allocate_operation_sequence(
                self.leader, lease, scope=self.scope, idempotency_key="publish-after-release",
                manifest_key=f"{self.scope}/after-release.json", manifest_sha256="b" * 64,
            )

    def test_independent_etcd_clients_allocate_unique_idempotent_sequences(self):
        lease = self.acquire("live-parallel-sequence-request")
        pending = self.authority_a.prepare_activation(
            self.leader, lease, scope=self.scope, idempotency_key="activate-parallel-live"
        )
        active = self.authority_b.confirm_activation(
            self.leader, scope=self.scope, fencing_token=pending.fencing_token,
            idempotency_key="activate-parallel-live", observed_provider_state="ACTIVE",
            observed_high_water_token=pending.fencing_token, observed_lease_id=lease.lease_id,
            provider_generation="synthetic-live-test-generation",
        )
        self.assertEqual(active.state, "ACTIVE")

        def allocate(index):
            authority = self.authority_a if index % 2 == 0 else self.authority_b
            return authority.allocate_operation_sequence(
                self.leader, lease, scope=self.scope,
                idempotency_key=f"publish-parallel-{index}",
                manifest_key=f"{self.scope}/manifest-{index}.json",
                manifest_sha256="c" * 64,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            operations = list(pool.map(allocate, range(8)))
        self.assertEqual(
            sorted(item.operation_sequence for item in operations), list(range(1, 9))
        )
        replay = self.authority_b.allocate_operation_sequence(
            self.leader, lease, scope=self.scope, idempotency_key="publish-parallel-3",
            manifest_key=f"{self.scope}/manifest-3.json", manifest_sha256="c" * 64,
        )
        self.assertEqual(replay.operation_sequence, operations[3].operation_sequence)
        self.assertEqual(self.authority_a.snapshot(self.scope)["latest_operation_sequence"], 8)

    def test_native_leader_ttl_takeover_advances_epoch_and_fences_old_leader(self):
        lease = self.acquire("live-leader-ttl-request")
        pending = self.authority_a.prepare_activation(
            self.leader, lease, scope=self.scope, idempotency_key="pending-before-takeover"
        )
        renewed = self.authority_a.renew_leadership(self.leader, ttl_seconds=1)
        self.assertEqual(renewed.epoch, self.leader.epoch)
        time.sleep(2.25)
        new_leader = self.authority_b.claim_leadership("live-leader-b", ttl_seconds=30)
        self.assertEqual(new_leader.epoch, self.leader.epoch + 1)
        with self.assertRaises(CoordinatorAuthorityStaleLeaderError):
            self.authority_a.authorize_operation_signing(self.leader, pending)
        self.assertEqual(
            [item.idempotency_key for item in self.authority_b.list_pending_operations(new_leader)],
            ["pending-before-takeover"],
        )
        self.leader = new_leader


if __name__ == "__main__":
    unittest.main()

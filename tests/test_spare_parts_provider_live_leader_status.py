import json
import unittest
from types import SimpleNamespace

from scripts.spare_parts_provider_live_leader_status import (
    CoordinatorLeaderStatusUnavailableError,
    EtcdCoordinatorLeaderStatusChecker,
)


PREFIX = b"/cnc/admission/unified/v2/"
STATE_KEY = PREFIX + b"scheduler/state"
LEADER_KEY = PREFIX + b"coordinator/leader"


class FakeLinearizableStore:
    def __init__(self, entries=(), error=None):
        self.entries = tuple(entries)
        self.error = error
        self.calls = []

    def linearizable_range(self, key, *, range_end=None):
        self.calls.append((key, range_end))
        if self.error:
            raise self.error
        return SimpleNamespace(entries=self.entries, revision=77)


def fixture():
    leader = {
        "leader_id": "coordinator-a",
        "epoch": 12,
        "expires_at": 2000.0,
        "backend_lease_id": 9001,
    }
    state = {
        "schema_version": 2,
        "coordinator": {"leader": leader, "scopes": {}, "operations": {}},
    }
    entries = (
        SimpleNamespace(key=STATE_KEY, value=json.dumps(state).encode(), lease_id=0),
        SimpleNamespace(key=LEADER_KEY, value=json.dumps(leader).encode(), lease_id=9001),
    )
    claims = {
        "coordinator_namespace": PREFIX.decode(),
        "leader_id": "coordinator-a",
        "leader_epoch": 12,
        "leader_lease_id": 9001,
        "leader_lease_expires_at_unix": 2000.0,
    }
    return entries, claims


class EtcdCoordinatorLeaderStatusCheckerTests(unittest.TestCase):
    def test_accepts_exact_live_leader_from_one_linearizable_prefix_range(self):
        entries, claims = fixture()
        store = FakeLinearizableStore(entries)
        checker = EtcdCoordinatorLeaderStatusChecker(store)

        self.assertTrue(checker.is_leader_active(claims, now_unix=1990.0))
        self.assertEqual(len(store.calls), 1)
        self.assertEqual(store.calls[0][0], PREFIX)
        self.assertEqual(store.calls[0][1], b"/cnc/admission/unified/v2" + b"0")

    def test_rejects_missing_leader_key_after_early_lease_revocation(self):
        entries, claims = fixture()
        checker = EtcdCoordinatorLeaderStatusChecker(
            FakeLinearizableStore((entries[0],))
        )
        self.assertFalse(checker.is_leader_active(claims, now_unix=1990.0))

    def test_rejects_native_lease_attachment_mismatch(self):
        entries, claims = fixture()
        wrong = SimpleNamespace(
            key=LEADER_KEY, value=entries[1].value, lease_id=9002
        )
        checker = EtcdCoordinatorLeaderStatusChecker(
            FakeLinearizableStore((entries[0], wrong))
        )
        self.assertFalse(checker.is_leader_active(claims, now_unix=1990.0))

    def test_rejects_stale_leader_identity_epoch_and_lease_claims(self):
        entries, claims = fixture()
        checker = EtcdCoordinatorLeaderStatusChecker(FakeLinearizableStore(entries))
        for field, value in (
            ("leader_id", "coordinator-old"),
            ("leader_epoch", 11),
            ("leader_lease_id", 9002),
        ):
            altered = dict(claims)
            altered[field] = value
            self.assertFalse(checker.is_leader_active(altered, now_unix=1990.0))

    def test_rejects_aggregate_and_ttl_key_value_drift(self):
        entries, claims = fixture()
        drifted_state = json.loads(entries[0].value)
        drifted_state["coordinator"]["leader"]["epoch"] = 13
        state_entry = SimpleNamespace(
            key=STATE_KEY, value=json.dumps(drifted_state).encode(), lease_id=0
        )
        checker = EtcdCoordinatorLeaderStatusChecker(
            FakeLinearizableStore((state_entry, entries[1]))
        )
        self.assertFalse(checker.is_leader_active(claims, now_unix=1990.0))

    def test_rejects_expired_lease_and_expiry_claim_drift(self):
        entries, claims = fixture()
        checker = EtcdCoordinatorLeaderStatusChecker(FakeLinearizableStore(entries))
        self.assertFalse(checker.is_leader_active(claims, now_unix=2000.0))
        altered = dict(claims, leader_lease_expires_at_unix=1999.0)
        self.assertFalse(checker.is_leader_active(altered, now_unix=1990.0))

    def test_rejects_noncanonical_namespace(self):
        entries, claims = fixture()
        checker = EtcdCoordinatorLeaderStatusChecker(FakeLinearizableStore(entries))
        for namespace in ("/cnc//bad/", "/cnc/../bad/", "cnc/no-leading-slash/"):
            altered = dict(claims, coordinator_namespace=namespace)
            self.assertFalse(checker.is_leader_active(altered, now_unix=1990.0))

    def test_store_unavailability_raises_for_fail_closed_provider_handling(self):
        _, claims = fixture()
        checker = EtcdCoordinatorLeaderStatusChecker(
            FakeLinearizableStore(error=ConnectionError("partition"))
        )
        with self.assertRaises(CoordinatorLeaderStatusUnavailableError):
            checker.is_leader_active(claims, now_unix=1990.0)


if __name__ == "__main__":
    unittest.main()

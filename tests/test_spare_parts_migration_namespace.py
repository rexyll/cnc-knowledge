from __future__ import annotations

import unittest

from scripts.spare_parts_provider_authority_store import (
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
    InMemoryEtcdV3Client,
)
from scripts.spare_parts_migration_namespace import (
    MigrationNamespaceError,
    preflight_empty_namespace,
    validate_isolated_namespace,
)


class MigrationNamespacePreflightTests(unittest.TestCase):
    def setUp(self):
        self.client = InMemoryEtcdV3Client()
        self.store = EtcdV3CoordinatorAuthorityStore(self.client)

    def test_accepts_only_one_segment_isolated_namespaces(self):
        self.assertEqual(
            validate_isolated_namespace(b"/cnc/migration/isolated/drill-2026-01/"),
            b"/cnc/migration/isolated/drill-2026-01/",
        )
        for prefix in (
            b"/cnc/admission/unified/v2/",
            b"/cnc/migration/isolated/",
            b"/cnc/migration/isolated/a/b/",
            b"/cnc/migration/isolated/../prod/",
            b"/cnc/migration/isolated/a b/",
            b"/cnc/migration/isolated/a",
        ):
            with self.subTest(prefix=prefix):
                with self.assertRaises(MigrationNamespaceError):
                    validate_isolated_namespace(prefix)

    def test_empty_namespace_returns_linearizable_revision(self):
        result = preflight_empty_namespace(
            self.store, b"/cnc/migration/isolated/empty-drill/"
        )
        self.assertEqual(result.existing_key_count, 0)
        self.assertGreaterEqual(result.revision, 0)

    def test_existing_key_blocks_preflight(self):
        self.store.transact(
            compares=[],
            success=[
                AuthorityStorePut(
                    b"/cnc/migration/isolated/used-drill/leases/one", b"{}"
                )
            ],
        )
        with self.assertRaisesRegex(MigrationNamespaceError, "not empty"):
            preflight_empty_namespace(
                self.store, b"/cnc/migration/isolated/used-drill/"
            )

    def test_adjacent_namespace_does_not_block_preflight(self):
        self.store.transact(
            compares=[],
            success=[
                AuthorityStorePut(
                    b"/cnc/migration/isolated/drill-b/leases/one", b"{}"
                )
            ],
        )
        result = preflight_empty_namespace(
            self.store, b"/cnc/migration/isolated/drill-a/"
        )
        self.assertEqual(result.existing_key_count, 0)

    def test_range_failure_is_fail_closed(self):
        class BrokenClient:
            def range(self, *args, **kwargs):
                raise ConnectionError("offline")

            def txn(self, *args, **kwargs):
                return {}

            def lease_grant(self, *args, **kwargs):
                return {}

            def lease_keepalive(self, *args, **kwargs):
                return {}

            def lease_revoke(self, *args, **kwargs):
                return {}

        broken_store = EtcdV3CoordinatorAuthorityStore(BrokenClient())
        with self.assertRaises(Exception):
            preflight_empty_namespace(
                broken_store, b"/cnc/migration/isolated/offline/"
            )


if __name__ == "__main__":
    unittest.main()

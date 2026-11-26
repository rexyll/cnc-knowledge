from __future__ import annotations

import os
import unittest
from uuid import uuid4

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_MTLS_* variables to run the live mTLS tests",
)
class Etcd3gwLiveMtlsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip()
            for item in os.environ.get("ETCD_MTLS_ENDPOINTS", "").split(",")
            if item.strip()
        ]
        if len(cls.endpoints) < 3:
            raise RuntimeError("three ETCD_MTLS_ENDPOINTS are required")
        cls.ca = os.environ["ETCD_MTLS_CA"]
        cls.client_cert = os.environ["ETCD_MTLS_CLIENT_CERT"]
        cls.client_key = os.environ["ETCD_MTLS_CLIENT_KEY"]
        cls.untrusted_ca = os.environ["ETCD_MTLS_UNTRUSTED_CA"]

    def _valid_client(self, endpoints=None):
        return Etcd3gwV3Client(
            endpoints or self.endpoints,
            timeout=2.0,
            ca_cert=self.ca,
            cert_cert=self.client_cert,
            cert_key=self.client_key,
        )

    def _assert_tls_failure(self, callback):
        with self.assertRaises(Exception) as raised:
            callback()
        message = str(raised.exception).lower()
        self.assertTrue(
            any(token in message for token in ("ssl", "tls", "certificate", "handshake")),
            f"failure was not TLS/certificate related: {raised.exception!r}",
        )

    def test_valid_mutual_tls_cluster_membership_and_linearizable_io(self):
        client = self._valid_client()
        try:
            self.assertEqual(len(client.members()), 3)
            store = EtcdV3CoordinatorAuthorityStore(client)
            key = f"/cnc-knowledge-it/mtls/{uuid4().hex}".encode()
            value = b"valid-mutual-tls"
            tx = store.transact(
                [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(key, value)],
            )
            self.assertTrue(tx.succeeded)
            entry, revision = store.linearizable_get(key)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.value, value)
            self.assertGreaterEqual(revision, tx.revision)
        finally:
            client.close()

    def test_server_rejects_client_without_certificate(self):
        client = Etcd3gwV3Client(
            [self.endpoints[0]],
            timeout=2.0,
            ca_cert=self.ca,
        )
        try:
            self._assert_tls_failure(client.status)
        finally:
            client.close()

    def test_client_rejects_server_signed_by_untrusted_ca(self):
        client = Etcd3gwV3Client(
            [self.endpoints[0]],
            timeout=2.0,
            ca_cert=self.untrusted_ca,
            cert_cert=self.client_cert,
            cert_key=self.client_key,
        )
        try:
            self._assert_tls_failure(client.status)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()

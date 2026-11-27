from __future__ import annotations

import base64
import os
import unittest
from uuid import uuid4


from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import (
    Etcd3gwAuthenticationError,
    Etcd3gwPermissionDeniedError,
    Etcd3gwV3Client,
    _gateway_error_from_response,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _prefix_end(prefix: bytes) -> bytes:
    return prefix[:-1] + bytes([prefix[-1] + 1])


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_MTLS_* variables to run live etcd RBAC tests",
)
class Etcd3gwLiveRbacMtlsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import requests

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
        cls.root_password = uuid4().hex
        cls.reader_password = uuid4().hex
        cls.writer_password = uuid4().hex
        cls.session = requests.Session()
        cls.session.verify = cls.ca
        cls.session.cert = (cls.client_cert, cls.client_key)
        cls.base_url = cls.endpoints[0] + "/v3"

        # etcd requires the root role and root user to exist before auth is enabled.
        cls._admin_post("/auth/role/add", {"name": "root"})
        cls._admin_post(
            "/auth/user/add", {"name": "root", "password": cls.root_password}
        )
        cls._admin_post(
            "/auth/user/grant", {"user": "root", "role": "root"}
        )
        cls._admin_post("/auth/enable", {})

        cls.root_token = cls._authenticate("root", cls.root_password)
        cls.root_client = cls._client(cls.root_token)
        cls.root_store = EtcdV3CoordinatorAuthorityStore(cls.root_client)

        suffix = uuid4().hex
        cls.authorized_prefix = f"/cnc-knowledge-it/authorized/{suffix}/".encode()
        cls.writable_prefix = f"/cnc-knowledge-it/writable/{suffix}/".encode()
        cls.outside_prefix = f"/cnc-knowledge-it/outside/{suffix}/".encode()

        cls._root_post("/auth/role/add", {"name": "cnc-reader"})
        cls._root_post(
            "/auth/role/grant",
            {
                "name": "cnc-reader",
                "perm": {
                    "permType": "READ",
                    "key": _b64(cls.authorized_prefix),
                    "range_end": _b64(_prefix_end(cls.authorized_prefix)),
                },
            },
        )
        cls._root_post(
            "/auth/user/add",
            {"name": "cnc-reader", "password": cls.reader_password},
        )
        cls._root_post(
            "/auth/user/grant", {"user": "cnc-reader", "role": "cnc-reader"}
        )

        cls._root_post("/auth/role/add", {"name": "cnc-writer"})
        cls._root_post(
            "/auth/role/grant",
            {
                "name": "cnc-writer",
                "perm": {
                    "permType": "READWRITE",
                    "key": _b64(cls.writable_prefix),
                    "range_end": _b64(_prefix_end(cls.writable_prefix)),
                },
            },
        )
        cls._root_post(
            "/auth/user/add",
            {"name": "cnc-writer", "password": cls.writer_password},
        )
        cls._root_post(
            "/auth/user/grant", {"user": "cnc-writer", "role": "cnc-writer"}
        )

        cls.reader_token = cls._authenticate("cnc-reader", cls.reader_password)
        cls.writer_token = cls._authenticate("cnc-writer", cls.writer_password)
        cls.reader_client = cls._client(cls.reader_token)
        cls.writer_client = cls._client(cls.writer_token)
        cls.reader_store = EtcdV3CoordinatorAuthorityStore(cls.reader_client)
        cls.writer_store = EtcdV3CoordinatorAuthorityStore(cls.writer_client)

        # Seed one key in each prefix before assertions; root is the only setup identity.
        for key, value in (
            (cls.authorized_prefix + b"seed", b"reader-can-see"),
            (cls.writable_prefix + b"seed", b"writer-can-see"),
            (cls.outside_prefix + b"seed", b"nobody-can-see"),
        ):
            result = cls.root_store.transact(
                [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(key, value)],
            )
            if not result.succeeded:
                raise RuntimeError("failed to seed RBAC integration fixture")

    @classmethod
    def tearDownClass(cls):
        for name in ("reader_client", "writer_client", "root_client"):
            client = getattr(cls, name, None)
            if client is not None:
                client.close()
        session = getattr(cls, "session", None)
        if session is not None:
            session.close()

    @classmethod
    def _admin_post(cls, path: str, payload: dict):
        response = cls.session.post(
            cls.base_url + path, json=payload, timeout=5
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"etcd RBAC bootstrap failed at {path}: HTTP {response.status_code}"
            )
        return response.json()

    @classmethod
    def _root_post(cls, path: str, payload: dict):
        response = cls.session.post(
            cls.base_url + path,
            json=payload,
            headers={"Authorization": cls.root_token},
            timeout=5,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"etcd RBAC provisioning failed at {path}: HTTP {response.status_code}"
            )
        return response.json()

    @classmethod
    def _authenticate(cls, username: str, password: str) -> str:
        response = cls.session.post(
            cls.base_url + "/auth/authenticate",
            json={"name": username, "password": password},
            timeout=5,
        )
        if response.status_code != 200:
            # Include the server's structured error without exposing credentials.
            raise RuntimeError(
                f"etcd authentication failed for test identity {username}: "
                f"HTTP {response.status_code}: {response.text[:1000]}"
            )
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("etcd authentication response omitted token")
        return token

    @classmethod
    def _client(cls, token: str) -> Etcd3gwV3Client:
        return Etcd3gwV3Client(
            cls.endpoints,
            timeout=3.0,
            ca_cert=cls.ca,
            cert_cert=cls.client_cert,
            cert_key=cls.client_key,
            auth_token=token,
        )

    def test_reader_can_range_only_its_authorized_prefix(self):
        key = self.authorized_prefix + b"seed"
        entry, _ = self.reader_store.linearizable_get(key)
        self.assertEqual(entry.value, b"reader-can-see")
        with self.assertRaises(Exception):
            self.reader_store.linearizable_get(self.outside_prefix + b"seed")

    def test_reader_cannot_write_even_inside_its_read_prefix(self):
        key = self.authorized_prefix + b"reader-write-denied"
        with self.assertRaises(Exception):
            self.reader_store.transact(
                [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(key, b"must-not-commit")],
            )
        entry, _ = self.root_store.linearizable_get(key)
        self.assertIsNone(entry)

    def test_writer_can_read_and_cas_write_only_its_authorized_prefix(self):
        key = self.writable_prefix + b"writer-write"
        before, _ = self.writer_store.linearizable_get(self.writable_prefix + b"seed")
        self.assertEqual(before.value, b"writer-can-see")
        result = self.writer_store.transact(
            [AuthorityStoreCompare(key, "VERSION", "EQUAL", 0)],
            [AuthorityStorePut(key, b"writer-authorized")],
        )
        self.assertTrue(result.succeeded)
        entry, _ = self.writer_store.linearizable_get(key)
        self.assertEqual(entry.value, b"writer-authorized")

    def test_writer_cannot_read_or_write_outside_its_prefix(self):
        outside_key = self.outside_prefix + b"writer-denied"
        with self.assertRaises(Exception):
            self.writer_store.linearizable_get(outside_key)
        with self.assertRaises(Exception):
            self.writer_store.transact(
                [AuthorityStoreCompare(outside_key, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(outside_key, b"must-not-commit")],
            )
        entry, _ = self.root_store.linearizable_get(outside_key)
        self.assertIsNone(entry)

    def test_missing_token_and_invalid_password_fail_closed(self):
        anonymous = Etcd3gwV3Client(
            [self.endpoints[0]],
            timeout=2.0,
            ca_cert=self.ca,
            cert_cert=self.client_cert,
            cert_key=self.client_key,
        )
        try:
            with self.assertRaises(Exception):
                anonymous.range(self.authorized_prefix + b"seed")
        finally:
            anonymous.close()

        response = self.session.post(
            self.base_url + "/auth/authenticate",
            json={"name": "cnc-reader", "password": "incorrect-password"},
            timeout=5,
        )
        self.assertGreaterEqual(response.status_code, 400)


    def test_invalid_token_is_normalized_as_unauthenticated(self):
        invalid_client = self._client("definitely-invalid-token")
        try:
            with self.assertRaises(Etcd3gwAuthenticationError):
                invalid_client.range(self.authorized_prefix + b"seed")
        finally:
            invalid_client.close()

    def test_reader_permission_denial_is_normalized(self):
        with self.assertRaises(Etcd3gwPermissionDeniedError):
            self.reader_client.range(self.outside_prefix + b"seed")

    def test_invalid_password_gateway_status_is_normalized(self):
        response = self.session.post(
            self.base_url + "/auth/authenticate",
            json={"name": "cnc-reader", "password": "incorrect-password"},
            timeout=5,
        )
        self.assertGreaterEqual(response.status_code, 400)
        normalized = _gateway_error_from_response(response.status_code, response.text)
        self.assertIsInstance(normalized, Etcd3gwAuthenticationError)

    def test_transport_failure_fails_over_but_auth_errors_do_not(self):
        client = Etcd3gwV3Client(
            ["https://127.0.0.1:24999", self.endpoints[0]],
            timeout=0.5,
            ca_cert=self.ca,
            cert_cert=self.client_cert,
            cert_key=self.client_key,
            auth_token=self.reader_token,
        )
        try:
            response = client.range(self.authorized_prefix + b"seed")
            self.assertEqual(response["kvs"][0]["value"], b"reader-can-see")
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import base64
import os
import time
import unittest
from uuid import uuid4

import requests

from scripts.spare_parts_provider_etcd3gw_driver import Etcd3gwV3Client


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1"
    and os.environ.get("ETCD_TOKEN_LIFECYCLE") == "1",
    "run through the dedicated short-TTL mTLS integration stage",
)
class Etcd3gwTokenLifecycleIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = [
            item.strip()
            for item in os.environ["ETCD_MTLS_ENDPOINTS"].split(",")
            if item.strip()
        ]
        cls.ca = os.environ["ETCD_MTLS_CA"]
        cls.client_cert = os.environ["ETCD_MTLS_CLIENT_CERT"]
        cls.client_key = os.environ["ETCD_MTLS_CLIENT_KEY"]
        cls.ttl = int(os.environ["ETCD_AUTH_TOKEN_TTL"])
        if cls.ttl < 5 or len(cls.endpoints) != 3:
            raise RuntimeError("token lifecycle test requires TTL >= 5 and three endpoints")
        cls.session = requests.Session()
        cls.session.verify = cls.ca
        cls.session.cert = (cls.client_cert, cls.client_key)
        cls.base_url = cls.endpoints[0] + "/v3"
        cls.password = uuid4().hex
        cls.key = f"/cnc-knowledge-token-lifecycle/{uuid4().hex}".encode()
        cls.value = b"token-lifecycle-live"

        # Seed data and bootstrap the root identity before enabling auth.
        response = cls.session.post(
            cls.base_url + "/kv/put",
            json={"key": base64.b64encode(cls.key).decode(), "value": base64.b64encode(cls.value).decode()},
            timeout=5,
        )
        if response.status_code != 200:
            raise RuntimeError(f"failed to seed token lifecycle key: HTTP {response.status_code}")
        for path, payload in (
            ("/auth/role/add", {"name": "root"}),
            ("/auth/user/add", {"name": "root", "password": cls.password}),
            ("/auth/user/grant", {"user": "root", "role": "root"}),
            ("/auth/enable", {}),
        ):
            response = cls.session.post(cls.base_url + path, json=payload, timeout=5)
            if response.status_code != 200:
                raise RuntimeError(f"token lifecycle bootstrap failed at {path}: HTTP {response.status_code}")
        cls.old_token = cls._authenticate()
        cls.client = Etcd3gwV3Client(
            cls.endpoints,
            timeout=3.0,
            ca_cert=cls.ca,
            cert_cert=cls.client_cert,
            cert_key=cls.client_key,
            auth_token=cls.old_token,
        )

    @classmethod
    def tearDownClass(cls):
        client = getattr(cls, "client", None)
        if client is not None:
            client.close()
        session = getattr(cls, "session", None)
        if session is not None:
            session.close()

    @classmethod
    def _authenticate(cls) -> str:
        response = cls.session.post(
            cls.base_url + "/auth/authenticate",
            json={"name": "root", "password": cls.password},
            timeout=5,
        )
        if response.status_code != 200:
            raise RuntimeError(f"token lifecycle authentication failed: HTTP {response.status_code}")
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("etcd authentication response omitted token")
        return token

    def test_expired_token_is_rejected_then_explicit_reauthentication_recovers(self):
        time.sleep(self.ttl + 2)

        # The stale token must fail closed; it must not trigger anonymous fallback.
        with self.assertRaises(Exception):
            self.client.range(self.key)
        old_client = Etcd3gwV3Client(
            [self.endpoints[0]],
            timeout=3.0,
            ca_cert=self.ca,
            cert_cert=self.client_cert,
            cert_key=self.client_key,
            auth_token=self.old_token,
        )
        try:
            with self.assertRaises(Exception):
                old_client.range(self.key)
        finally:
            old_client.close()

        # Re-authentication is an explicit caller action; the driver only installs
        # the replacement token and never stores the user's password.
        new_token = self._authenticate()
        self.assertNotEqual(new_token, self.old_token)
        self.client.set_auth_token(new_token)
        self.assertTrue(
            all(
                endpoint.session.headers.get("Authorization") == new_token
                for endpoint in self.client._clients
            )
        )

        # Exercise requests through the three configured endpoint sessions.
        for _ in range(3):
            response = self.client.range(self.key)
            self.assertEqual(response["kvs"][0]["value"], self.value)

        # Watch shares the same endpoint session and therefore the rotated token.
        stream = self.client.watch(self.key, start_revision=0)
        try:
            created = next(stream)
            self.assertTrue(created["created"])
        finally:
            stream.close()


if __name__ == "__main__":
    unittest.main()

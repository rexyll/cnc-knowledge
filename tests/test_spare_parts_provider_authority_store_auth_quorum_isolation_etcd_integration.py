from __future__ import annotations

import base64
import os
import subprocess
import time
import unittest
from pathlib import Path
from uuid import uuid4


from scripts.spare_parts_provider_etcd3gw_driver import (
    Etcd3gwAuthenticationError,
    Etcd3gwV3Client,
)


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1"
    and os.environ.get("ETCD_AUTH_QUORUM_ISOLATION") == "1",
    "run through the dedicated disposable mTLS auth/quorum isolation stage",
)
class Etcd3gwAuthQuorumIsolationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import requests

        cls.root_dir = Path(__file__).resolve().parents[1]
        cls.compose_file = cls.root_dir / "scripts/etcd-integration/compose-mtls.yaml"
        cls.compose_project = "cnc-knowledge-etcd-mtls-itest"
        cls.endpoints = [
            item.strip()
            for item in os.environ["ETCD_MTLS_ENDPOINTS"].split(",")
            if item.strip()
        ]
        if len(cls.endpoints) != 3:
            raise RuntimeError("auth/quorum isolation requires exactly three endpoints")
        cls.ca = os.environ["ETCD_MTLS_CA"]
        cls.client_cert = os.environ["ETCD_MTLS_CLIENT_CERT"]
        cls.client_key = os.environ["ETCD_MTLS_CLIENT_KEY"]
        cls.password = uuid4().hex
        cls.key = f"/cnc-knowledge-auth-quorum/{uuid4().hex}".encode()
        cls.value = b"valid-token-survives-member-outage"
        cls.session = requests.Session()
        cls.session.verify = cls.ca
        cls.session.cert = (cls.client_cert, cls.client_key)
        cls.base_url = cls.endpoints[0] + "/v3"

        seed = cls.session.post(
            cls.base_url + "/kv/put",
            json={
                "key": base64.b64encode(cls.key).decode(),
                "value": base64.b64encode(cls.value).decode(),
            },
            timeout=5,
        )
        if seed.status_code != 200:
            raise RuntimeError(f"failed to seed auth/quorum fixture: HTTP {seed.status_code}")
        for path, payload in (
            ("/auth/role/add", {"name": "root"}),
            ("/auth/user/add", {"name": "root", "password": cls.password}),
            ("/auth/user/grant", {"user": "root", "role": "root"}),
            ("/auth/enable", {}),
        ):
            response = cls.session.post(cls.base_url + path, json=payload, timeout=5)
            if response.status_code != 200:
                raise RuntimeError(
                    f"auth/quorum bootstrap failed at {path}: HTTP {response.status_code}"
                )
        cls.token = cls._authenticate()
        cls.client = Etcd3gwV3Client(
            [cls.endpoints[0]],
            timeout=2.0,
            ca_cert=cls.ca,
            cert_cert=cls.client_cert,
            cert_key=cls.client_key,
            auth_token=cls.token,
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
            raise RuntimeError(
                f"auth/quorum reauthentication failed: HTTP {response.status_code}"
            )
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("auth/quorum authentication response omitted token")
        return token

    @classmethod
    def _compose(cls, action: str):
        subprocess.run(
            [
                "docker", "compose", "--project-name", cls.compose_project,
                "-f", str(cls.compose_file), action, "etcd2", "etcd3",
            ],
            cwd=cls.root_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_existing_token_and_reauthentication_during_quorum_loss(self):
        # Stop two members; etcd1 remains reachable but cannot form a quorum.
        self._compose("stop")
        try:
            time.sleep(5)
            with self.assertRaises(ConnectionError):
                self.client.range(self.key)

            # Reauthentication is a separate RPC path. Record the actual Gateway
            # response rather than assuming it has the same failure as KV Range.
            response = self.session.post(
                self.base_url + "/auth/authenticate",
                json={"name": "root", "password": self.password},
                timeout=5,
            )
            print(f"AUTH_REAUTH_HTTP_STATUS_DURING_QUORUM_LOSS={response.status_code}")
            self.assertIn(response.status_code, {200, 503})
        finally:
            self._compose("start")

        deadline = time.monotonic() + 90
        last_error = None
        while time.monotonic() < deadline:
            try:
                result = self.client.range(self.key)
                self.assertEqual(result["kvs"][0]["value"], self.value)
                break
            except Etcd3gwAuthenticationError:
                # A stateful simple token may require explicit reauthentication
                # after member recovery; never retry anonymously.
                self.client.set_auth_token(self._authenticate())
            except Exception as exc:
                last_error = exc
                time.sleep(2)
        else:
            self.fail(f"cluster did not recover a valid authenticated Range: {last_error}")


if __name__ == "__main__":
    unittest.main()

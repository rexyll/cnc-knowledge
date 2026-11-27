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
    Etcd3gwPermissionDeniedError,
    Etcd3gwV3Client,
)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


@unittest.skipUnless(
    os.environ.get("ETCD_INTEGRATION") == "1"
    and os.environ.get("ETCD_MTLS_MEMBER_OUTAGE") == "1",
    "set ETCD_INTEGRATION=1 and ETCD_MTLS_MEMBER_OUTAGE=1 for live member-outage tests",
)
class Etcd3gwLiveMemberOutageAuthIntegrationTests(unittest.TestCase):
    compose_project = "cnc-knowledge-etcd-mtls-itest"
    compose_file = Path(__file__).resolve().parents[1] / "scripts/etcd-integration/compose-mtls.yaml"

    @classmethod
    def setUpClass(cls):
        import requests

        cls.requests = requests
        cls.root_dir = Path(__file__).resolve().parents[1]
        cls.endpoints = [
            item.strip()
            for item in os.environ["ETCD_MTLS_ENDPOINTS"].split(",")
            if item.strip()
        ]
        if len(cls.endpoints) != 3:
            raise RuntimeError("exactly three ETCD_MTLS_ENDPOINTS are required")
        cls.ca = os.environ["ETCD_MTLS_CA"]
        cls.client_cert = os.environ["ETCD_MTLS_CLIENT_CERT"]
        cls.client_key = os.environ["ETCD_MTLS_CLIENT_KEY"]
        cls.root_password = uuid4().hex
        cls.reader_password = uuid4().hex
        cls.session = requests.Session()
        cls.session.verify = cls.ca
        cls.session.cert = (cls.client_cert, cls.client_key)
        cls.base_url = cls.endpoints[0] + "/v3"

        cls._admin_post("/auth/role/add", {"name": "root"})
        cls._admin_post("/auth/user/add", {"name": "root", "password": cls.root_password})
        cls._admin_post("/auth/user/grant", {"user": "root", "role": "root"})
        cls._admin_post("/auth/enable", {})
        cls.root_token = cls._authenticate("root", cls.root_password)

        cls.prefix = f"/cnc-knowledge-member-outage/{uuid4().hex}/".encode()
        cls.seed_key = cls.prefix + b"seed"
        cls.outside_key = b"/cnc-knowledge-member-outage-outside/" + uuid4().hex.encode()
        cls._root_post("/auth/role/add", {"name": "cnc-reader"})
        cls._root_post(
            "/auth/role/grant",
            {
                "name": "cnc-reader",
                "perm": {
                    "permType": "READ",
                    "key": _b64(cls.prefix),
                    "range_end": _b64(cls.prefix[:-1] + bytes([cls.prefix[-1] + 1])),
                },
            },
        )
        cls._root_post(
            "/auth/user/add", {"name": "cnc-reader", "password": cls.reader_password}
        )
        cls._root_post(
            "/auth/user/grant", {"user": "cnc-reader", "role": "cnc-reader"}
        )
        cls.reader_token = cls._authenticate("cnc-reader", cls.reader_password)
        cls.root_client = cls._client(cls.root_token)
        seeded = cls.root_client.txn(
            compare=[{"key": cls.seed_key, "target": "VERSION", "result": "EQUAL", "version": 0}],
            success=[{"request_put": {"key": cls.seed_key, "value": b"reader-visible"}}],
            failure=[],
        )
        if not seeded.get("succeeded"):
            raise RuntimeError("failed to seed member-outage RBAC fixture")

        # Wait for the simple token's auth state to be accepted by every member
        # before introducing the outage. Record immediate observations without
        # assuming that Raft apply timing is identical on all members.
        cls.immediate_token_observations = cls._observe_token_on_members()
        print(
            "MEMBER_OUTAGE_TOKEN_PROPAGATION_IMMEDIATE="
            + ",".join(f"member{index + 1}:{state}" for index, state in cls.immediate_token_observations)
        )
        cls.converged_token_observations = cls._wait_for_token_on_healthy_members()
        print(
            "MEMBER_OUTAGE_TOKEN_PROPAGATION_CONVERGED="
            + ",".join(f"member{index + 1}:{state}" for index, state in cls.converged_token_observations)
        )

    @classmethod
    def tearDownClass(cls):
        client = getattr(cls, "root_client", None)
        if client is not None:
            client.close()
        session = getattr(cls, "session", None)
        if session is not None:
            session.close()

    @classmethod
    def _compose(cls, action: str, member: str):
        subprocess.run(
            [
                "docker", "compose", "--project-name", cls.compose_project,
                "-f", str(cls.compose_file), action, member,
            ],
            cwd=cls.root_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def _admin_post(cls, path: str, payload: dict):
        response = cls.session.post(cls.base_url + path, json=payload, timeout=5)
        if response.status_code != 200:
            raise RuntimeError(f"member-outage bootstrap failed at {path}: HTTP {response.status_code}")
        return response.json()

    @classmethod
    def _root_post(cls, path: str, payload: dict):
        response = cls.session.post(
            cls.base_url + path, json=payload,
            headers={"Authorization": cls.root_token}, timeout=5,
        )
        if response.status_code != 200:
            raise RuntimeError(f"member-outage RBAC provisioning failed at {path}: HTTP {response.status_code}")
        return response.json()

    @classmethod
    def _authenticate(cls, username: str, password: str) -> str:
        response = cls.session.post(
            cls.base_url + "/auth/authenticate",
            json={"name": username, "password": password}, timeout=5,
        )
        if response.status_code != 200:
            raise RuntimeError(f"member-outage authentication failed for {username}: HTTP {response.status_code}")
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("authentication response omitted token")
        return token

    @classmethod
    def _client(cls, token: str, endpoints=None, timeout=2.0):
        return Etcd3gwV3Client(
            endpoints or cls.endpoints,
            timeout=timeout,
            ca_cert=cls.ca,
            cert_cert=cls.client_cert,
            cert_key=cls.client_key,
            auth_token=token,
        )

    @classmethod
    def _direct_range(cls, endpoint: str, key: bytes):
        return cls.session.post(
            endpoint + "/v3/kv/range",
            json={"key": _b64(key), "serializable": False},
            headers={"Authorization": cls.reader_token},
            timeout=2,
        )

    @classmethod
    def _observe_token_on_members(cls):
        observations = []
        for index, endpoint in enumerate(cls.endpoints):
            try:
                response = cls._direct_range(endpoint, cls.seed_key)
                state = "accepted" if response.status_code == 200 else f"http-{response.status_code}"
            except cls.requests.exceptions.RequestException as exc:
                state = f"transport-{type(exc).__name__}"
            observations.append((index, state))
        return observations

    @classmethod
    def _wait_for_token_on_healthy_members(cls):
        deadline = time.monotonic() + 30
        last = []
        while time.monotonic() < deadline:
            last = cls._observe_token_on_members()
            if all(state == "accepted" for _, state in last):
                return last
            time.sleep(0.5)
        raise AssertionError(f"reader token did not converge on all members: {last}")

    def test_valid_rbac_token_fails_over_during_single_member_outage_and_recovers(self):
        self._compose("stop", "etcd1")
        try:
            # Verify the two surviving members remain independently reachable.
            for endpoint in self.endpoints[1:]:
                response = self._direct_range(endpoint, self.seed_key)
                self.assertEqual(response.status_code, 200, response.text[:300])

            # The driver's first endpoint is the stopped member. The read-only
            # Range must fail over on transport failure, preserving the RBAC token.
            client = self._client(self.reader_token, endpoints=self.endpoints, timeout=1.0)
            try:
                result = client.range(self.seed_key)
                self.assertEqual(result["kvs"][0]["value"], b"reader-visible")
                print("MEMBER_OUTAGE_DRIVER_RANGE=success_after_transport_failover")
            finally:
                client.close()

            # Query each surviving member directly to distinguish token acceptance
            # from the driver's endpoint failover behavior.
            for index, endpoint in enumerate(self.endpoints[1:], start=2):
                response = self._direct_range(endpoint, self.seed_key)
                print(f"MEMBER_OUTAGE_DIRECT_TOKEN_MEMBER_{index}=http-{response.status_code}")
                self.assertEqual(response.status_code, 200, response.text[:300])

            # Authorization denial must remain an authorization error, not a reason
            # to try another endpoint. The client begins with the stopped member;
            # it can only reach the healthy member after a transport failover.
            denied_client = self._client(self.reader_token, endpoints=self.endpoints, timeout=1.0)
            try:
                with self.assertRaises(Etcd3gwPermissionDeniedError):
                    denied_client.range(self.outside_key)
            finally:
                denied_client.close()
        finally:
            self._compose("start", "etcd1")

        # Wait for the restarted member to rejoin and accept the same token.
        deadline = time.monotonic() + 90
        last_status = None
        while time.monotonic() < deadline:
            try:
                response = self._direct_range(self.endpoints[0], self.seed_key)
                if response.status_code == 200:
                    last_status = "accepted"
                    break
                last_status = f"http-{response.status_code}"
            except self.requests.exceptions.RequestException as exc:
                last_status = f"transport-{type(exc).__name__}"
            time.sleep(2)
        self.assertEqual(last_status, "accepted", f"restarted member did not recover token access: {last_status}")

        recovered = self._client(self.reader_token)
        try:
            result = recovered.range(self.seed_key)
            self.assertEqual(result["kvs"][0]["value"], b"reader-visible")
        finally:
            recovered.close()
        print("MEMBER_OUTAGE_RESTARTED_MEMBER_TOKEN=accepted")


if __name__ == "__main__":
    unittest.main()

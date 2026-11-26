from __future__ import annotations

import base64
import unittest

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import (
    Etcd3gwConfigurationError,
    Etcd3gwV3Client,
)


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


class FakeGatewayClient:
    def __init__(self, host, port, protocol, **kwargs):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.kwargs = kwargs
        self.calls = []
        self.responses = {}
        self.failures = {}
        self.session = type("Session", (), {"close": lambda self: None})()

    def get_url(self, path):
        return f"{self.protocol}://{self.host}:{self.port}/v3/{path.lstrip('/')}"

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        path = url.split("/v3/", 1)[1]
        failure = self.failures.get(path)
        if failure:
            raise failure
        response = self.responses.get(path)
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise AssertionError(f"no fake response configured for {path}")
        return response


class Etcd3gwDriverContractTests(unittest.TestCase):
    def setUp(self):
        self.by_port = {}

        def factory(**kwargs):
            port = kwargs["port"]
            client = FakeGatewayClient(**kwargs)
            self.by_port[port] = client
            return client

        self.driver = Etcd3gwV3Client(
            ["http://127.0.0.1:23791", "http://127.0.0.1:23792"],
            timeout=1.75,
            client_factory=factory,
        )

    def test_range_encodes_bytes_and_preserves_header_revision(self):
        client = self.by_port[23791]
        client.responses["kv/range"] = {
            "header": {"revision": "42"},
            "kvs": [{
                "key": b64(b"/cnc/key"),
                "value": b64(b"\x00value\xff"),
                "create_revision": "3",
                "mod_revision": "42",
                "version": "7",
                "lease": "0",
            }],
        }
        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        entry, revision = store.linearizable_get(b"/cnc/key")
        self.assertEqual(revision, 42)
        self.assertEqual(entry.key, b"/cnc/key")
        self.assertEqual(entry.value, b"\x00value\xff")
        url, kwargs = client.calls[0]
        self.assertTrue(url.endswith("/v3/kv/range"))
        self.assertEqual(kwargs["json"]["key"], b64(b"/cnc/key"))
        self.assertIs(kwargs["json"]["serializable"], False)
        self.assertEqual(client.kwargs["timeout"], 1.75)

    def test_prefix_range_encodes_range_end_and_decodes_multiple_records(self):
        client = self.by_port[23791]
        client.responses["kv/range"] = {
            "header": {"revision": "8"},
            "kvs": [
                {"key": b64(b"/p/a"), "value": b64(b"A"), "create_revision": "2", "mod_revision": "8", "version": "2"},
                {"key": b64(b"/p/b"), "value": b64(b"B"), "create_revision": "3", "mod_revision": "8", "version": "1"},
            ],
        }
        response = self.driver.range(b"/p/", range_end=b"/p0", serializable=False)
        self.assertEqual(response["header"]["revision"], 8)
        self.assertEqual([entry["key"] for entry in response["kvs"]], [b"/p/a", b"/p/b"])
        self.assertEqual(client.calls[0][1]["json"]["range_end"], b64(b"/p0"))

    def test_transaction_maps_compare_put_and_decodes_header(self):
        client = self.by_port[23791]
        client.responses["kv/txn"] = {
            "header": {"revision": "51"},
            "succeeded": True,
            "responses": [{"response_put": {}}],
        }
        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        result = store.transact(
            [AuthorityStoreCompare(b"/key", "VERSION", "EQUAL", 0)],
            [AuthorityStorePut(b"/key", b"binary\x00value")],
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.revision, 51)
        url, kwargs = client.calls[0]
        self.assertTrue(url.endswith("/v3/kv/txn"))
        payload = __import__("json").loads(kwargs["data"])
        self.assertEqual(payload["compare"][0]["key"], b64(b"/key"))
        self.assertEqual(payload["compare"][0]["version"], 0)
        self.assertEqual(payload["success"][0]["request_put"]["value"], b64(b"binary\x00value"))

    def test_transaction_range_response_is_decoded_for_ordered_get(self):
        client = self.by_port[23791]
        client.responses["kv/txn"] = {
            "header": {"revision": "12"},
            "succeeded": True,
            "responses": [{
                "response_range": {
                    "header": {"revision": "12"},
                    "kvs": [{
                        "key": b64(b"/read"),
                        "value": b64(b"from-txn"),
                        "create_revision": "1",
                        "mod_revision": "12",
                        "version": "2",
                    }],
                },
            }],
        }
        raw = self.driver.txn(
            compare=[],
            success=[{"request_range": {"key": b"/read"}}],
            failure=[],
        )
        self.assertEqual(raw["responses"][0]["response_range"]["kvs"][0]["value"], b"from-txn")
        self.assertEqual(raw["header"]["revision"], 12)

    def test_lease_grant_keepalive_and_revoke_map_gateway_shapes(self):
        client = self.by_port[23791]
        client.responses["lease/grant"] = {"ID": "7001", "TTL": "30"}
        client.responses["lease/keepalive"] = {"result": {"ID": "7001", "TTL": "29"}}
        client.responses["kv/lease/revoke"] = {}
        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        lease = store.lease_grant(30)
        self.assertEqual((lease.lease_id, lease.ttl_seconds), (7001, 30))
        refreshed = store.lease_keepalive(7001)
        self.assertEqual((refreshed.lease_id, refreshed.ttl_seconds), (7001, 29))
        store.lease_revoke(7001)
        self.assertEqual(len(client.calls), 3)
        self.assertTrue(client.calls[0][0].endswith("/v3/lease/grant"))
        self.assertTrue(client.calls[1][0].endswith("/v3/lease/keepalive"))
        self.assertTrue(client.calls[2][0].endswith("/v3/kv/lease/revoke"))

    def test_read_only_range_fails_over_but_never_weakens_consistency(self):
        first = self.by_port[23791]
        second = self.by_port[23792]
        first.failures["kv/range"] = TimeoutError("first member down")
        second.responses["kv/range"] = {"header": {"revision": "4"}, "kvs": []}
        response = self.driver.range(b"/key", serializable=False)
        self.assertEqual(response["header"]["revision"], 4)
        self.assertEqual(first.calls[0][1]["json"]["serializable"], False)
        self.assertEqual(second.calls[0][1]["json"]["serializable"], False)

    def test_mutating_transaction_is_not_retried_after_transport_timeout(self):
        first = self.by_port[23791]
        second = self.by_port[23792]
        first.failures["kv/txn"] = TimeoutError("reply lost")
        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        with self.assertRaises(AuthorityStoreOutcomeUnknownError):
            store.transact([], [AuthorityStorePut(b"/once", b"value")])
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(second.calls, [])

    def test_driver_does_not_advertise_watch_without_watch_envelopes(self):
        self.assertFalse(callable(getattr(self.driver, "watch", None)))
        self.assertFalse(callable(getattr(self.driver, "watch_progress", None)))

    def test_rejects_endpoints_with_paths_credentials_or_invalid_scheme(self):
        for endpoint in (
            "http://user:pass@localhost:2379",
            "http://localhost:2379/custom",
            "ftp://localhost:2379",
            "http://localhost:2379?serializable=true",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(Etcd3gwConfigurationError):
                    Etcd3gwV3Client(endpoint, client_factory=lambda **kwargs: None)

    def test_from_env_requires_explicit_endpoint_list(self):
        with self.assertRaises(Etcd3gwConfigurationError):
            Etcd3gwV3Client.from_env(env_var="NON_EXISTENT_ETCD_ENDPOINTS_FOR_TEST")


if __name__ == "__main__":
    unittest.main()

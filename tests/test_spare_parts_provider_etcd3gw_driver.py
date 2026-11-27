from __future__ import annotations

import base64
import unittest

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreUnavailableError,
    EtcdV3CoordinatorAuthorityStore,
)
from scripts.spare_parts_provider_etcd3gw_driver import (
    Etcd3gwAuthenticationError,
    Etcd3gwConfigurationError,
    Etcd3gwPermissionDeniedError,
    Etcd3gwRequestError,
    Etcd3gwV3Client,
    _gateway_error_from_response,
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
        self.session = type("Session", (), {"close": lambda self: None, "headers": {}})()

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


class FakeStreamingResponse:
    def __init__(self, chunks, *, failure=None, status_code=200):
        self.chunks = list(chunks)
        self.failure = failure
        self.status_code = status_code
        self.text = "fake gateway error"
        self.closed = False

    def iter_content(self, chunk_size=None, decode_unicode=False):
        for chunk in self.chunks:
            yield chunk
        if self.failure is not None:
            raise self.failure

    def close(self):
        self.closed = True


class FakeStreamingSession:
    def __init__(self, responses=None, *, failure=None):
        self.responses = list(responses or [])
        self.failure = failure
        self.calls = []
        self.closed = False
        self.headers = {}

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.failure is not None:
            raise self.failure
        if not self.responses:
            raise AssertionError("no fake Watch response configured")
        return self.responses.pop(0)

    def close(self):
        self.closed = True


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
        for client in self.by_port.values():
            client.responses["lease/grant"] = {"ID": "7001", "TTL": "30"}
            client.responses["lease/keepalive"] = {"result": {"ID": "7001", "TTL": "29"}}
            client.responses["kv/lease/revoke"] = {}
        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        lease = store.lease_grant(30)
        self.assertEqual((lease.lease_id, lease.ttl_seconds), (7001, 30))
        refreshed = store.lease_keepalive(7001)
        self.assertEqual((refreshed.lease_id, refreshed.ttl_seconds), (7001, 29))
        store.lease_revoke(7001)
        calls = {
            port: [url for url, _ in client.calls]
            for port, client in self.by_port.items()
        }
        self.assertEqual(sum(len(urls) for urls in calls.values()), 3)
        self.assertEqual(
            [url.rsplit("/v3/", 1)[-1] for url in calls[23791]],
            ["lease/grant", "kv/lease/revoke"],
        )
        self.assertEqual(
            [url.rsplit("/v3/", 1)[-1] for url in calls[23792]],
            ["lease/keepalive"],
        )

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

    def test_lease_mutations_dispatch_once_and_map_transport_failures(self):
        cases = (
            ("lease_grant", "lease/grant", AuthorityStoreOutcomeUnknownError),
            ("lease_keepalive", "lease/keepalive", AuthorityStoreUnavailableError),
            ("lease_revoke", "kv/lease/revoke", AuthorityStoreOutcomeUnknownError),
        )
        for method, path, expected_error in cases:
            with self.subTest(method=method):
                clients = {}

                def factory(**kwargs):
                    client = FakeGatewayClient(**kwargs)
                    clients[kwargs["port"]] = client
                    return client

                driver = Etcd3gwV3Client(
                    ["http://127.0.0.1:23791", "http://127.0.0.1:23792"],
                    timeout=1.0,
                    client_factory=factory,
                )
                first = clients[23791]
                second = clients[23792]
                first.failures[path] = TimeoutError("synthetic response timeout")
                store = EtcdV3CoordinatorAuthorityStore(driver)
                with self.assertRaises(expected_error):
                    if method == "lease_grant":
                        store.lease_grant(30)
                    elif method == "lease_keepalive":
                        store.lease_keepalive(7001)
                    else:
                        store.lease_revoke(7001)
                self.assertEqual(len(first.calls), 1)
                self.assertTrue(first.calls[0][0].endswith(f"/v3/{path}"))
                self.assertEqual(second.calls, [])
                driver.close()

    def test_lease_mutations_keep_gateway_auth_permission_and_request_errors_typed(self):
        class Etcd3Exception(Exception):
            pass

        cases = (
            (
                "lease/grant",
                '{"code":16,"message":"etcdserver: invalid auth token"}',
                Etcd3gwAuthenticationError,
                "lease_grant",
            ),
            (
                "lease/keepalive",
                '{"code":7,"message":"etcdserver: permission denied"}',
                Etcd3gwPermissionDeniedError,
                "lease_keepalive",
            ),
            (
                "kv/lease/revoke",
                '{"code":3,"message":"etcdserver: key is empty"}',
                Etcd3gwRequestError,
                "lease_revoke",
            ),
        )
        for path, body, expected_error, method in cases:
            with self.subTest(path=path):
                clients = {}

                def factory(**kwargs):
                    client = FakeGatewayClient(**kwargs)
                    clients[kwargs["port"]] = client
                    return client

                driver = Etcd3gwV3Client(
                    ["http://127.0.0.1:23791", "http://127.0.0.1:23792"],
                    timeout=1.0,
                    client_factory=factory,
                )
                first = clients[23791]
                second = clients[23792]
                original = Etcd3Exception(body)
                first.failures[path] = original
                with self.assertRaises(expected_error) as caught:
                    if method == "lease_grant":
                        driver.lease_grant(30)
                    elif method == "lease_keepalive":
                        driver.lease_keepalive(7001)
                    else:
                        driver.lease_revoke(7001)
                self.assertIs(caught.exception.__cause__, original)
                self.assertEqual(len(first.calls), 1)
                self.assertEqual(second.calls, [])
                driver.close()

    def test_lease_mutations_dispatch_once_and_map_transport_failures(self):
        cases = (
            ("lease_grant", "lease/grant", AuthorityStoreOutcomeUnknownError),
            ("lease_keepalive", "lease/keepalive", AuthorityStoreUnavailableError),
            ("lease_revoke", "kv/lease/revoke", AuthorityStoreOutcomeUnknownError),
        )
        for method, path, expected_error in cases:
            with self.subTest(method=method):
                clients = {}

                def factory(**kwargs):
                    client = FakeGatewayClient(**kwargs)
                    clients[kwargs["port"]] = client
                    return client

                driver = Etcd3gwV3Client(
                    ["http://127.0.0.1:23791", "http://127.0.0.1:23792"],
                    timeout=1.0,
                    client_factory=factory,
                )
                first = clients[23791]
                second = clients[23792]
                first.failures[path] = TimeoutError("synthetic response timeout")
                store = EtcdV3CoordinatorAuthorityStore(driver)
                with self.assertRaises(expected_error):
                    if method == "lease_grant":
                        store.lease_grant(30)
                    elif method == "lease_keepalive":
                        store.lease_keepalive(7001)
                    else:
                        store.lease_revoke(7001)
                self.assertEqual(len(first.calls), 1)
                self.assertTrue(first.calls[0][0].endswith(f"/v3/{path}"))
                self.assertEqual(second.calls, [])
                driver.close()

    def test_lease_mutations_keep_gateway_auth_permission_and_request_errors_typed(self):
        class Etcd3Exception(Exception):
            pass

        cases = (
            (
                "lease/grant",
                '{"code":16,"message":"etcdserver: invalid auth token"}',
                Etcd3gwAuthenticationError,
                "lease_grant",
            ),
            (
                "lease/keepalive",
                '{"code":7,"message":"etcdserver: permission denied"}',
                Etcd3gwPermissionDeniedError,
                "lease_keepalive",
            ),
            (
                "kv/lease/revoke",
                '{"code":3,"message":"etcdserver: key is empty"}',
                Etcd3gwRequestError,
                "lease_revoke",
            ),
        )
        for path, body, expected_error, method in cases:
            with self.subTest(path=path):
                clients = {}

                def factory(**kwargs):
                    client = FakeGatewayClient(**kwargs)
                    clients[kwargs["port"]] = client
                    return client

                driver = Etcd3gwV3Client(
                    ["http://127.0.0.1:23791", "http://127.0.0.1:23792"],
                    timeout=1.0,
                    client_factory=factory,
                )
                first = clients[23791]
                second = clients[23792]
                original = Etcd3Exception(body)
                first.failures[path] = original
                with self.assertRaises(expected_error) as caught:
                    if method == "lease_grant":
                        driver.lease_grant(30)
                    elif method == "lease_keepalive":
                        driver.lease_keepalive(7001)
                    else:
                        driver.lease_revoke(7001)
                self.assertIs(caught.exception.__cause__, original)
                self.assertEqual(len(first.calls), 1)
                self.assertEqual(second.calls, [])
                driver.close()

    def test_watch_preserves_complete_envelope_and_decodes_event_bytes(self):
        client = self.by_port[23791]
        key = b"/watch/a"
        value = b"\\x00value\\xff"
        previous = b"old-value"
        frames = [
            {"result": {"header": {"revision": "10"}, "watch_id": "9", "created": True}},
            {
                "result": {
                    "header": {"revision": "11"},
                    "watch_id": "9",
                    "fragment": True,
                    "events": [{
                        "kv": {
                            "key": b64(key), "value": b64(value),
                            "create_revision": "4", "mod_revision": "11",
                            "version": "2", "lease": "0"
                        },
                        "prev_kv": {
                            "key": b64(key), "value": b64(previous),
                            "create_revision": "4", "mod_revision": "8",
                            "version": "1", "lease": "0"
                        }
                    }]
                }
            },
            {
                "result": {
                    "header": {"revision": "12"},
                    "watch_id": "9",
                    "fragment": False,
                    "events": [{
                        "type": "DELETE",
                        "kv": {
                            "key": b64(key), "create_revision": "4",
                            "mod_revision": "12", "version": "0", "lease": "0"
                        },
                        "prev_kv": {
                            "key": b64(key), "value": b64(value),
                            "create_revision": "4", "mod_revision": "11",
                            "version": "2", "lease": "0"
                        }
                    }]
                }
            },
            {
                "result": {
                    "header": {"revision": "12"},
                    "watch_id": "9",
                    "canceled": True,
                    "compact_revision": "7",
                    "cancel_reason": "required revision has been compacted"
                }
            }
        ]
        stream_bytes = b"".join(
            __import__("json").dumps(frame, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            for frame in frames
        )
        # Deliberately split JSON keys, base64 payloads and UTF-8/text boundaries.
        chunks = [stream_bytes[:5], stream_bytes[5:31], stream_bytes[31:88], stream_bytes[88:173], stream_bytes[173:]]
        response = FakeStreamingResponse(chunks)
        client.session = FakeStreamingSession([response])

        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        stream = store.watch(
            b"/watch/",
            start_revision=10,
            range_end=b"/watch0",
            progress_notify=True,
            prev_kv=True,
        )
        created = next(stream)
        self.assertTrue(created.created)
        self.assertEqual((created.watch_id, created.header_revision), (9, 10))

        put = next(stream)
        self.assertTrue(put.fragment)
        self.assertEqual(put.events[0].event_type, "PUT")
        self.assertEqual(put.events[0].key, key)
        self.assertEqual(put.events[0].entry.value, value)
        self.assertEqual(put.events[0].previous_entry.value, previous)

        deleted = next(stream)
        self.assertFalse(deleted.fragment)
        self.assertEqual(deleted.events[0].event_type, "DELETE")
        self.assertEqual(deleted.events[0].previous_entry.value, value)

        canceled = next(stream)
        self.assertTrue(canceled.canceled)
        self.assertEqual(canceled.compact_revision, 7)
        self.assertEqual(canceled.cancel_reason, "required revision has been compacted")
        self.assertIsNone(canceled.resume_revision)
        with self.assertRaises(StopIteration):
            next(stream)
        self.assertTrue(response.closed)

        url, kwargs = client.session.calls[0]
        self.assertTrue(url.endswith("/v3/watch"))
        self.assertTrue(kwargs["stream"])
        self.assertEqual(kwargs["timeout"], (1.75, None))
        create = kwargs["json"]["create_request"]
        self.assertEqual(create["key"], b64(b"/watch/"))
        self.assertEqual(create["range_end"], b64(b"/watch0"))
        self.assertEqual(create["start_revision"], 10)
        self.assertIs(create["progress_notify"], True)
        self.assertIs(create["prev_kv"], True)

    def test_watch_establishment_failover_and_stream_disconnect_are_explicit(self):
        first = self.by_port[23791]
        second = self.by_port[23792]
        first.session = FakeStreamingSession(failure=ConnectionError("first endpoint down"))
        created = {"result": {"header": {"revision": "20"}, "watch_id": "4", "created": True}}
        response = FakeStreamingResponse([
            __import__("json").dumps(created).encode("utf-8")
        ], failure=ConnectionError("stream disconnected"))
        second.session = FakeStreamingSession([response])

        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        stream = store.watch(b"/watch/disconnect", start_revision=20)
        created_response = next(stream)
        self.assertTrue(created_response.created)
        with self.assertRaises(AuthorityStoreUnavailableError):
            next(stream)
        self.assertEqual(len(first.session.calls), 1)
        self.assertEqual(len(second.session.calls), 1)
        self.assertTrue(response.closed)

    def test_watch_preserves_progress_notification_without_events_and_cursor(self):
        client = self.by_port[23791]
        frames = [
            {
                "result": {
                    "header": {"revision": "10"},
                    "watch_id": "9",
                    "created": True,
                    "events": [],
                }
            },
            {
                "result": {
                    "header": {"revision": "12"},
                    "watch_id": "9",
                    "events": [],
                }
            },
        ]
        response = FakeStreamingResponse([
            __import__("json").dumps(frame).encode("utf-8") for frame in frames
        ])
        client.session = FakeStreamingSession([response])

        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        stream = store.watch(
            b"/watch/progress",
            start_revision=11,
            progress_notify=True,
            prev_kv=True,
        )
        created = next(stream)
        self.assertTrue(created.created)
        self.assertEqual(created.watch_id, 9)

        progress = next(stream)
        self.assertTrue(progress.is_progress)
        self.assertFalse(progress.created)
        self.assertFalse(progress.canceled)
        self.assertEqual(progress.watch_id, created.watch_id)
        self.assertEqual(progress.header_revision, 12)
        self.assertEqual(progress.events, ())
        self.assertEqual(progress.resume_revision, 13)

        url, kwargs = client.session.calls[0]
        self.assertTrue(url.endswith("/v3/watch"))
        self.assertIs(kwargs["json"]["create_request"]["progress_notify"], True)
        stream.close()
        self.assertTrue(response.closed)

    def test_watch_clean_eof_without_terminal_control_frame_is_a_disconnect(self):
        client = self.by_port[23791]
        created = {
            "result": {
                "header": {"revision": "20"},
                "watch_id": "4",
                "created": True,
            }
        }
        response = FakeStreamingResponse([
            __import__("json").dumps(created).encode("utf-8")
        ])
        client.session = FakeStreamingSession([response])

        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        stream = store.watch(b"/watch/unexpected-eof", start_revision=20)
        opened = next(stream)
        self.assertTrue(opened.created)
        self.assertEqual(opened.header_revision, 20)

        # A clean TCP/HTTP EOF is not a normal Watch completion: etcd signals
        # server-side cancellation with an explicit canceled WatchResponse.
        with self.assertRaises(AuthorityStoreUnavailableError):
            next(stream)
        self.assertTrue(response.closed)

    def test_watch_read_timeout_is_applied_and_surfaces_transport_stall(self):
        client = self.by_port[23791]
        created = {
            "result": {
                "header": {"revision": "20"},
                "watch_id": "4",
                "created": True,
            }
        }
        response = FakeStreamingResponse(
            [__import__("json").dumps(created).encode("utf-8")],
            failure=TimeoutError("watch response read timed out"),
        )
        client.session = FakeStreamingSession([response])

        driver = Etcd3gwV3Client(
            ["http://127.0.0.1:23791"],
            timeout=1.75,
            watch_read_timeout=4.5,
            client_factory=lambda **kwargs: client,
        )
        store = EtcdV3CoordinatorAuthorityStore(driver)
        stream = store.watch(
            b"/watch/read-timeout",
            start_revision=20,
            progress_notify=True,
        )
        opened = next(stream)
        self.assertTrue(opened.created)
        with self.assertRaises(AuthorityStoreUnavailableError):
            next(stream)

        _, request = client.session.calls[0]
        self.assertEqual(request["timeout"], (1.75, 4.5))
        self.assertTrue(request["json"]["create_request"]["progress_notify"])
        self.assertTrue(response.closed)
        driver.close()

    def test_watch_read_timeout_must_be_positive_or_none(self):
        for value in (0, -1, True, "4"):
            with self.subTest(value=value):
                with self.assertRaises(Etcd3gwConfigurationError):
                    Etcd3gwV3Client(
                        "http://127.0.0.1:23791",
                        watch_read_timeout=value,
                        client_factory=lambda **kwargs: None,
                    )

    def test_watch_compaction_cancel_without_gateway_header_is_preserved(self):
        client = self.by_port[23791]
        canceled_frame = {
            "result": {
                "watch_id": "10",
                "canceled": True,
                "compact_revision": "27",
                "cancel_reason": "required revision has been compacted",
            }
        }
        response = FakeStreamingResponse([
            __import__("json").dumps(canceled_frame).encode("utf-8")
        ])
        client.session = FakeStreamingSession([response])

        store = EtcdV3CoordinatorAuthorityStore(self.driver)
        stream = store.watch(b"/watch/compacted", start_revision=20)
        canceled = next(stream)
        self.assertTrue(canceled.canceled)
        self.assertEqual(canceled.compact_revision, 27)
        self.assertIn("compacted", canceled.cancel_reason)
        self.assertEqual(canceled.header_revision, 0)
        self.assertIsNone(canceled.resume_revision)
        with self.assertRaises(StopIteration):
            next(stream)
        self.assertTrue(response.closed)

    def test_watch_close_before_first_frame_releases_http_response(self):
        client = self.by_port[23791]
        response = FakeStreamingResponse([])
        client.session = FakeStreamingSession([response])
        stream = self.driver.watch(b"/watch/close")
        stream.close()
        self.assertTrue(response.closed)

    def test_watch_progress_is_not_advertised_without_bidirectional_gateway_support(self):
        self.assertTrue(callable(getattr(self.driver, "watch", None)))
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

    def test_auth_token_is_applied_to_every_endpoint_session(self):
        clients = {}

        def factory(**kwargs):
            client = FakeGatewayClient(**kwargs)
            clients[kwargs["port"]] = client
            return client

        driver = Etcd3gwV3Client(
            ["https://127.0.0.1:23791", "https://127.0.0.1:23792"],
            ca_cert="/tmp/test-ca.pem",
            cert_cert="/tmp/test-client.pem",
            cert_key="/tmp/test-client-key.pem",
            auth_token="opaque-test-token",
            client_factory=factory,
        )
        self.assertEqual(
            [client.session.headers["Authorization"] for client in clients.values()],
            ["opaque-test-token", "opaque-test-token"],
        )
        self.assertTrue(all(client.kwargs["ca_cert"] == "/tmp/test-ca.pem" for client in clients.values()))
        self.assertTrue(all(client.kwargs["cert_cert"] == "/tmp/test-client.pem" for client in clients.values()))
        driver.close()

    def test_rejects_empty_auth_token(self):
        with self.assertRaises(Etcd3gwConfigurationError):
            Etcd3gwV3Client(
                "https://127.0.0.1:23791",
                auth_token=" ",
                client_factory=lambda **kwargs: FakeGatewayClient(**kwargs),
            )

    def test_auth_token_can_be_rotated_and_cleared_on_every_endpoint(self):
        clients = {}

        def factory(**kwargs):
            client = FakeGatewayClient(**kwargs)
            clients[kwargs["port"]] = client
            return client

        driver = Etcd3gwV3Client(
            ["https://127.0.0.1:23791", "https://127.0.0.1:23792"],
            auth_token="old-token",
            client_factory=factory,
        )
        self.assertEqual(
            [client.session.headers["Authorization"] for client in clients.values()],
            ["old-token", "old-token"],
        )
        driver.set_auth_token("new-token")
        self.assertEqual(
            [client.session.headers["Authorization"] for client in clients.values()],
            ["new-token", "new-token"],
        )
        driver.set_auth_token(None)
        self.assertTrue(
            all("Authorization" not in client.session.headers for client in clients.values())
        )
        with self.assertRaises(Etcd3gwConfigurationError):
            driver.set_auth_token(" ")
        driver.close()

    def test_gateway_error_classification_uses_http_and_grpc_status(self):
        self.assertIsInstance(
            _gateway_error_from_response(401, '{"code":16,"message":"etcdserver: invalid auth token"}'),
            Etcd3gwAuthenticationError,
        )
        self.assertIsInstance(
            _gateway_error_from_response(403, '{"code":7,"message":"etcdserver: permission denied"}'),
            Etcd3gwPermissionDeniedError,
        )
        self.assertIsInstance(
            _gateway_error_from_response(400, '{"code":3,"message":"etcdserver: authentication failed, invalid user ID or password"}'),
            Etcd3gwAuthenticationError,
        )
        self.assertIsInstance(
            _gateway_error_from_response(400, '{"code":3,"message":"etcdserver: key is empty"}'),
            Etcd3gwRequestError,
        )
        self.assertIsInstance(
            _gateway_error_from_response(418, 'not-json'),
            Etcd3gwRequestError,
        )

    def test_authentication_exception_is_not_treated_as_transport_failover(self):
        class Etcd3Exception(Exception):
            pass

        first = self.by_port[23791]
        second = self.by_port[23792]
        original = Etcd3Exception(
            '{"code":16,"message":"etcdserver: invalid auth token"}',
            "Unauthorized",
        )
        first.failures["kv/range"] = original
        with self.assertRaises(Etcd3gwAuthenticationError) as caught:
            self.driver.range(b"/protected")
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(second.calls, [])

    def test_permission_denied_exception_is_not_treated_as_transport_failover(self):
        class Etcd3Exception(Exception):
            pass

        first = self.by_port[23791]
        second = self.by_port[23792]
        first.failures["kv/range"] = Etcd3Exception(
            '{"code":7,"message":"etcdserver: permission denied"}'
        )
        with self.assertRaises(Etcd3gwPermissionDeniedError):
            self.driver.range(b"/outside-prefix")
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(second.calls, [])

    def test_gateway_watch_permission_error_is_typed_and_not_failed_over(self):
        first = self.by_port[23791]
        second = self.by_port[23792]
        response = FakeStreamingResponse(
            [], status_code=403
        )
        response.text = '{"code":7,"message":"etcdserver: permission denied"}'
        first.session = FakeStreamingSession([response])
        second.session = FakeStreamingSession([])
        with self.assertRaises(Etcd3gwPermissionDeniedError):
            self.driver.watch(b"/outside-prefix")
        self.assertTrue(response.closed)
        self.assertEqual(len(first.session.calls), 1)
        self.assertEqual(second.session.calls, [])

    def test_from_env_requires_explicit_endpoint_list(self):
        with self.assertRaises(Etcd3gwConfigurationError):
            Etcd3gwV3Client.from_env(env_var="NON_EXISTENT_ETCD_ENDPOINTS_FOR_TEST")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""etcd v3 gRPC-gateway adapter backed by the OpenStack etcd3gw client.

KV Range, Txn and Lease use the pinned etcd3gw client. Watch uses its configured
HTTP session directly because etcd3gw's convenience iterator drops control
fields from WatchResponse. The raw server stream preserves the complete
response envelope. The HTTP gateway path supports a server stream created by
one request; it does not expose bidirectional WatchProgress/WatchCancel here.
"""
from __future__ import annotations

import base64
import codecs
import json
import os
import threading
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlsplit


class Etcd3gwConfigurationError(ValueError):
    """Invalid etcd endpoint or client configuration."""


class Etcd3gwProtocolError(RuntimeError):
    """Unexpected etcd gateway response shape."""


def _encode_bytes(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise TypeError("etcd keys and values must be bytes")
    return base64.b64encode(value).decode("ascii")


def _decode_bytes(value: Any) -> bytes:
    if value in (None, ""):
        return b""
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        raise Etcd3gwProtocolError("etcd gateway byte field is not base64 text")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise Etcd3gwProtocolError("etcd gateway returned invalid base64 data") from exc


def _field(mapping: Mapping[str, Any], snake_name: str, camel_name: str | None = None) -> Any:
    if snake_name in mapping:
        return mapping[snake_name]
    if camel_name and camel_name in mapping:
        return mapping[camel_name]
    return None


def _decode_kv(kv: Mapping[str, Any]) -> dict[str, Any]:
    key = _field(kv, "key")
    if key is None:
        raise Etcd3gwProtocolError("etcd gateway KV response is missing key")
    return {
        "key": _decode_bytes(key),
        "value": _decode_bytes(_field(kv, "value")),
        "create_revision": int(_field(kv, "create_revision", "createRevision") or 0),
        "mod_revision": int(_field(kv, "mod_revision", "modRevision") or 0),
        "version": int(_field(kv, "version") or 0),
        "lease": int(_field(kv, "lease") or 0),
    }


def _transport_error(exc: Exception) -> Exception:
    """Translate etcd3gw's named transport exceptions to built-in exceptions."""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return exc
    name = type(exc).__name__
    if name in {"ConnectionTimeoutError", "Timeout", "ReadTimeout"}:
        return TimeoutError(str(exc))
    if name in {"ConnectionFailedError", "ConnectionError", "ConnectTimeout"}:
        return ConnectionError(str(exc))
    return exc



def _iter_json_stream(response: Any) -> Iterator[Mapping[str, Any]]:
    """Decode concatenated/line-delimited JSON documents from an HTTP stream.

    HTTP chunk boundaries are not assumed to match JSON object boundaries.
    """
    utf8 = codecs.getincrementaldecoder("utf-8")()
    parser = json.JSONDecoder()
    buffer = ""

    def extract(final: bool = False) -> Iterator[Mapping[str, Any]]:
        nonlocal buffer
        while True:
            buffer = buffer.lstrip()
            if not buffer:
                return
            try:
                value, end = parser.raw_decode(buffer)
            except json.JSONDecodeError as exc:
                if final:
                    raise Etcd3gwProtocolError(
                        "etcd Watch stream ended with an incomplete JSON frame"
                    ) from exc
                return
            if not isinstance(value, Mapping):
                raise Etcd3gwProtocolError(
                    "etcd Watch stream frame must be a JSON object"
                )
            buffer = buffer[end:]
            yield value

    try:
        for chunk in response.iter_content(chunk_size=None, decode_unicode=False):
            if not chunk:
                continue
            if isinstance(chunk, str):
                buffer += chunk
            else:
                try:
                    buffer += utf8.decode(bytes(chunk), final=False)
                except UnicodeDecodeError as exc:
                    raise Etcd3gwProtocolError(
                        "etcd Watch stream contains invalid UTF-8"
                    ) from exc
            yield from extract()
        try:
            buffer += utf8.decode(b"", final=True)
        except UnicodeDecodeError as exc:
            raise Etcd3gwProtocolError(
                "etcd Watch stream ends in an incomplete UTF-8 sequence"
            ) from exc
        yield from extract(final=True)
    except Etcd3gwProtocolError:
        raise
    except Exception:
        raise


def _normalize_watch_response(envelope: Mapping[str, Any]) -> dict[str, Any]:
    result = envelope.get("result")
    if not isinstance(result, Mapping):
        raise Etcd3gwProtocolError(
            "etcd Watch stream frame is missing the result envelope"
        )

    raw_header = result.get("header")
    if not isinstance(raw_header, Mapping):
        raise Etcd3gwProtocolError(
            "etcd Watch response is missing its response header"
        )
    revision = _field(raw_header, "revision")
    if revision is None:
        raise Etcd3gwProtocolError(
            "etcd Watch response header is missing revision"
        )
    header = dict(raw_header)
    header["revision"] = int(revision)

    raw_events = result.get("events") or []
    if not isinstance(raw_events, list):
        raise Etcd3gwProtocolError("etcd Watch events must be an array")
    events: list[dict[str, Any]] = []
    for raw_event in raw_events:
        if not isinstance(raw_event, Mapping):
            raise Etcd3gwProtocolError("etcd Watch event is malformed")
        event_type = raw_event.get("type")
        # In proto3 JSON, the zero-valued enum (PUT) may be omitted.
        # DELETE is non-zero and remains explicitly represented.
        if event_type is None or event_type == 0 or event_type == "0":
            event_type = "PUT"
        elif isinstance(event_type, bool):
            raise Etcd3gwProtocolError("etcd Watch event type is invalid")
        elif isinstance(event_type, int):
            event_type = {1: "DELETE"}.get(event_type)
        elif isinstance(event_type, str):
            event_type = event_type.upper()
            if event_type.startswith("EVENT_TYPE_"):
                event_type = event_type.removeprefix("EVENT_TYPE_")
            if event_type == "1":
                event_type = "DELETE"
        if event_type not in {"PUT", "DELETE"}:
            raise Etcd3gwProtocolError("etcd Watch event type is invalid")

        raw_kv = raw_event.get("kv")
        if not isinstance(raw_kv, Mapping):
            raise Etcd3gwProtocolError("etcd Watch event is missing its KV")
        event = dict(raw_event)
        event["type"] = event_type
        event["kv"] = _decode_kv(raw_kv)

        raw_previous = raw_event.get("prev_kv", raw_event.get("prevKv"))
        if raw_previous is not None:
            if not isinstance(raw_previous, Mapping):
                raise Etcd3gwProtocolError("etcd Watch previous KV is malformed")
            event["prev_kv"] = _decode_kv(raw_previous)
        events.append(event)

    watch_id = _field(result, "watch_id", "watchId")
    compact_revision = _field(result, "compact_revision", "compactRevision")
    cancel_reason = _field(result, "cancel_reason", "cancelReason")
    return {
        "header": header,
        "watch_id": int(watch_id or 0),
        "created": bool(result.get("created", False)),
        "canceled": bool(result.get("canceled", False)),
        "compact_revision": int(compact_revision or 0),
        "cancel_reason": str(cancel_reason or ""),
        "fragment": bool(result.get("fragment", False)),
        "events": events,
    }


class _Etcd3gwWatchStream:
    """Closeable iterator over complete WatchResponse envelopes."""

    def __init__(self, response: Any):
        self._response = response
        self._frames = _iter_json_stream(response)
        self._closed = False

    def __iter__(self) -> "_Etcd3gwWatchStream":
        return self

    def __next__(self) -> Mapping[str, Any]:
        if self._closed:
            raise StopIteration
        try:
            envelope = next(self._frames)
            return _normalize_watch_response(envelope)
        except StopIteration:
            self.close()
            raise
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close_iterator = getattr(self._frames, "close", None)
        if callable(close_iterator):
            close_iterator()
        close_response = getattr(self._response, "close", None)
        if callable(close_response):
            close_response()


class Etcd3gwV3Client:
    """Concrete EtcdV3Client using etcd's HTTP gRPC-gateway v3 API.

    Read-only Range/status/member-list calls may fail over to the next endpoint.
    Mutating Txn and Lease calls are never retried across endpoints: a lost
    response can have an unknown outcome and must be reconciled by the caller.
    """

    def __init__(
        self,
        endpoints: Sequence[str] | str,
        *,
        timeout: float = 3.0,
        ca_cert: str | None = None,
        cert_key: str | None = None,
        cert_cert: str | None = None,
        auth_token: str | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if isinstance(endpoints, str):
            endpoint_list = [item.strip() for item in endpoints.split(",") if item.strip()]
        else:
            endpoint_list = [str(item).strip() for item in endpoints if str(item).strip()]
        if not endpoint_list:
            raise Etcd3gwConfigurationError("at least one etcd endpoint is required")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            raise Etcd3gwConfigurationError("timeout must be a positive number")
        if bool(cert_key) != bool(cert_cert):
            raise Etcd3gwConfigurationError("mTLS requires both cert_key and cert_cert")
        if auth_token is not None and (
            not isinstance(auth_token, str) or not auth_token.strip()
        ):
            raise Etcd3gwConfigurationError("auth_token must be a non-empty string")

        if client_factory is None:
            try:
                from etcd3gw.client import Etcd3Client
            except ImportError as exc:
                raise RuntimeError(
                    "Etcd3gwV3Client requires the optional dependency "
                    "etcd3gw; install requirements-ch17-etcd-integration.txt"
                ) from exc
            client_factory = Etcd3Client

        self.timeout = float(timeout)
        self.endpoints = tuple(endpoint_list)
        self._clients: list[Any] = []
        self._next_index = 0
        self._lock = threading.Lock()
        self._auth_token = auth_token

        for endpoint in self.endpoints:
            parsed = self._parse_endpoint(endpoint)
            kwargs = {
                "host": parsed[0],
                "port": parsed[1],
                "protocol": parsed[2],
                "ca_cert": ca_cert,
                "cert_key": cert_key,
                "cert_cert": cert_cert,
                "timeout": self.timeout,
                "api_path": "/v3/",
            }
            try:
                client = client_factory(**kwargs)
            except TypeError:
                raise
            self._clients.append(client)

        if auth_token is not None:
            self.set_auth_token(auth_token)

    def set_auth_token(self, auth_token: str | None) -> None:
        """Replace or clear the bearer token on every endpoint session.

        Authentication itself is deliberately external: callers obtain a new
        token through their credential provider and then install it here.
        This method does not retain usernames/passwords or refresh tokens.
        """
        if auth_token is not None and (
            not isinstance(auth_token, str) or not auth_token.strip()
        ):
            raise Etcd3gwConfigurationError("auth_token must be a non-empty string")
        with self._lock:
            sessions = [getattr(client, "session", None) for client in self._clients]
            for session in sessions:
                headers = getattr(session, "headers", None)
                if headers is None or not hasattr(headers, "__setitem__"):
                    raise Etcd3gwConfigurationError(
                        "authenticated clients require a mutable HTTP session headers mapping"
                    )
            for headers in (session.headers for session in sessions):
                if auth_token is None:
                    headers.pop("Authorization", None)
                else:
                    headers["Authorization"] = auth_token
            self._auth_token = auth_token

    @classmethod
    def from_env(cls, *, env_var: str = "ETCD_ENDPOINTS", **kwargs: Any) -> "Etcd3gwV3Client":
        endpoints = os.environ.get(env_var, "")
        if not endpoints.strip():
            raise Etcd3gwConfigurationError(
                f"{env_var} must contain a comma-separated endpoint list"
            )
        return cls(endpoints, **kwargs)

    @staticmethod
    def _parse_endpoint(endpoint: str) -> tuple[str, int, str]:
        try:
            parsed = urlsplit(endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("endpoint must be an http(s) URL with a host")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("endpoint must not contain credentials, query or fragment")
            if parsed.path not in {"", "/"}:
                raise ValueError("endpoint path is not supported; API path is fixed to /v3/")
            port = parsed.port or (443 if parsed.scheme == "https" else 2379)
            if not 1 <= port <= 65535:
                raise ValueError("endpoint port is out of range")
            return parsed.hostname, port, parsed.scheme
        except ValueError as exc:
            raise Etcd3gwConfigurationError(f"invalid endpoint {endpoint!r}: {exc}") from exc

    def _take_start_index(self) -> int:
        with self._lock:
            index = self._next_index
            self._next_index = (self._next_index + 1) % len(self._clients)
            return index

    def _post(
        self,
        path: str,
        payload: Mapping[str, Any],
        *,
        read_only: bool,
        encode_as_json: bool = True,
    ) -> Mapping[str, Any]:
        start = self._take_start_index()
        count = len(self._clients) if read_only else 1
        last_transport_error: Exception | None = None
        for offset in range(count):
            index = (start + offset) % len(self._clients)
            client = self._clients[index]
            try:
                url = client.get_url(path)
                if encode_as_json:
                    response = client.post(url, json=dict(payload))
                else:
                    response = client.post(
                        url,
                        data=json.dumps(payload, separators=(",", ":")),
                    )
            except Exception as exc:
                translated = _transport_error(exc)
                if read_only and isinstance(translated, (TimeoutError, ConnectionError)):
                    last_transport_error = translated
                    continue
                if translated is not exc:
                    raise translated from exc
                raise
            if not isinstance(response, Mapping):
                raise Etcd3gwProtocolError("etcd gateway response must be a JSON object")
            return response
        if last_transport_error is not None:
            raise last_transport_error
        raise ConnectionError("no etcd endpoint could be reached")

    def range(
        self,
        key: bytes,
        *,
        range_end: bytes | None = None,
        serializable: bool = False,
    ) -> Mapping[str, Any]:
        if not isinstance(key, bytes) or not key:
            raise ValueError("Range key must be non-empty bytes")
        if range_end is not None and not isinstance(range_end, bytes):
            raise ValueError("Range range_end must be bytes or None")
        payload: dict[str, Any] = {
            "key": _encode_bytes(key),
            "serializable": bool(serializable),
        }
        if range_end is not None:
            payload["range_end"] = _encode_bytes(range_end)
        response = self._post("/kv/range", payload, read_only=True)
        result = dict(response)
        kvs = _field(response, "kvs")
        if kvs is not None:
            if not isinstance(kvs, list):
                raise Etcd3gwProtocolError("etcd Range kvs is not an array")
            result["kvs"] = [_decode_kv(item) for item in kvs]
        header = _field(response, "header")
        if not isinstance(header, Mapping):
            raise Etcd3gwProtocolError("etcd Range response is missing header")
        header_result = dict(header)
        header_revision = _field(header, "revision")
        if header_revision is None:
            raise Etcd3gwProtocolError("etcd Range response header is missing revision")
        header_result["revision"] = int(header_revision)
        result["header"] = header_result
        return result

    @staticmethod
    def _encode_compare(item: Mapping[str, Any]) -> dict[str, Any]:
        target = str(item["target"]).upper()
        field_name = {
            "VERSION": "version",
            "CREATE": "create_revision",
            "MOD": "mod_revision",
            "VALUE": "value",
        }.get(target)
        if field_name is None:
            raise ValueError(f"unsupported etcd Compare target: {target}")
        expected = item[field_name]
        return {
            "key": _encode_bytes(item["key"]),
            "target": target,
            "result": str(item["result"]).upper(),
            field_name: _encode_bytes(expected) if target == "VALUE" else int(expected),
        }

    @staticmethod
    def _encode_operation(item: Mapping[str, Any]) -> dict[str, Any]:
        if "request_range" in item:
            request = item["request_range"]
            return {"request_range": {"key": _encode_bytes(request["key"])}}
        if "request_put" in item:
            request = item["request_put"]
            encoded: dict[str, Any] = {
                "key": _encode_bytes(request["key"]),
                "value": _encode_bytes(request["value"]),
            }
            if request.get("lease") not in (None, 0, "0", ""):
                encoded["lease"] = int(request["lease"])
            return {"request_put": encoded}
        if "request_delete_range" in item:
            request = item["request_delete_range"]
            return {"request_delete_range": {"key": _encode_bytes(request["key"])}}
        raise ValueError("unsupported etcd transaction operation")

    @staticmethod
    def _decode_txn_response(response: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(response)
        responses = _field(response, "responses")
        if responses is not None:
            if not isinstance(responses, list):
                raise Etcd3gwProtocolError("etcd Txn responses is not an array")
            decoded_responses: list[dict[str, Any]] = []
            for operation_response in responses:
                if not isinstance(operation_response, Mapping):
                    raise Etcd3gwProtocolError("etcd Txn operation response is malformed")
                current = dict(operation_response)
                range_response = _field(operation_response, "response_range", "responseRange")
                if range_response is not None:
                    if not isinstance(range_response, Mapping):
                        raise Etcd3gwProtocolError("etcd Txn Range response is malformed")
                    decoded_range = dict(range_response)
                    kvs = _field(range_response, "kvs")
                    if kvs is not None:
                        decoded_range["kvs"] = [_decode_kv(item) for item in kvs]
                    nested_header = _field(range_response, "header")
                    if isinstance(nested_header, Mapping):
                        decoded_header = dict(nested_header)
                        revision = _field(nested_header, "revision")
                        if revision is not None:
                            decoded_header["revision"] = int(revision)
                        decoded_range["header"] = decoded_header
                    current["response_range"] = decoded_range
                decoded_responses.append(current)
            result["responses"] = decoded_responses
        header = _field(response, "header")
        if isinstance(header, Mapping):
            decoded_header = dict(header)
            revision = _field(header, "revision")
            if revision is not None:
                decoded_header["revision"] = int(revision)
            result["header"] = decoded_header
        return result

    def txn(
        self,
        *,
        compare: Sequence[Mapping[str, Any]],
        success: Sequence[Mapping[str, Any]],
        failure: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        payload = {
            "compare": [self._encode_compare(item) for item in compare],
            "success": [self._encode_operation(item) for item in success],
            "failure": [self._encode_operation(item) for item in failure],
        }
        # Mutating transactions are sent exactly once. Transport loss is
        # translated by EtcdV3CoordinatorAuthorityStore to OUTCOME_UNKNOWN.
        response = self._post(
            "/kv/txn", payload, read_only=False, encode_as_json=False
        )
        return self._decode_txn_response(response)

    def lease_grant(self, ttl_seconds: int) -> Mapping[str, Any]:
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds < 1:
            raise ValueError("lease TTL must be a positive integer")
        response = self._post(
            "/lease/grant",
            {"TTL": ttl_seconds, "ID": 0},
            read_only=False,
        )
        lease_id = _field(response, "ID", "id")
        ttl = _field(response, "TTL", "ttl")
        if lease_id is None or ttl is None:
            raise Etcd3gwProtocolError("etcd LeaseGrant response is missing ID or TTL")
        return {"id": int(lease_id), "ttl": int(ttl)}

    def lease_keepalive(self, lease_id: int) -> Mapping[str, Any]:
        if not isinstance(lease_id, int) or isinstance(lease_id, bool) or lease_id < 1:
            raise ValueError("lease ID must be positive")
        response = self._post(
            "/lease/keepalive", {"ID": lease_id}, read_only=False
        )
        result = _field(response, "result")
        if not isinstance(result, Mapping):
            raise Etcd3gwProtocolError("etcd LeaseKeepAlive response is missing result")
        ttl = _field(result, "TTL", "ttl")
        response_id = _field(result, "ID", "id")
        if ttl is None:
            ttl = 0
        return {"id": lease_id if response_id is None else int(response_id), "ttl": int(ttl)}

    def lease_revoke(self, lease_id: int) -> Mapping[str, Any]:
        if not isinstance(lease_id, int) or isinstance(lease_id, bool) or lease_id < 1:
            raise ValueError("lease ID must be positive")
        response = self._post(
            "/kv/lease/revoke", {"ID": lease_id}, read_only=False
        )
        return {"id": lease_id, "response": dict(response)}

    def watch(
        self,
        key: bytes,
        *,
        start_revision: int = 0,
        progress_notify: bool = True,
        filters: Sequence[str] | None = None,
        prev_kv: bool = True,
        range_end: bytes | None = None,
        watch_id: int | None = None,
        fragment: bool | None = None,
    ) -> Iterator[Mapping[str, Any]]:
        """Open an HTTP server-streaming Watch and preserve every response.

        The stream is bound to the endpoint that accepted the request. A
        transport failure after stream establishment is propagated; callers
        must rebuild their snapshot with a linearizable Range and resume at
        R+1 rather than silently restarting at the old cursor.
        """
        if not isinstance(key, bytes) or not key:
            raise ValueError("Watch key must be non-empty bytes")
        if (
            not isinstance(start_revision, int)
            or isinstance(start_revision, bool)
            or start_revision < 0
        ):
            raise ValueError("Watch start_revision must be a non-negative integer")
        if range_end is not None and not isinstance(range_end, bytes):
            raise ValueError("Watch range_end must be bytes or None")
        if watch_id is not None and (
            not isinstance(watch_id, int)
            or isinstance(watch_id, bool)
            or watch_id < 0
        ):
            raise ValueError("Watch watch_id must be a non-negative integer or None")
        if filters is not None and any(
            item not in {"NOPUT", "NODELETE"} for item in filters
        ):
            raise ValueError("Watch filters may only contain NOPUT or NODELETE")

        create_request: dict[str, Any] = {
            "key": _encode_bytes(key),
            "progress_notify": bool(progress_notify),
            "prev_kv": bool(prev_kv),
        }
        if start_revision > 0:
            create_request["start_revision"] = start_revision
        if range_end is not None:
            create_request["range_end"] = _encode_bytes(range_end)
        if watch_id is not None:
            create_request["watch_id"] = watch_id
        if filters is not None:
            create_request["filters"] = list(filters)
        if fragment is not None:
            create_request["fragment"] = bool(fragment)

        payload = {"create_request": create_request}
        start = self._take_start_index()
        last_transport_error: Exception | None = None
        for offset in range(len(self._clients)):
            client = self._clients[(start + offset) % len(self._clients)]
            try:
                response = client.session.post(
                    client.get_url("/watch"),
                    json=payload,
                    stream=True,
                    timeout=(self.timeout, None),
                )
            except Exception as exc:
                translated = _transport_error(exc)
                if isinstance(translated, (TimeoutError, ConnectionError)):
                    last_transport_error = translated
                    continue
                raise translated from exc

            status = int(getattr(response, "status_code", 200))
            if status >= 400:
                detail = str(getattr(response, "text", ""))[:512]
                close = getattr(response, "close", None)
                if callable(close):
                    close()
                if status in {408, 504}:
                    last_transport_error = TimeoutError(
                        f"etcd Watch endpoint returned HTTP {status}"
                    )
                    continue
                if status == 503:
                    last_transport_error = ConnectionError(
                        f"etcd Watch endpoint returned HTTP {status}"
                    )
                    continue
                raise Etcd3gwProtocolError(
                    f"etcd Watch endpoint returned HTTP {status}: {detail}"
                )
            return _Etcd3gwWatchStream(response)

        if last_transport_error is not None:
            raise last_transport_error
        raise ConnectionError("no etcd endpoint accepted the Watch request")

    def members(self) -> list[Mapping[str, Any]]:
        response = self._post("/cluster/member/list", {}, read_only=True)
        members = _field(response, "members")
        if not isinstance(members, list):
            raise Etcd3gwProtocolError("etcd member-list response is missing members")
        return list(members)

    def status(self) -> Mapping[str, Any]:
        return self._post("/maintenance/status", {}, read_only=True)

    def close(self) -> None:
        for client in self._clients:
            session = getattr(client, "session", None)
            close = getattr(session, "close", None)
            if callable(close):
                close()


__all__ = [
    "Etcd3gwConfigurationError",
    "Etcd3gwProtocolError",
    "Etcd3gwV3Client",
]

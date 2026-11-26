#!/usr/bin/env python3
"""Read-only Nacos config inspection with redacted, value-free output.

Remote mode only issues GET /nacos/v1/cs/configs. Local mode can inspect the
repository samples without network access. Configuration bodies and credential
values are never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DEFAULT_SERVER_URL = "http://192.168.89.128:8848"
DEFAULT_NAMESPACE = "4833404f-4b82-462e-889a-3c508160c6b4"
DEFAULT_GROUP = "DEFAULT_GROUP"
DEFAULT_DATA_IDS = ("data-source.yaml", "key-config.yaml", "third-services.yaml")
MAX_CONFIG_BYTES = 2 * 1024 * 1024
SAFE_DATA_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
ENV_PLACEHOLDER_RE = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*(?::[^}]*)?\}")
PLACEHOLDER_FULL_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}$")
KEY_VALUE_RE = re.compile(r"^\s*(?:-\s*)?[\"']?([A-Za-z0-9_.-]+)[\"']?\s*:\s*(.*?)\s*$")
URI_USERINFO_RE = re.compile(r"\b(?:mongodb(?:\+srv)?|mysql|postgres(?:ql)?|redis|rediss|amqp|amqps|https?)://([^\s/@]+)@", re.IGNORECASE)
URI_QUERY_SECRET_RE = re.compile(
    r"[?&](?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|token)=([^&#\s]*)",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")


class FetchError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _strip_yaml_comment(line: str) -> str:
    result: List[str] = []
    quote: Optional[str] = None
    escaped = False
    for index, char in enumerate(line):
        if quote == '"' and escaped:
            result.append(char)
            escaped = False
            continue
        if quote == '"' and char == "\\":
            result.append(char)
            escaped = True
            continue
        if quote:
            result.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            result.append(char)
            continue
        if char == "#" and (index == 0 or line[index - 1].isspace()):
            break
        result.append(char)
    return "".join(result)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _placeholder_has_literal_default(value: str) -> bool:
    for match in ENV_PLACEHOLDER_RE.finditer(value):
        expression = match.group(0)
        parsed = PLACEHOLDER_FULL_RE.fullmatch(expression)
        if parsed and parsed.group(2) not in (None, ""):
            return True
    return False


def _safe_placeholder(value: str) -> bool:
    match = PLACEHOLDER_FULL_RE.fullmatch(value)
    return bool(match and match.group(2) in (None, ""))


def _is_sensitive_key(key: str) -> bool:
    compact = re.sub(r"[^a-z0-9]", "", key.rsplit(".", 1)[-1].casefold())
    if compact == "pwd":
        return True
    return any(
        marker in compact
        for marker in ("password", "passwd", "secret", "apikey", "accesskey", "privatekey", "credential")
    )


def _userinfo_is_safe(userinfo: str) -> bool:
    # A URI may contain placeholders for both username and password. Separators
    # alone are not literal credential material; any remaining text is suspect.
    remainder = ENV_PLACEHOLDER_RE.sub("", userinfo)
    return not remainder.strip(":")


def analyze_content(data_id: str, content: bytes) -> Dict[str, object]:
    text = content.decode("utf-8-sig", errors="replace")
    clean_text = "\n".join(_strip_yaml_comment(line) for line in text.splitlines())
    has_placeholder = bool(ENV_PLACEHOLDER_RE.search(clean_text))
    suspected = False

    if PRIVATE_KEY_RE.search(clean_text):
        suspected = True

    for line in clean_text.splitlines():
        match = KEY_VALUE_RE.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        value = _unquote(raw_value.strip())
        if _is_sensitive_key(key) and value:
            if value.casefold() in {"null", "~"}:
                continue
            if re.fullmatch(r"[|>][+-]?", value):
                suspected = True
                continue
            if not _safe_placeholder(value) or _placeholder_has_literal_default(value):
                suspected = True

    for match in URI_USERINFO_RE.finditer(clean_text):
        if not _userinfo_is_safe(match.group(1)):
            suspected = True
    for match in URI_QUERY_SECRET_RE.finditer(clean_text):
        value = _unquote(match.group(1).strip())
        if value and (not _safe_placeholder(value) or _placeholder_has_literal_default(value)):
            suspected = True

    return {
        "data_id": data_id,
        "sha256": hashlib.sha256(content).hexdigest(),
        "plaintext_credential_suspected": suspected,
        "env_placeholder_present": has_placeholder,
    }


def _read_local(data_id: str, directory: Path) -> bytes:
    try:
        base = directory.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError):
        raise FetchError("local_directory_not_found")
    except OSError:
        raise FetchError("local_directory_not_readable")
    candidate = (base / data_id).resolve()
    if candidate.parent != base or not candidate.is_file():
        raise FetchError("local_file_not_found")
    try:
        with candidate.open("rb") as handle:
            content = handle.read(MAX_CONFIG_BYTES + 1)
    except PermissionError:
        raise FetchError("local_file_not_readable")
    except OSError:
        raise FetchError("local_file_not_readable")
    if len(content) > MAX_CONFIG_BYTES:
        raise FetchError("config_too_large")
    return content


def _validate_server_url(server_url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(server_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise FetchError("invalid_server_url")
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise FetchError("invalid_server_url")
    if port is not None and not 1 <= port <= 65535:
        raise FetchError("invalid_server_url")
    return server_url.rstrip("/")


def _fetch_nacos(server_url: str, namespace: str, group: str, data_id: str, timeout: int) -> bytes:
    base = _validate_server_url(server_url)
    base_path = urllib.parse.urlsplit(base).path.rstrip("/")
    endpoint_path = base_path + ("/v1/cs/configs" if base_path.endswith("/nacos") else "/nacos/v1/cs/configs")
    endpoint = urllib.parse.urlunsplit((urllib.parse.urlsplit(base).scheme, urllib.parse.urlsplit(base).netloc, endpoint_path, "", ""))
    params = {"dataId": data_id, "group": group, "tenant": namespace}
    access_token = os.environ.get("NACOS_ACCESS_TOKEN", "")
    if access_token:
        params["accessToken"] = access_token
    request = urllib.request.Request(
        endpoint + "?" + urllib.parse.urlencode(params),
        method="GET",
        headers={"Accept": "text/plain, */*", "User-Agent": "aiwms-nacos-readonly-inspector/1.0"},
    )
    # Do not follow redirects (which could forward credentials) or send the
    # access token through an implicitly configured proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if not 200 <= status < 300:
                raise FetchError("http_status:" + str(status))
            content = response.read(MAX_CONFIG_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise FetchError("http_status:" + str(error.code))
    except (urllib.error.URLError, TimeoutError, OSError):
        raise FetchError("network_error")
    if len(content) > MAX_CONFIG_BYTES:
        raise FetchError("config_too_large")
    return content


def _error_result(data_id: str, code: str) -> Dict[str, object]:
    return {
        "data_id": data_id,
        "sha256": None,
        "plaintext_credential_suspected": None,
        "env_placeholder_present": None,
        "status": "error",
        "error": code,
    }


def _emit(results: Sequence[Dict[str, object]], as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "results": list(results),
                    "summary": {
                        "ok": sum(1 for item in results if item.get("status") != "error"),
                        "errors": sum(1 for item in results if item.get("status") == "error"),
                        "suspected": sum(1 for item in results if item.get("plaintext_credential_suspected") is True),
                    },
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return
    for item in results:
        data_id = item["data_id"]
        if item.get("status") == "error":
            print(f"data_id={data_id} status=error error={item['error']} (content hidden)")
            continue
        print(
            f"data_id={data_id} sha256={item['sha256']} "
            f"plaintext_credential_suspected={str(item['plaintext_credential_suspected']).lower()} "
            f"env_placeholder_present={str(item['env_placeholder_present']).lower()}"
        )
    errors = sum(1 for item in results if item.get("status") == "error")
    suspected = sum(1 for item in results if item.get("plaintext_credential_suspected") is True)
    print(f"summary: ok={len(results) - errors} errors={errors} suspected={suspected} (values hidden)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Nacos config hashes and credential indicators without printing config bodies.")
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL, help="Nacos base URL; default is the documented dev endpoint.")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE, help="Nacos namespace/tenant ID.")
    parser.add_argument("--group", default=DEFAULT_GROUP, help="Nacos group (default: DEFAULT_GROUP).")
    parser.add_argument("--data-id", action="append", dest="data_ids", help="dataId to inspect; repeat for multiple IDs.")
    parser.add_argument("--local-dir", type=Path, help="Inspect local files instead of making network requests.")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds (default: 10).")
    parser.add_argument("--json", action="store_true", help="Emit redacted JSON.")
    args = parser.parse_args(argv)

    data_ids = args.data_ids or list(DEFAULT_DATA_IDS)
    if not args.namespace or not args.group or not 1 <= args.timeout <= 60:
        _emit([_error_result("request", "invalid_request")], args.json)
        return 2
    for data_id in data_ids:
        if not SAFE_DATA_ID_RE.fullmatch(data_id) or data_id in {".", ".."}:
            _emit([_error_result("request", "invalid_data_id")], args.json)
            return 2
    if args.local_dir is None:
        try:
            _validate_server_url(args.server_url)
        except FetchError as error:
            _emit([_error_result("request", error.code)], args.json)
            return 2

    results: List[Dict[str, object]] = []
    for data_id in data_ids:
        try:
            content = _read_local(data_id, args.local_dir) if args.local_dir else _fetch_nacos(
                args.server_url, args.namespace, args.group, data_id, args.timeout
            )
            result = analyze_content(data_id, content)
            result["status"] = "ok"
            results.append(result)
        except FetchError as error:
            results.append(_error_result(data_id, error.code))

    _emit(results, args.json)
    if any(item.get("status") == "error" for item in results):
        return 2
    if any(item.get("plaintext_credential_suspected") is True for item in results):
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except Exception:
        print("[ERROR] internal inspection failure (details and content hidden)", file=sys.stderr)
        sys.exit(2)

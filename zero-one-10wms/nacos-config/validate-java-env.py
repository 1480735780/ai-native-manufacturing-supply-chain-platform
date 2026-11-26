#!/usr/bin/env python3
"""Validate Java service environment variables without printing their values.

This script only inspects the current process environment or a local env file.
It does not generate credentials, contact Nacos, or connect to any service.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Rule:
    kind: str
    required: bool = True
    min_length: int = 0


RULES: Dict[str, Rule] = {
    "WMS_DB_HOST": Rule("host"),
    "WMS_DB_PORT": Rule("port"),
    "WMS_DB_USERNAME": Rule("username"),
    "WMS_DB_PASSWORD": Rule("secret", min_length=12),
    "WMS_REDIS_HOST": Rule("host"),
    "WMS_REDIS_PORT": Rule("port"),
    "WMS_REDIS_PASSWORD": Rule("secret", min_length=12),
    "WMS_MONGO_HOST": Rule("host"),
    "WMS_MONGO_PORT": Rule("port"),
    "WMS_MONGO_USERNAME": Rule("username"),
    "WMS_MONGO_PASSWORD": Rule("secret", min_length=12),
    "WMS_OAUTH2_MGR_ID": Rule("id"),
    "WMS_OAUTH2_MGR_PASSWORD": Rule("secret", min_length=12),
    "AGENT_SERVICE_API_KEY": Rule("secret", min_length=12),
    "AGENT_SERVICE_API_KEY_ID": Rule("id"),
    "AGENT_SERVICE_USERNAME": Rule("username"),
    "AGENT_SERVICE_PASSWORD": Rule("secret", min_length=12),
    "AGENT_SERVICE_WAREHOUSES": Rule("warehouses"),
    "AGENT_SERVICE_TOKEN_TTL_SECONDS": Rule("ttl"),
    "AGENT_SERVICE_TOKEN_USE": Rule("token_use"),
    "AGENT_SERVICE_TOKEN_ISSUER": Rule("issuer"),
    "AGENT_SERVICE_IP_WHITELIST": Rule("ip_list"),
    "FASTDFS_HTTP_SECRET_KEY": Rule("secret", min_length=12),
    "AGENT_SERVICE_API_KEY_PREVIOUS": Rule("secret", required=False, min_length=12),
    "AGENT_SERVICE_API_KEY_PREVIOUS_ID": Rule("id", required=False),
    "AGENT_SERVICE_PRIVATE_KEY_PATH": Rule("path", required=False),
    "AGENT_SERVICE_JKS_PATH": Rule("path", required=False),
    "AGENT_SERVICE_JKS_PASSWORD": Rule("secret", required=False, min_length=12),
    "AGENT_SERVICE_KEY_ALIAS": Rule("alias", required=False),
    "AGENT_SERVICE_KEY_PASSWORD": Rule("secret", required=False, min_length=12),
}

JKS_VARIABLES = (
    "AGENT_SERVICE_JKS_PATH",
    "AGENT_SERVICE_JKS_PASSWORD",
    "AGENT_SERVICE_KEY_ALIAS",
    "AGENT_SERVICE_KEY_PASSWORD",
)
SIGNING_GROUP = "AGENT_SERVICE_JKS_PATH|AGENT_SERVICE_PRIVATE_KEY_PATH"

PLACEHOLDER_RE = re.compile(
    r"<[^>]+>|\$\{[^}]+\}|\{\{[^}]+\}\}|REPLACE[_-]?ME|CHANGEME|TODO",
    re.IGNORECASE,
)
WEAK_SECRETS = {
    "password",
    "password123",
    "passwd",
    "123456",
    "1234567",
    "12345678",
    "123456789",
    "1234567890",
    "111111",
    "000000",
    "qwerty",
    "qwerty123",
    "abc123",
    "changeme",
    "change_me",
    "secret",
    "default",
    "test",
    "demo",
}
WEAK_HOSTS = {
    "127.0.0.1",
    "::1",
    "localhost",
    "0.0.0.0",
    "::",
    "192.168.89.128",  # documented dev endpoint, not a prod target
}
WEAK_IDS = {"admin", "root", "k1", "k2", "default", "test", "demo"}
WEAK_USERNAMES = {"admin", "root", "sa", "postgres"}
WEAK_WAREHOUSES = {"w01", "warehouse01", "default", "test", "demo"}
ASSIGNMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
ISSUER_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


class EnvFileError(Exception):
    def __init__(self, code: str, line: Optional[int] = None):
        super().__init__(code)
        self.code = code
        self.line = line


def _parse_quoted_value(raw: str, quote: str, line: int) -> str:
    chars: List[str] = []
    escaped = False
    for index in range(1, len(raw)):
        char = raw[index]
        if quote == '"' and escaped:
            chars.append(char)
            escaped = False
            continue
        if quote == '"' and char == "\\":
            chars.append(char)
            escaped = True
            continue
        if char == quote:
            trailing = raw[index + 1 :].strip()
            if trailing and not trailing.startswith("#"):
                raise EnvFileError("invalid_quoted_value", line)
            return "".join(chars)
        chars.append(char)
    raise EnvFileError("unterminated_quote", line)


def _parse_value(raw: str, line: int) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] in ("'", '"'):
        return _parse_quoted_value(raw, raw[0], line)
    return re.sub(r"\s+#.*$", "", raw).rstrip()


def load_env_file(path: Path) -> Dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise EnvFileError("file_not_found")
    except PermissionError:
        raise EnvFileError("file_not_readable")
    except UnicodeDecodeError:
        raise EnvFileError("invalid_encoding")
    except OSError:
        raise EnvFileError("file_not_readable")

    values: Dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        match = ASSIGNMENT_RE.match(stripped)
        if not match:
            raise EnvFileError("invalid_assignment", line_number)
        name, raw_value = match.groups()
        if name in values:
            raise EnvFileError("duplicate_variable:" + name, line_number)
        value = _parse_value(raw_value, line_number)
        if "\x00" in value:
            raise EnvFileError("invalid_character:" + name, line_number)
        values[name] = value
    return values


def _is_weak_secret(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in WEAK_SECRETS:
        return True
    if re.fullmatch(r"(.)\1{5,}", normalized):
        return True
    if normalized.isdigit() and len(set(normalized)) <= 2:
        return True
    if any(sequence in normalized for sequence in ("1234567890", "0123456789", "9876543210", "0987654321")):
        return True
    if re.fullmatch(r"(?:password|passwd|admin|root|wms)[@_.-]?\d{1,6}[!@#$]?", normalized):
        return True
    if re.fullmatch(r"abcdefghijklmnopqrstuvwxyz|qwertyuiop", normalized):
        return True
    if len(normalized) >= 6:
        for size in range(1, len(normalized) // 2 + 1):
            if len(normalized) % size == 0 and normalized == normalized[:size] * (len(normalized) // size):
                return True
    return False


def _validate_value(name: str, value: Optional[str], rule: Rule) -> List[Tuple[str, str]]:
    if value is None:
        return [(name, "missing")] if rule.required else []
    if value == "" or not value.strip():
        return [(name, "empty")] if rule.required else []
    if value != value.strip():
        return [(name, "surrounding_whitespace")]
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return [(name, "invalid_character")]
    if PLACEHOLDER_RE.search(value):
        return [(name, "placeholder_value")]

    stripped = value.strip()
    normalized = stripped.casefold()
    if rule.kind == "secret":
        if len(stripped) < rule.min_length:
            return [(name, "weak_or_short")]
        if _is_weak_secret(stripped):
            return [(name, "weak_default")]
    elif rule.kind == "host":
        if normalized in WEAK_HOSTS:
            return [(name, "weak_default")]
        if any(char in stripped for char in "/?#@"):
            return [(name, "invalid_host")]
    elif rule.kind == "port":
        if not stripped.isdigit() or not 1 <= int(stripped) <= 65535:
            return [(name, "invalid_port")]
    elif rule.kind == "username":
        if normalized in WEAK_USERNAMES:
            return [(name, "weak_default")]
    elif rule.kind == "id":
        if normalized in WEAK_IDS:
            return [(name, "weak_default")]
    elif rule.kind == "path":
        if "://" in stripped:
            return [(name, "invalid_path")]
    elif rule.kind == "warehouses":
        parts = [part.strip() for part in stripped.split(",")]
        if not parts or any(not part for part in parts):
            return [(name, "invalid_list")]
        if any(part.casefold() in WEAK_WAREHOUSES for part in parts):
            return [(name, "weak_default")]
    elif rule.kind == "ttl":
        if not stripped.isdigit() or not 60 <= int(stripped) <= 86400:
            return [(name, "invalid_ttl")]
    elif rule.kind == "token_use":
        if stripped != "agent_service":
            return [(name, "invalid_token_use")]
    elif rule.kind == "issuer":
        if not ISSUER_RE.fullmatch(stripped):
            return [(name, "invalid_issuer")]
    elif rule.kind == "ip_list":
        parts = [part.strip() for part in stripped.split(",")]
        if not parts or any(not part for part in parts):
            return [(name, "invalid_list")]
        try:
            addresses = [ipaddress.ip_address(part) for part in parts]
        except ValueError:
            return [(name, "invalid_ip")]
        if any(address.is_unspecified for address in addresses):
            return [(name, "weak_default")]
        if all(address.is_loopback for address in addresses):
            return [(name, "weak_default")]
    elif rule.kind == "alias":
        if not stripped or any(char.isspace() for char in stripped):
            return [(name, "invalid_alias")]
    return []


def validate_environment(values: Mapping[str, str], signing: str = "any") -> List[Tuple[str, str]]:
    rules = dict(RULES)
    if signing == "jks":
        for name in JKS_VARIABLES:
            rules[name] = Rule(rules[name].kind, required=True, min_length=rules[name].min_length)
    elif signing == "pem":
        rules["AGENT_SERVICE_PRIVATE_KEY_PATH"] = Rule("path", required=True)

    issues: List[Tuple[str, str]] = []
    for name, rule in rules.items():
        issues.extend(_validate_value(name, values.get(name), rule))

    if signing == "any":
        has_pem = bool((values.get("AGENT_SERVICE_PRIVATE_KEY_PATH") or "").strip())
        has_jks = bool((values.get("AGENT_SERVICE_JKS_PATH") or "").strip())
        if not has_pem and not has_jks:
            issues.append((SIGNING_GROUP, "one_required"))
        if has_jks:
            for name in JKS_VARIABLES:
                issues.extend(_validate_value(name, values.get(name), Rule(rules[name].kind, required=True, min_length=rules[name].min_length)))

    previous = (values.get("AGENT_SERVICE_API_KEY_PREVIOUS") or "").strip()
    previous_id = (values.get("AGENT_SERVICE_API_KEY_PREVIOUS_ID") or "").strip()
    if bool(previous) != bool(previous_id):
        missing_name = "AGENT_SERVICE_API_KEY_PREVIOUS_ID" if previous else "AGENT_SERVICE_API_KEY_PREVIOUS"
        issues.append((missing_name, "missing_pair"))
    if previous and previous_id:
        if previous == (values.get("AGENT_SERVICE_API_KEY") or "").strip():
            issues.append(("AGENT_SERVICE_API_KEY_PREVIOUS", "must_differ_from_current"))
        if previous_id.casefold() == (values.get("AGENT_SERVICE_API_KEY_ID") or "").strip().casefold():
            issues.append(("AGENT_SERVICE_API_KEY_PREVIOUS_ID", "must_differ_from_current"))

    # Keep output deterministic and avoid duplicate diagnostics.
    return list(dict.fromkeys(issues))


def _emit(issues: Iterable[Tuple[str, str]], as_json: bool, passed: bool, checked: int) -> None:
    issue_list = list(issues)
    if as_json:
        payload = {
            "status": "pass" if passed else "fail",
            "checked_variables": checked,
            "issues": [{"variable": name, "code": code} for name, code in issue_list],
        }
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return
    if passed:
        print(f"[PASS] Java environment validated: {checked} variables (values hidden)")
        return
    for name, code in issue_list:
        print(f"[ERROR] {name}: {code} (value hidden)")
    print(f"[FAIL] Java environment validation: {len(issue_list)} issue(s); no values printed")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Java service environment variables without printing values.")
    parser.add_argument("--env-file", type=Path, help="Local env file; process environment overrides file values.")
    parser.add_argument("--signing", choices=("any", "jks", "pem"), default="any", help="Required service-token signing mode (default: any).")
    parser.add_argument("--json", action="store_true", help="Emit only redacted JSON diagnostics.")
    args = parser.parse_args(argv)

    try:
        file_values = load_env_file(args.env_file) if args.env_file else {}
    except EnvFileError as error:
        location = f"line={error.line}" if error.line is not None else "file"
        _emit([(f"env_file:{location}", error.code)], args.json, False, 0)
        return 2

    values = dict(file_values)
    values.update(os.environ)
    issues = validate_environment(values, args.signing)
    _emit(issues, args.json, not issues, len(RULES))
    return 0 if not issues else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except Exception:
        print("[ERROR] internal validation failure (details hidden)", file=sys.stderr)
        sys.exit(2)

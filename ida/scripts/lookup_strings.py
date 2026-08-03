#!/usr/bin/env python3
"""
Resolve IL2CPP StringLiteral_N entries from Il2CppDumper's stringliteral.json.

The script intentionally has no project-specific default path. Pass --json-path,
or set IL2CPP_STRINGLITERAL_JSON / LOOKUP_STRINGS_JSON_PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


STRING_LITERAL_RE = re.compile(r"\bStringLiteral_(\d+)\b")
ENV_PATHS = ("IL2CPP_STRINGLITERAL_JSON", "LOOKUP_STRINGS_JSON_PATH")


class LookupErrorWithMessage(Exception):
    pass


def parse_int(text: str) -> int:
    value = text.strip()
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}") from exc


def normalize_rva(value: int) -> str:
    return f"0x{value:X}"


def resolve_json_path(arg_path: str | None) -> Path:
    if arg_path:
        return Path(arg_path)

    for env_name in ENV_PATHS:
        env_value = os.environ.get(env_name)
        if env_value:
            return Path(env_value)

    names = " or ".join(ENV_PATHS)
    raise LookupErrorWithMessage(
        f"stringliteral.json path is required. Pass --json-path or set {names}."
    )


def load_entries(json_path: Path) -> list[dict[str, Any]]:
    if not json_path.exists():
        raise LookupErrorWithMessage(f"stringliteral.json not found: {json_path}")

    try:
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise LookupErrorWithMessage(f"invalid JSON in {json_path}: {exc}") from exc

    if not isinstance(data, list):
        raise LookupErrorWithMessage("stringliteral.json must contain a JSON array")

    entries: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise LookupErrorWithMessage(f"entry {index} is not an object")
        if "address" not in item or "value" not in item:
            raise LookupErrorWithMessage(f"entry {index} lacks address or value")
        entries.append(item)
    return entries


def build_address_index(entries: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for item in entries:
        address = item["address"]
        if not isinstance(address, str):
            continue
        try:
            rva = int(address, 0)
        except ValueError:
            continue
        index[rva] = item
    return index


def label_to_id(text: str) -> int | None:
    match = STRING_LITERAL_RE.search(text)
    if match:
        return int(match.group(1))
    if text.strip().isdigit():
        return int(text.strip())
    return None


def extract_label_ids(text: str) -> list[int]:
    return sorted({int(match) for match in STRING_LITERAL_RE.findall(text)})


def lookup_by_label(entries: list[dict[str, Any]], label_id: int) -> tuple[str, str]:
    index = label_id - 1
    if index < 0 or index >= len(entries):
        raise LookupErrorWithMessage(
            f"StringLiteral_{label_id} is out of range; max is StringLiteral_{len(entries)}"
        )
    item = entries[index]
    return str(item["address"]), str(item["value"])


def lookup_by_rva(address_index: dict[int, dict[str, Any]], rva: int) -> tuple[str, str]:
    item = address_index.get(rva)
    if item is None:
        raise LookupErrorWithMessage(f"RVA {normalize_rva(rva)} was not found")
    return str(item["address"]), str(item["value"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve IL2CPP StringLiteral_N labels or RVA/VA values.",
    )
    parser.add_argument(
        "items",
        nargs="*",
        help="StringLiteral_N labels or plain numeric label ids.",
    )
    parser.add_argument(
        "--json-path",
        help="Path to Il2CppDumper stringliteral.json.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read text from stdin and extract all StringLiteral_N labels.",
    )
    parser.add_argument(
        "--from-file",
        "--from-decompile",
        metavar="PATH",
        help="Read a text/decompile file and extract all StringLiteral_N labels.",
    )
    parser.add_argument(
        "--rva",
        nargs="+",
        type=parse_int,
        help="Resolve one or more RVA values, e.g. --rva 0x4222200.",
    )
    parser.add_argument(
        "--va",
        nargs="+",
        type=parse_int,
        help="Resolve one or more VA values. Requires --base.",
    )
    parser.add_argument(
        "--base",
        type=parse_int,
        help="Image base used to convert VA to RVA, e.g. --base 0x180000000.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only resolved string values.",
    )
    return parser


def collect_label_ids(args: argparse.Namespace) -> list[int]:
    ids: list[int] = []

    if args.stdin:
        ids.extend(extract_label_ids(sys.stdin.read()))

    if args.from_file:
        text = Path(args.from_file).read_text(encoding="utf-8")
        ids.extend(extract_label_ids(text))

    for item in args.items:
        label_id = label_to_id(item)
        if label_id is None:
            raise LookupErrorWithMessage(f"not a StringLiteral label/id: {item!r}")
        ids.append(label_id)

    return sorted(set(ids))


def print_result(kind: str, key: str, address: str, value: str, quiet: bool) -> None:
    if quiet:
        print(value)
    else:
        print(f"{kind:<13} {key:<18} {address:<12} => {value!r}")


def run(args: argparse.Namespace) -> int:
    json_path = resolve_json_path(args.json_path)
    entries = load_entries(json_path)
    address_index = build_address_index(entries)

    label_ids = collect_label_ids(args)
    rvas = list(args.rva or [])

    if args.va:
        if args.base is None:
            raise LookupErrorWithMessage("--va requires --base")
        rvas.extend(va - args.base for va in args.va)

    if not label_ids and not rvas:
        raise LookupErrorWithMessage("provide labels, --stdin, --from-file, --rva, or --va")

    for label_id in label_ids:
        address, value = lookup_by_label(entries, label_id)
        print_result("StringLiteral", f"StringLiteral_{label_id}", address, value, args.quiet)

    for rva in rvas:
        address, value = lookup_by_rva(address_index, rva)
        print_result("RVA", normalize_rva(rva), address, value, args.quiet)

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except LookupErrorWithMessage as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

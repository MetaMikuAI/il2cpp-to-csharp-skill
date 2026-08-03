#!/usr/bin/env python3
"""Query Il2CppDumper ScriptMethod records without enumerating Ghidra symbols."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def parse_int(text: str) -> int:
    try:
        return int(text.strip(), 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}") from exc


def resolve_path(value: str | None) -> Path:
    if value:
        return Path(value)
    configured = os.environ.get("IL2CPP_SCRIPT_JSON")
    if configured:
        return Path(configured)
    raise SystemExit("error: pass --json-path or set IL2CPP_SCRIPT_JSON")


def address_of(record: dict[str, Any]) -> int | None:
    value = record.get("Address")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query method names and RVAs in Il2CppDumper script.json.",
    )
    parser.add_argument("--json-path", help="Path to Il2CppDumper script.json")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--name", help="Exact case-sensitive ScriptMethod name")
    selector.add_argument("--contains", help="Case-insensitive method-name fragment")
    selector.add_argument("--rva", type=parse_int, help="Exact ScriptMethod RVA")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows to print")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    json_path = resolve_path(args.json_path)
    if not json_path.is_file():
        raise SystemExit(f"error: script.json not found: {json_path}")
    if args.limit < 1:
        raise SystemExit("error: --limit must be positive")

    with json_path.open("r", encoding="utf-8") as handle:
        root = json.load(handle)
    methods = root.get("ScriptMethod", [])
    if not isinstance(methods, list):
        raise SystemExit("error: ScriptMethod is not an array")

    fragment = args.contains.casefold() if args.contains is not None else None
    matches: list[dict[str, Any]] = []
    for record in methods:
        if not isinstance(record, dict):
            continue
        name = str(record.get("Name", ""))
        address = address_of(record)
        if args.name is not None and name != args.name:
            continue
        if fragment is not None and fragment not in name.casefold():
            continue
        if args.rva is not None and address != args.rva:
            continue
        matches.append(record)

    for record in matches[: args.limit]:
        address = address_of(record)
        rva = "<invalid>" if address is None else f"0x{address:X}"
        name = str(record.get("Name", ""))
        signature = str(record.get("Signature", "")).strip()
        print(f"{rva:<18} {name}")
        if signature:
            print(f"{'':18} {signature}")

    if len(matches) > args.limit:
        print(f"<truncated: {len(matches)} matches; limit={args.limit}>", file=sys.stderr)
    if not matches:
        print("no matches", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

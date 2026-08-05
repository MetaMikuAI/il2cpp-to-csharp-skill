#!/usr/bin/env python3
"""
Compute IL2CPP object/Fields offsets from noisy decompiler pointer expressions.

This script only performs offset arithmetic. Resolve the final field name with
the decompiler's struct/type inspection or the dumped C# [FieldOffset] data.
"""

from __future__ import annotations

import argparse


BUILTIN_MEMBER_OFFSETS = {
    "klass": 0x0,
    "monitor": 0x8,
    "fields": 0x10,
}


def parse_int(text: str) -> int:
    try:
        return int(text.strip(), 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {text!r}") from exc


def hex_int(value: int) -> str:
    return f"0x{value:X}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute IL2CPP object and Fields offsets from decompiler pointer noise.",
    )
    parser.add_argument(
        "--object-size",
        type=parse_int,
        help="Size of the pointer element type, e.g. 0x10 for Il2CppObject or 0x60 for SchedulerNode_o.",
    )
    parser.add_argument(
        "--index",
        type=parse_int,
        default=0,
        help="Array index from pseudo-C, e.g. 40 in Instance[40].monitor.",
    )
    parser.add_argument(
        "--member",
        choices=sorted(BUILTIN_MEMBER_OFFSETS),
        help="Built-in object member offset: klass=0, monitor=8, fields=0x10.",
    )
    parser.add_argument(
        "--member-offset",
        type=parse_int,
        help="Explicit member offset inside the pointer element type.",
    )
    parser.add_argument(
        "--byte-offset",
        type=parse_int,
        default=0,
        help="Extra byte offset from BYTE4/BYTE1/etc. BYTE4 means --byte-offset 4.",
    )
    parser.add_argument(
        "--object-offset",
        type=parse_int,
        help="Known object-relative offset from assembly, e.g. 0x28c from [rax+28Ch].",
    )
    parser.add_argument(
        "--object-header",
        type=parse_int,
        default=0x10,
        help="IL2CPP object header size before fields. Default: 0x10.",
    )
    return parser


def resolve_member_offset(args: argparse.Namespace) -> int:
    if args.member_offset is not None:
        return args.member_offset
    if args.member is not None:
        return BUILTIN_MEMBER_OFFSETS[args.member]
    return 0


def compute_object_offset(args: argparse.Namespace) -> int:
    if args.object_offset is not None:
        return args.object_offset
    if args.object_size is None:
        raise SystemExit("error: --object-size is required unless --object-offset is provided")

    return args.index * args.object_size + resolve_member_offset(args) + args.byte_offset


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    object_offset = compute_object_offset(args)
    fields_offset = object_offset - args.object_header

    print(f"object_offset = {hex_int(object_offset)}")
    print(f"fields_offset = {hex_int(fields_offset)}")
    if fields_offset < 0:
        print("warning: fields_offset is negative; this points into the object header")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run bounded Ghidra queries without returning headless noise to the model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_LIST_LIMIT = 50
DEFAULT_INLINE_LINES = 120
DEFAULT_READ_LINES = 120
HARD_READ_LIMIT = 240
HARD_BATCH_LIMIT = 32
QUERY_BEGIN = "=== GHIDRA_QUERY_BEGIN ==="
QUERY_END = "=== GHIDRA_QUERY_END ==="
SCRIPT_PREFIX = "GhidraQuery.java>"
STRING_RE = re.compile(r"\bStringLiteral_(\d+)\b")
CONTROL_RE = re.compile(r"^(else\s+if|if|switch|case|default|for|while|do)\b")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture Ghidra output as artifacts and emit a compact result."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Run one bounded Ghidra query.")
    query.add_argument("action", choices=(
        "info", "decompile", "callees", "callers", "xrefs", "disassemble"
    ))
    query.add_argument("selector", help="va:0x..., rva:0x..., or name:Exact.Symbol")
    query.add_argument("--project-location", type=Path, required=True)
    query.add_argument("--project-name", required=True)
    query.add_argument("--program", required=True)
    query.add_argument("--launcher", type=Path)
    query.add_argument("--script-path", type=Path, default=Path(__file__).resolve().parent)
    query.add_argument("--artifacts", type=Path)
    query.add_argument("--timeout", type=positive_int, default=120)
    query.add_argument("--limit", type=positive_int, default=DEFAULT_LIST_LIMIT)
    query.add_argument("--inline-max-lines", type=nonnegative_int,
                       default=DEFAULT_INLINE_LINES)
    query.add_argument("--no-inline", action="store_true")
    query.add_argument("--preview-items", type=positive_int, default=20)
    query.add_argument("--process-timeout", type=positive_int, default=600)
    query.add_argument("--no-cache", action="store_true",
                       help="Bypass the content-addressed successful-query cache.")

    batch = subparsers.add_parser(
        "batch", help="Run bounded queries for several exact selectors in one Ghidra launch."
    )
    batch.add_argument("action", choices=(
        "info", "decompile", "callees", "callers", "xrefs", "disassemble"
    ))
    batch.add_argument("selectors", nargs="+",
                       help="Exact va:, rva:, or name: selectors.")
    batch.add_argument("--project-location", type=Path, required=True)
    batch.add_argument("--project-name", required=True)
    batch.add_argument("--program", required=True)
    batch.add_argument("--launcher", type=Path)
    batch.add_argument("--script-path", type=Path, default=Path(__file__).resolve().parent)
    batch.add_argument("--artifacts", type=Path)
    batch.add_argument("--timeout", type=positive_int, default=120)
    batch.add_argument("--limit", type=positive_int, default=DEFAULT_LIST_LIMIT)
    batch.add_argument("--preview-items", type=positive_int, default=10)
    batch.add_argument("--process-timeout", type=positive_int, default=1800)
    batch.add_argument("--max-items", type=positive_int, default=16)
    batch.add_argument("--no-cache", action="store_true")

    read = subparsers.add_parser("read", help="Read a bounded slice of a saved artifact.")
    read.add_argument("artifact", type=Path, nargs="?")
    read.add_argument("--index", type=Path,
                      help="Evidence index used to resolve the artifact or a semantic block.")
    selection = read.add_mutually_exclusive_group()
    selection.add_argument("--lines", help="One-based inclusive range, for example 1:120.")
    selection.add_argument("--around", help="Show one bounded window around a literal substring.")
    selection.add_argument("--block", help="Semantic block ID from index.json, for example B0002.")
    read.add_argument("--context", type=nonnegative_int, default=20)
    read.add_argument("--block-context", type=nonnegative_int, default=2)
    read.add_argument("--occurrence", type=positive_int, default=1)
    read.add_argument("--max-lines", type=positive_int, default=DEFAULT_READ_LINES)
    read.add_argument("--max-line-chars", type=positive_int, default=4000)
    return parser


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return parsed


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def discover_launcher(explicit: Path | None) -> Path:
    if explicit is not None:
        launcher = explicit.expanduser().resolve()
        if launcher.is_file() and os.access(launcher, os.X_OK):
            return launcher
        raise RuntimeError(f"analyzeHeadless is not executable: {launcher}")

    on_path = shutil.which("analyzeHeadless")
    if on_path:
        return Path(on_path).resolve()

    brew = shutil.which("brew")
    if brew:
        result = subprocess.run(
            [brew, "--prefix", "ghidra"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            candidate = Path(result.stdout.strip()) / "libexec" / "support" / "analyzeHeadless"
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate.resolve()
    raise RuntimeError("Could not locate analyzeHeadless; pass --launcher explicitly")


def artifact_root(requested: Path | None) -> Path:
    root = requested if requested is not None else Path(tempfile.gettempdir()) / "codex-ghidra"
    return root.expanduser().resolve()


def create_run_dir(root: Path, args: argparse.Namespace) -> Path:
    selectors = getattr(args, "selectors", None)
    selector_identity = "\0".join(selectors) if selectors is not None else args.selector
    identity = "\0".join((
        str(args.project_location.resolve()), args.project_name, args.program,
        args.action, selector_identity,
    ))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = root / "runs" / f"{stamp}-{os.getpid()}-{digest}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_fingerprint(project_location: Path, project_name: str) -> str:
    digest = hashlib.sha256()
    candidates = [project_location / f"{project_name}.gpr"]
    repository = project_location / f"{project_name}.rep"
    if repository.is_dir():
        candidates.extend(
            path for path in repository.rglob("*")
            if path.is_file()
            and "user" not in path.relative_to(repository).parts
            and not path.name.startswith("~index.")
        )

    existing = sorted((path for path in candidates if path.is_file()), key=lambda path: str(path))
    if not existing:
        raise RuntimeError(
            f"Could not fingerprint Ghidra project {project_name!r} in {project_location}"
        )
    for path in existing:
        stat = path.stat()
        try:
            relative = path.relative_to(project_location)
        except ValueError:
            relative = path
        digest.update(str(relative).encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def query_cache_key(args: argparse.Namespace, project_location: Path, launcher: Path,
                    script_path: Path, fingerprint: str) -> str:
    java_script = script_path / "GhidraQuery.java"
    wrapper_script = Path(__file__).resolve()
    launcher_stat = launcher.stat()
    payload = {
        "schema": 1,
        "project_location": str(project_location),
        "project_name": args.project_name,
        "project_fingerprint": fingerprint,
        "program": args.program,
        "action": args.action,
        "selector": getattr(args, "selector", None),
        "selectors": getattr(args, "selectors", None),
        "timeout": args.timeout,
        "limit": args.limit,
        "inline_max_lines": getattr(args, "inline_max_lines", None),
        "no_inline": getattr(args, "no_inline", None),
        "preview_items": args.preview_items,
        "launcher": str(launcher),
        "launcher_size": launcher_stat.st_size,
        "launcher_mtime_ns": launcher_stat.st_mtime_ns,
        "java_sha256": file_digest(java_script),
        "wrapper_sha256": file_digest(wrapper_script),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:32]


def normalize_log_line(line: str) -> str:
    line = line.rstrip()
    if SCRIPT_PREFIX in line:
        line = line.split(SCRIPT_PREFIX, 1)[1].strip()
    if line.endswith(" (GhidraScript)"):
        line = line[:-len(" (GhidraScript)")].rstrip()
    return line


def extract_query_blocks(log_text: str) -> tuple[list[list[str]], bool]:
    lines = [normalize_log_line(line) for line in log_text.splitlines()]
    blocks: list[list[str]] = []
    current: list[str] | None = None
    complete = True
    for line in lines:
        if QUERY_BEGIN in line:
            if current is not None:
                complete = False
            current = []
            continue
        if QUERY_END in line:
            if current is None:
                complete = False
            else:
                blocks.append(current)
                current = None
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        complete = False
    return blocks, complete and bool(blocks)


def extract_query_block(log_text: str) -> tuple[list[str], bool]:
    blocks, complete = extract_query_blocks(log_text)
    return (blocks[-1] if blocks else []), complete and len(blocks) == 1


def parse_query_block(lines: Iterable[str]) -> tuple[dict[str, str], list[str], dict[str, list[str]]]:
    metadata: dict[str, str] = {}
    aliases: list[str] = []
    sections: dict[str, list[str]] = {}
    active: str | None = None
    begin_re = re.compile(r"^=== ([A-Z_]+)_BEGIN ===$")
    end_re = re.compile(r"^=== ([A-Z_]+)_END ===$")

    for line in lines:
        begin = begin_re.match(line)
        if begin:
            active = begin.group(1).lower()
            sections.setdefault(active, [])
            continue
        end = end_re.match(line)
        if end:
            active = None
            continue
        if active is not None:
            sections[active].append(line)
            continue
        if line.startswith("symbol="):
            aliases.append(line.split("=", 1)[1])
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if re.fullmatch(r"[a-z_]+", key):
                metadata[key] = value
    return metadata, aliases, sections


def lexical_index(c_code: str) -> dict[str, Any]:
    lines = c_code.splitlines()
    strings = sorted(
        {f"StringLiteral_{match}" for match in STRING_RE.findall(c_code)},
        key=lambda item: int(item.rsplit("_", 1)[1]),
    )
    controls: list[dict[str, Any]] = []
    indirect_lines: list[int] = []
    return_lines: list[int] = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        control = CONTROL_RE.match(stripped)
        if control:
            controls.append({
                "line": number,
                "kind": control.group(1).replace(" ", "_"),
                "preview": stripped[:240],
            })
        if "->vtable" in line or re.search(
            r"\(\*\*?\(code \*\*\)|\(\*[A-Za-z_][A-Za-z0-9_]*\)\s*\(", line
        ):
            indirect_lines.append(number)
        if stripped.startswith("return"):
            return_lines.append(number)
    return {
        "string_labels": strings,
        "control_flow": controls,
        "control_counts": dict(Counter(item["kind"] for item in controls)),
        "possible_indirect_call_lines": indirect_lines,
        "return_lines": return_lines,
    }


def unescape_tsv(value: str) -> str:
    output: list[str] = []
    index = 0
    escapes = {"t": "\t", "r": "\r", "n": "\n", "\\": "\\"}
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value) \
                and value[index + 1] in escapes:
            output.append(escapes[value[index + 1]])
            index += 2
        else:
            output.append(value[index])
            index += 1
    return "".join(output)


def semantic_index(path: Path, c_line_count: int,
                   metadata: dict[str, str]) -> dict[str, Any]:
    unavailable: dict[str, Any] = {
        "available": False,
        "format": metadata.get("semantic_format", "ghidra-markup-blocks-v1"),
        "block_count": 0,
        "blocks": [],
    }
    if metadata.get("semantic_complete") != "true":
        unavailable["reason"] = metadata.get(
            "semantic_error", "Ghidra semantic markup export was unavailable"
        )
        return unavailable
    if not path.is_file():
        unavailable["reason"] = "Ghidra reported a semantic artifact that does not exist"
        return unavailable

    try:
        rows = path.read_text(encoding="utf-8", errors="strict").splitlines()
        expected = (
            "block_id\tkind\tdepth\tparent\tstart_line\tend_line\t"
            "min_address\tmax_address\theader"
        )
        if not rows or rows[0] != expected:
            raise ValueError("unsupported semantic artifact header")
        blocks: list[dict[str, Any]] = []
        known_ids: set[str] = set()
        for row_number, row in enumerate(rows[1:], 2):
            fields = row.split("\t", 8)
            if len(fields) != 9:
                raise ValueError(f"semantic row {row_number} has {len(fields)} fields")
            block_id, kind, depth_text, parent, start_text, end_text, \
                min_address, max_address, header = fields
            if not re.fullmatch(r"B\d{4}", block_id) or block_id in known_ids:
                raise ValueError(f"semantic row {row_number} has an invalid block ID")
            depth, start, end = int(depth_text), int(start_text), int(end_text)
            if depth < 0 or start <= 0 or end < start or end > c_line_count:
                raise ValueError(f"semantic row {row_number} has an invalid range")
            if parent and parent not in known_ids:
                raise ValueError(f"semantic row {row_number} has an unknown parent")
            block = {
                "id": block_id,
                "kind": kind,
                "depth": depth,
                "parent": parent or None,
                "lines": [start, end],
                "address": [min_address or None, max_address or None],
                "header": unescape_tsv(header),
            }
            blocks.append(block)
            known_ids.add(block_id)
        reported_count = metadata.get("semantic_blocks")
        if reported_count is not None and int(reported_count) != len(blocks):
            raise ValueError("semantic block count does not match Ghidra metadata")
        return {
            "available": True,
            "format": metadata.get("semantic_format", "ghidra-markup-blocks-v1"),
            "artifact": path.name,
            "block_count": len(blocks),
            "blocks": blocks,
        }
    except (OSError, UnicodeError, ValueError) as error:
        unavailable["reason"] = f"Semantic artifact rejected: {error}"
        return unavailable


def semantic_preview(index: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    if index.get("available") is not True:
        return []
    return [
        {
            "id": block["id"],
            "kind": block["kind"],
            "lines": block["lines"],
            "header": block["header"][:160],
        }
        for block in index["blocks"][:min(limit, 8)]
    ]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cached_summary(cache_dir: Path, cache_key: str) -> dict[str, Any] | None:
    marker = cache_dir / ".complete"
    summary_path = cache_dir / "summary.json"
    if not marker.is_file() or not summary_path.is_file():
        return None
    try:
        if marker.read_text(encoding="utf-8").strip() != cache_key:
            return None
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(summary, dict) or summary.get("ok") is not True:
        return None
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    artifact_names = list(artifacts.values())
    items = summary.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("artifacts"), dict):
                artifact_names.extend(item["artifacts"].values())
    for name in artifact_names:
        relative = Path(name) if isinstance(name, str) else None
        if relative is None or relative.is_absolute() or ".." in relative.parts:
            return None
        if not (cache_dir / relative).is_file():
            return None
    summary["artifact_dir"] = str(cache_dir)
    return summary


def emit_summary(summary: dict[str, Any], artifact_dir: Path, cache_hit: bool) -> int:
    summary["artifact_dir"] = str(artifact_dir)
    cache = summary.get("cache")
    if isinstance(cache, dict):
        cache["hit"] = cache_hit
    print(compact_json(summary))
    decompile = summary.get("decompile")
    artifacts = summary.get("artifacts")
    if isinstance(decompile, dict) and decompile.get("inlined") is True \
            and isinstance(artifacts, dict):
        c_name = artifacts.get("decompile")
        if isinstance(c_name, str):
            c_path = artifact_dir / c_name
            if c_path.is_file():
                c_code = c_path.read_text(encoding="utf-8", errors="replace")
                print("=== DECOMPILE_BEGIN ===")
                print(c_code, end="" if c_code.endswith("\n") else "\n")
                print("=== DECOMPILE_END ===")
    return 0


def finalize_success(summary: dict[str, Any], run_dir: Path, cache_dir: Path | None,
                     cache_key: str | None, fingerprint: str | None) -> int:
    if cache_dir is None or cache_key is None:
        summary["cache"] = {"enabled": False, "hit": False}
        return emit_summary(summary, run_dir, False)

    summary["cache"] = {
        "enabled": True,
        "hit": False,
        "key": cache_key,
        "project_fingerprint": fingerprint[:16] if fingerprint else None,
        "stored": True,
    }
    summary["artifact_dir"] = str(cache_dir)
    summary["artifacts"]["summary"] = "summary.json"
    write_json(run_dir / "summary.json", summary)
    (run_dir / ".complete").write_text(cache_key + "\n", encoding="utf-8")
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_dir.rename(cache_dir)
        return emit_summary(summary, cache_dir, False)
    except FileExistsError:
        cached = load_cached_summary(cache_dir, cache_key)
        if cached is not None:
            return emit_summary(cached, cache_dir, True)
    except OSError:
        pass

    summary["artifact_dir"] = str(run_dir)
    summary["cache"]["stored"] = False
    summary["cache"]["reason"] = "cache publish failed"
    write_json(run_dir / "summary.json", summary)
    return emit_summary(summary, run_dir, False)


def tail_lines(text: str, limit: int = 24) -> list[str]:
    lines = [normalize_log_line(line) for line in text.splitlines() if line.strip()]
    signals = (
        "error", "exception", "failed", "failure", "timeout", "no function",
        "bad instruction", "not found", "could not", "incomplete",
    )
    interesting = [
        line for line in lines
        if not line.lstrip().startswith("at ")
        and any(signal in line.lower() for signal in signals)
    ]
    selected = interesting if interesting else [
        line for line in lines
        if not line.startswith("INFO ") and not line.lstrip().startswith("at ")
    ]
    return selected[-min(limit, 12):]


def fail(message: str, *, log_path: Path | None = None, log_text: str = "",
         returncode: int | None = None) -> int:
    result: dict[str, Any] = {"ok": False, "error": message}
    if returncode is not None:
        result["returncode"] = returncode
    if log_path is not None:
        result["log"] = str(log_path)
    if log_text:
        result["tail"] = tail_lines(log_text)
    print(compact_json(result))
    return 1


def run_query(args: argparse.Namespace) -> int:
    project_location = args.project_location.expanduser().resolve()
    script_path = args.script_path.expanduser().resolve()
    if not project_location.is_dir():
        return fail(f"Project location does not exist: {project_location}")
    if not script_path.is_dir():
        return fail(f"Script path does not exist: {script_path}")
    try:
        launcher = discover_launcher(args.launcher)
        root = artifact_root(args.artifacts)
        fingerprint: str | None = None
        cache_key: str | None = None
        cache_dir: Path | None = None
        if not args.no_cache:
            fingerprint = project_fingerprint(project_location, args.project_name)
            cache_key = query_cache_key(
                args, project_location, launcher, script_path, fingerprint
            )
            candidate = root / "cache" / cache_key
            cached = load_cached_summary(candidate, cache_key)
            if cached is not None:
                return emit_summary(cached, candidate, True)
            if not candidate.exists():
                cache_dir = candidate
        run_dir = create_run_dir(root, args)
    except (OSError, RuntimeError) as error:
        return fail(str(error))

    log_path = run_dir / "headless.log"
    result_path = run_dir / "result.txt"
    c_path = run_dir / "decompile.c"
    semantic_path = run_dir / "semantic.tsv"
    java_action = "export" if args.action == "decompile" else args.action
    final_number = args.timeout if args.action == "decompile" else args.limit
    script_args = [java_action, args.selector, str(final_number)]
    if args.action == "decompile":
        script_args.extend((str(c_path), str(semantic_path)))

    command = [
        str(launcher), str(project_location), args.project_name,
        "-process", args.program, "-readOnly", "-noanalysis",
        "-scriptPath", str(script_path),
        "-postScript", "GhidraQuery.java", *script_args,
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=max(args.process_timeout, args.timeout + 60),
            check=False,
        )
        log_text = completed.stdout
        returncode = completed.returncode
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        log_path.write_text(partial, encoding="utf-8")
        return fail("analyzeHeadless exceeded the process timeout", log_path=log_path,
                    log_text=partial)

    log_path.write_text(log_text, encoding="utf-8")
    block, complete = extract_query_block(log_text)
    if block:
        result_path.write_text("\n".join(block) + "\n", encoding="utf-8")
    if returncode != 0 or not complete:
        reason = "analyzeHeadless failed" if returncode != 0 else "Ghidra query markers were incomplete"
        return fail(reason, log_path=log_path, log_text=log_text, returncode=returncode)

    metadata, aliases, sections = parse_query_block(block)
    common: dict[str, Any] = {
        "ok": True,
        "action": args.action,
        "selector": args.selector,
        "program": metadata.get("program", args.program),
        "image_base": metadata.get("image_base"),
        "resolved_address": metadata.get("resolved_address"),
        "function": metadata.get("function"),
        "entry": metadata.get("entry"),
        "body": [metadata.get("body_min"), metadata.get("body_max")],
        "parameter_count": int(metadata["parameter_count"])
            if metadata.get("parameter_count", "").isdigit() else None,
        "thunk": metadata.get("thunk") == "true",
        "aliases": {
            "count": len(aliases),
            "preview": aliases[:min(args.preview_items, 20)],
            "truncated": len(aliases) > min(args.preview_items, 20),
        },
        "artifact_dir": str(run_dir),
        "artifacts": {"result": result_path.name, "log": log_path.name},
    }

    if args.action != "decompile":
        if args.action != "info":
            items = sections.get(args.action, [])
            preview_limit = min(args.preview_items, 50)
            common["result"] = {
                "count": len(items),
                "preview": items[:preview_limit],
                "truncated": len(items) > preview_limit,
            }
        return finalize_success(common, run_dir, cache_dir, cache_key, fingerprint)

    if not c_path.is_file() or metadata.get("decompile_complete") != "true":
        return fail("Ghidra completed without a verified decompile artifact",
                    log_path=log_path, log_text=log_text, returncode=returncode)

    c_bytes = c_path.read_bytes()
    c_code = c_bytes.decode("utf-8", errors="replace")
    line_count = len(c_code.splitlines())
    index = lexical_index(c_code)
    semantic = semantic_index(semantic_path, line_count, metadata)
    callees = sections.get("callees", [])
    manifest = {
        "schema_version": 2,
        "query": {key: value for key, value in common.items() if key != "artifact_dir"},
        "decompile": {
            "complete": True,
            "artifact": c_path.name,
            "lines": line_count,
            "bytes": len(c_bytes),
            "sha256": hashlib.sha256(c_bytes).hexdigest(),
        },
        "direct_callees": callees,
        "semantic_index": semantic,
        "lexical_index": index,
    }
    index_path = run_dir / "index.json"
    write_json(index_path, manifest)

    common["decompile"] = {
        "complete": True,
        "lines": line_count,
        "bytes": len(c_bytes),
        "sha256": manifest["decompile"]["sha256"],
        "inlined": not args.no_inline and line_count <= args.inline_max_lines,
    }
    common["artifacts"].update({"decompile": c_path.name, "index": index_path.name})
    if semantic_path.is_file():
        common["artifacts"]["semantic"] = semantic_path.name
    common["evidence"] = {
        "direct_callee_count": len(callees),
        "direct_callees_preview": callees[:min(args.preview_items, 20)],
        "string_labels": index["string_labels"][:min(args.preview_items, 20)],
        "string_label_count": len(index["string_labels"]),
        "control_counts": index["control_counts"],
        "possible_indirect_call_lines":
            index["possible_indirect_call_lines"][:min(args.preview_items, 20)],
        "semantic_available": semantic["available"],
        "semantic_block_count": semantic["block_count"],
        "semantic_blocks_preview": semantic_preview(semantic, args.preview_items),
    }
    if semantic.get("available") and len(semantic["blocks"]) > 1:
        common["read_hint"] = {
            "index": index_path.name,
            "block": semantic["blocks"][1]["id"],
        }
    else:
        common["read_hint"] = {"artifact": c_path.name, "lines": f"1:{DEFAULT_READ_LINES}"}
    return finalize_success(common, run_dir, cache_dir, cache_key, fingerprint)


def run_batch(args: argparse.Namespace) -> int:
    args.selectors = list(dict.fromkeys(args.selectors))
    allowed = min(args.max_items, HARD_BATCH_LIMIT)
    if len(args.selectors) > allowed:
        return fail(
            f"batch has {len(args.selectors)} selectors; limit is {allowed} "
            f"(hard maximum {HARD_BATCH_LIMIT})"
        )

    project_location = args.project_location.expanduser().resolve()
    script_path = args.script_path.expanduser().resolve()
    if not project_location.is_dir():
        return fail(f"Project location does not exist: {project_location}")
    if not script_path.is_dir():
        return fail(f"Script path does not exist: {script_path}")
    try:
        launcher = discover_launcher(args.launcher)
        root = artifact_root(args.artifacts)
        fingerprint: str | None = None
        cache_key: str | None = None
        cache_dir: Path | None = None
        if not args.no_cache:
            fingerprint = project_fingerprint(project_location, args.project_name)
            cache_key = query_cache_key(
                args, project_location, launcher, script_path, fingerprint
            )
            candidate = root / "cache" / cache_key
            cached = load_cached_summary(candidate, cache_key)
            if cached is not None:
                return emit_summary(cached, candidate, True)
            if not candidate.exists():
                cache_dir = candidate
        run_dir = create_run_dir(root, args)
    except (OSError, RuntimeError) as error:
        return fail(str(error))

    log_path = run_dir / "headless.log"
    command = [
        str(launcher), str(project_location), args.project_name,
        "-process", args.program, "-readOnly", "-noanalysis",
        "-scriptPath", str(script_path),
    ]
    result_paths: list[Path] = []
    c_paths: list[Path | None] = []
    semantic_paths: list[Path | None] = []
    for index, selector in enumerate(args.selectors):
        result_paths.append(run_dir / f"result-{index:03d}.txt")
        java_action = "export" if args.action == "decompile" else args.action
        final_number = args.timeout if args.action == "decompile" else args.limit
        script_args = [java_action, selector, str(final_number)]
        if args.action == "decompile":
            c_path = run_dir / f"decompile-{index:03d}.c"
            semantic_path = run_dir / f"semantic-{index:03d}.tsv"
            c_paths.append(c_path)
            semantic_paths.append(semantic_path)
            script_args.extend((str(c_path), str(semantic_path)))
        else:
            c_paths.append(None)
            semantic_paths.append(None)
        command.extend(["-postScript", "GhidraQuery.java", *script_args])

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=max(args.process_timeout, (args.timeout + 30) * len(args.selectors) + 60),
            check=False,
        )
        log_text = completed.stdout
        returncode = completed.returncode
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        log_path.write_text(partial, encoding="utf-8")
        return fail("batch analyzeHeadless exceeded the process timeout", log_path=log_path,
                    log_text=partial)

    log_path.write_text(log_text, encoding="utf-8")
    blocks, complete = extract_query_blocks(log_text)
    if returncode != 0 or not complete or len(blocks) != len(args.selectors):
        reason = "batch analyzeHeadless failed" if returncode != 0 else (
            f"batch returned {len(blocks)} complete results for {len(args.selectors)} selectors"
        )
        return fail(reason, log_path=log_path, log_text=log_text, returncode=returncode)

    items: list[dict[str, Any]] = []
    preview_limit = min(args.preview_items, 10)
    for index, (selector, block, result_path, c_path, semantic_path) in enumerate(
            zip(args.selectors, blocks, result_paths, c_paths, semantic_paths)):
        result_path.write_text("\n".join(block) + "\n", encoding="utf-8")
        metadata, aliases, sections = parse_query_block(block)
        item: dict[str, Any] = {
            "index": index,
            "selector": selector,
            "resolved_address": metadata.get("resolved_address"),
            "function": metadata.get("function"),
            "entry": metadata.get("entry"),
            "body": [metadata.get("body_min"), metadata.get("body_max")],
            "thunk": metadata.get("thunk") == "true",
            "aliases": {
                "count": len(aliases),
                "preview": aliases[:min(preview_limit, 5)],
                "truncated": len(aliases) > min(preview_limit, 5),
            },
            "artifacts": {"result": result_path.name},
        }
        if args.action != "decompile":
            if args.action != "info":
                values = sections.get(args.action, [])
                item["result"] = {
                    "count": len(values),
                    "preview": values[:preview_limit],
                    "truncated": len(values) > preview_limit,
                }
            items.append(item)
            continue

        if c_path is None or not c_path.is_file() \
                or metadata.get("decompile_complete") != "true":
            return fail(
                f"batch item {index} completed without a verified decompile artifact",
                log_path=log_path, log_text=log_text, returncode=returncode,
            )
        c_bytes = c_path.read_bytes()
        c_code = c_bytes.decode("utf-8", errors="replace")
        lexical = lexical_index(c_code)
        semantic = semantic_index(
            semantic_path, len(c_code.splitlines()), metadata
        ) if semantic_path is not None else {
            "available": False, "block_count": 0, "blocks": [],
            "reason": "semantic artifact path was unavailable",
        }
        callees = sections.get("callees", [])
        index_path = run_dir / f"index-{index:03d}.json"
        item_manifest = {
            "schema_version": 2,
            "selector": selector,
            "function": item["function"],
            "entry": item["entry"],
            "decompile": {
                "artifact": c_path.name,
                "complete": True,
                "lines": len(c_code.splitlines()),
                "bytes": len(c_bytes),
                "sha256": hashlib.sha256(c_bytes).hexdigest(),
            },
            "direct_callees": callees,
            "semantic_index": semantic,
            "lexical_index": lexical,
        }
        write_json(index_path, item_manifest)
        item["artifacts"].update({"decompile": c_path.name, "index": index_path.name})
        if semantic_path is not None and semantic_path.is_file():
            item["artifacts"]["semantic"] = semantic_path.name
        item["decompile"] = {
            key: value for key, value in item_manifest["decompile"].items()
            if key != "artifact"
        }
        item["evidence"] = {
            "direct_callee_count": len(callees),
            "direct_callees_preview": callees[:preview_limit],
            "string_label_count": len(lexical["string_labels"]),
            "string_labels": lexical["string_labels"][:preview_limit],
            "control_counts": lexical["control_counts"],
            "possible_indirect_call_lines":
                lexical["possible_indirect_call_lines"][:preview_limit],
            "semantic_available": semantic["available"],
            "semantic_block_count": semantic["block_count"],
            "semantic_blocks_preview": semantic_preview(semantic, min(preview_limit, 5)),
        }
        items.append(item)

    summary = {
        "ok": True,
        "action": f"batch-{args.action}",
        "program": args.program,
        "item_count": len(items),
        "artifact_dir": str(run_dir),
        "artifacts": {"log": log_path.name},
        "items": items,
    }
    return finalize_success(summary, run_dir, cache_dir, cache_key, fingerprint)


def parse_line_range(specification: str, total: int) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+):(\d+)", specification.strip())
    if not match:
        raise ValueError("--lines must use one-based START:END syntax")
    start, end = (int(match.group(1)), int(match.group(2)))
    if start <= 0 or end < start:
        raise ValueError("invalid line range")
    if total == 0 or start > total:
        raise ValueError(f"range starts beyond artifact length ({total} lines)")
    return start, min(end, total)


def run_read(args: argparse.Namespace) -> int:
    manifest: dict[str, Any] | None = None
    index_path: Path | None = None
    selected_block: dict[str, Any] | None = None
    artifact = args.artifact.expanduser().resolve() if args.artifact is not None else None

    if args.index is not None:
        index_path = args.index.expanduser().resolve()
        if not index_path.is_file():
            return fail(f"Index does not exist: {index_path}")
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return fail(f"Could not read evidence index: {error}")
        if not isinstance(loaded, dict):
            return fail("Evidence index must contain a JSON object")
        manifest = loaded
        decompile = manifest.get("decompile")
        if artifact is None:
            artifact_name = decompile.get("artifact") if isinstance(decompile, dict) else None
            relative = Path(artifact_name) if isinstance(artifact_name, str) else None
            if relative is None or relative.is_absolute() or ".." in relative.parts:
                return fail("Evidence index has no safe relative decompile artifact")
            artifact = (index_path.parent / relative).resolve()

    if args.block is not None:
        if manifest is None:
            return fail("--block requires --index")
        semantic = manifest.get("semantic_index")
        if not isinstance(semantic, dict) or semantic.get("available") is not True:
            reason = semantic.get("reason") if isinstance(semantic, dict) else None
            return fail(f"Semantic block index is unavailable{': ' + reason if reason else ''}")
        blocks = semantic.get("blocks")
        if not isinstance(blocks, list):
            return fail("Semantic block list is malformed")
        block_id = args.block.upper()
        selected_block = next(
            (block for block in blocks
             if isinstance(block, dict) and block.get("id") == block_id),
            None,
        )
        if selected_block is None:
            return fail(f"Semantic block was not found: {block_id}")

    if artifact is None:
        return fail("Provide an artifact path or --index")
    if not artifact.is_file():
        return fail(f"Artifact does not exist: {artifact}")
    if manifest is not None:
        decompile = manifest.get("decompile")
        expected_sha = decompile.get("sha256") if isinstance(decompile, dict) else None
        if isinstance(expected_sha, str) and file_digest(artifact) != expected_sha:
            return fail("Artifact SHA-256 does not match the evidence index")
    text = artifact.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    hard_limit = min(args.max_lines, HARD_READ_LIMIT)
    matches: list[int] = []

    try:
        if selected_block is not None:
            block_lines = selected_block.get("lines")
            if not isinstance(block_lines, list) or len(block_lines) != 2 \
                    or not all(isinstance(value, int) for value in block_lines):
                return fail("Selected semantic block has a malformed line range")
            start = max(1, block_lines[0] - args.block_context)
            end = min(len(lines), block_lines[1] + args.block_context)
        elif args.around is not None:
            matches = [number for number, line in enumerate(lines, 1) if args.around in line]
            if args.occurrence > len(matches):
                return fail(f"Substring occurrence not found: {args.around!r}")
            center = matches[args.occurrence - 1]
            start = max(1, center - args.context)
            end = min(len(lines), center + args.context)
        else:
            specification = args.lines or f"1:{DEFAULT_READ_LINES}"
            start, end = parse_line_range(specification, len(lines))
    except ValueError as error:
        return fail(str(error))

    requested_end = end
    if end - start + 1 > hard_limit:
        end = start + hard_limit - 1
    summary = {
        "ok": True,
        "artifact": str(artifact),
        "total_lines": len(lines),
        "range": [start, end],
        "requested_end": requested_end,
        "truncated": end < requested_end,
        "match_count": len(matches) if args.around is not None else None,
        "occurrence": args.occurrence if args.around is not None else None,
    }
    if index_path is not None:
        summary["index"] = str(index_path)
    if selected_block is not None:
        summary["block"] = {
            "id": selected_block.get("id"),
            "kind": selected_block.get("kind"),
            "lines": selected_block.get("lines"),
            "header": selected_block.get("header"),
        }
        summary["block_truncated"] = (
            end < selected_block["lines"][1] or start > selected_block["lines"][0]
        )
    print(compact_json(summary))
    print("=== ARTIFACT_SLICE_BEGIN ===")
    for number in range(start, end + 1):
        line = lines[number - 1]
        if len(line) > args.max_line_chars:
            line = line[:args.max_line_chars] + " <line-truncated>"
        print(f"{number:06d}|{line}")
    print("=== ARTIFACT_SLICE_END ===")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "query":
        return run_query(args)
    if args.command == "batch":
        return run_batch(args)
    return run_read(args)


if __name__ == "__main__":
    raise SystemExit(main())

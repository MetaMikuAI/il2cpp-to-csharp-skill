---
name: il2cpp-to-csharp
description: Reconstruct plausible C# from Unity IL2CPP binaries with either the IDA Pro MCP backend or the Ghidra backend, using matching Il2CppDumper metadata. Use for method VA/RVA/name analysis, string literal resolution, vtable mapping, switch/enum recovery, compiler-generated lambdas, LINQ, coroutine or async state machines, and IL2CPP runtime-helper cleanup. Pick exactly one backend based on the environment that is actually available and follow only that backend's instructions. Do not use for Mono/.NET assemblies, generic native decompilation, or exploit development.
---

# IL2CPP to C# Source Restoration

Reconstruct readable C# from Unity IL2CPP binaries, one method at a time. This skill ships two independent backends that consume the same Il2CppDumper artifacts (`script.json`, `stringliteral.json`, `DummyDll` / `dump.cs`) and produce the same kind of output.

## 1. Choose a Backend — do this first, exactly once

Read and follow **exactly one** backend's SKILL.md. The two backends are self-contained: never mix their instructions, tool rules, or docs.

- **IDA backend** (original) — use when IDA Pro MCP tools are present in the tool list (e.g. `decompile_function`, `get_function_by_address`, `get_callees`, `get_xrefs_to`), or when the user states IDA is the working environment.
  → Read [ida/SKILL.md](ida/SKILL.md) and follow it completely. All IDA docs and scripts live under `ida/`.
- **Ghidra backend** (custom) — use when Ghidra (GUI or `analyzeHeadless`) is set up and this skill's Ghidra scripts are reachable (`ghidra/scripts/ghidra_query.py`, `ghidra/scripts/ApplyIl2CppSymbols.java`), or when the user states Ghidra is the working environment.
  → Read [ghidra/SKILL.md](ghidra/SKILL.md) and follow it completely. All Ghidra docs and scripts live under `ghidra/`.

If neither environment is confirmed — no IDA Pro MCP tools and no ready Ghidra project/scripts — ask the user which backend is ready before analyzing anything.

## 2. Shared Rules (apply to both backends)

- Treat complete decompiler C as the primary evidence. If output is truncated, incomplete, or fails, obtain the full body before reconstructing; never fill missing regions from context.
- Never invent string literals, names, conditions, enum labels, or branches. Confirm everything against dump metadata and stub projects.
- Preserve all metadata attributes (`[Token]`, `[Address]`, `[FieldOffset]`, `[CompilerGenerated]`, …) from any supplied stub.
- Restore one method at a time; process multiple VAs sequentially and return each result before continuing.
- Report unresolved details explicitly instead of guessing.

## 3. Repository Layout

| Path | Content |
|---|---|
| `ida/SKILL.md` | IDA backend workflow (original skill, unmodified) |
| `ida/` | IDA docs: `ida-usage.md`, `ida-quirks.md`, `strings.md`, `helpers.md`, `compiler-patterns.md`; `scripts/` (`lookup_strings.py`, `field_offset.py`) |
| `ghidra/SKILL.md` | Ghidra backend workflow (custom skill, unmodified) |
| `ghidra/` | Ghidra docs: `ghidra-setup.md`, `ghidra-query.md`, `ghidra-quirks.md`, `strings.md`, `helpers.md`, `string-formatting.md`, `lambdas-closures.md`, `linq-generics.md`, `coroutines.md`, `async.md`, `runtime-exceptions.md`, `runtime-memory.md`; `scripts/` (`ghidra_query.py`, `GhidraQuery.java`, `ApplyIl2CppSymbols.java`, `query_script_json.py`, `lookup_strings.py`, `field_offset.py`); `agents/` |

Both `scripts/` trees are backend-specific copies; always run them from within their own backend directory so relative paths and references stay valid.

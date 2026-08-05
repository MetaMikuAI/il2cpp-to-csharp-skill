---
name: il2cpp-to-csharp
description: Reconstruct plausible C# from Unity IL2CPP binaries with either the IDA Pro MCP backend or the Ghidra backend, using matching Il2CppDumper metadata. Use for method VA/RVA/name analysis, string literal resolution, vtable mapping, switch/enum recovery, compiler-generated lambdas, LINQ, coroutine or async state machines, and IL2CPP runtime-helper cleanup. Pick exactly one backend based on the environment that is actually available and follow only that backend's instructions. Do not use for Mono/.NET assemblies, generic native decompilation, or exploit development.
---

# IL2CPP to C# Source Restoration

Reconstruct readable C# from Unity IL2CPP binaries, one method at a time. This skill ships two independent backends that consume the same Il2CppDumper artifacts (`script.json`, `stringliteral.json`, `DummyDll` / `dump.cs`) and produce the same kind of output.

## 1. Choose a Backend — do this first, exactly once

Ask the user to specify which backend to use. Read and follow **exactly one** backend's workflow. The two backends are self-contained: never mix their instructions, tool rules, or docs.

- **IDA backend** — follow [ida/workflow.md](ida/workflow.md). All IDA docs and scripts live under `ida/`.
- **Ghidra backend** — follow [ghidra/workflow.md](ghidra/workflow.md). All Ghidra docs and scripts live under `ghidra/`.

## 2. Shared Rules (apply to both backends)

- Treat complete decompiler C as the primary evidence. If output is truncated, incomplete, or fails, obtain the full body before reconstructing; never fill missing regions from context.
- Never invent string literals, names, conditions, enum labels, or branches. Confirm everything against dump metadata and stub projects.
- Preserve all metadata attributes (`[Token]`, `[Address]`, `[FieldOffset]`, `[CompilerGenerated]`, …) from any supplied stub.
- Restore one method at a time; process multiple VAs sequentially and return each result before continuing.
- Report unresolved details explicitly instead of guessing.

## 3. Repository Layout

| Path | Content |
|---|---|
| `ida/workflow.md` | IDA backend workflow |
| `ida/` | IDA docs: `ida-usage.md`, `ida-quirks.md`, `strings.md`, `helpers.md`, `compiler-patterns.md` |
| `ghidra/workflow.md` | Ghidra backend workflow |
| `ghidra/` | Ghidra docs: `ghidra-setup.md`, `ghidra-query.md`, `ghidra-quirks.md`, `strings.md`, `helpers.md`, `string-formatting.md`, `lambdas-closures.md`, `linq-generics.md`, `coroutines.md`, `async.md`, `runtime-exceptions.md`, `runtime-memory.md`; `scripts/` (`ghidra_query.py`, `GhidraQuery.java`, `ApplyIl2CppSymbols.java`); `agents/` |
| `scripts/` | Shared tools: `lookup_strings.py`, `field_offset.py`, `query_script_json.py` |

Run shared scripts from the root `scripts/` directory. Ghidra-specific scripts live under `ghidra/scripts/`; run them from within `ghidra/`.

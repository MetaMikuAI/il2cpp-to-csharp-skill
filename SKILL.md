---
name: il2cpp-to-csharp
description: Reconstruct plausible C# from Unity IL2CPP binaries with either the IDA Pro MCP backend or the Ghidra backend, using matching Il2CppDumper metadata. Use for method VA/RVA/name analysis, string literal resolution, vtable mapping, switch/enum recovery, compiler-generated lambdas, LINQ, coroutine or async state machines, and IL2CPP runtime-helper cleanup. Pick exactly one backend based on the environment that is actually available and follow only that backend's instructions. Do not use for Mono/.NET assemblies, generic native decompilation, or exploit development.
---

# IL2CPP to C# Source Restoration

Reconstruct readable C# from Unity IL2CPP binaries, one method at a time. This skill ships two independent backends that consume the same Il2CppDumper artifacts (`script.json`, `stringliteral.json`, `DummyDll` / `dump.cs`) and produce the same kind of output.

## 1. Pick a Mode — do this first

- **Task mode** — the user wants C# reconstructed from a concrete binary or method. Ask the user which backend to use, then read that backend's workflow completely and follow **exactly one** backend. The two backends are self-contained: never mix their instructions, tool rules, or docs.
- **Reference mode** — the user only wants to consult this skill (no backend chosen yet, no binary at hand), for example "how does this skill resolve string literals / lambdas / state machines?". Skip backend selection and read the topic doc for that construct directly from the trigger table in section 3. Either backend's version of a topic doc may be read; both document the same constructs with their own tooling (IDA docs are more consolidated, Ghidra docs are split finer).

## 2. Shared Rules (apply to both backends)

- Treat complete decompiler C as the primary evidence. If output is truncated, incomplete, or fails, obtain the full body before reconstructing; never fill missing regions from context.
- Never invent string literals, names, conditions, enum labels, or branches. Confirm everything against dump metadata and stub projects.
- Preserve all metadata attributes (`[Token]`, `[Address]`, `[FieldOffset]`, `[CompilerGenerated]`, …) from any supplied stub.
- Restore one method at a time; process multiple VAs sequentially and return each result before continuing.
- Report unresolved details explicitly instead of guessing.

## 3. Doc Trigger Table

Every row is a direct link to a doc in this skill. Read the doc before restoring or answering about that construct — when a trigger fires, that read is mandatory, not optional. Backend workflows repeat some of these pointers in context; this table is the routing source of truth. In task mode, stay within the backend you picked.

### IDA backend

Entry (task mode): read [ida/workflow.md](ida/workflow.md) completely before analyzing a method.

| Trigger | Read before restoring |
|---|---|
| `StringLiteral_N` in the pseudo-C | [ida/strings.md](ida/strings.md) |
| `__c` / `__9__N_M` / `b__` / `DisplayClassN_M` / `<Outer>g__` helpers | [ida/compiler-patterns.md](ida/compiler-patterns.md) |
| LINQ chains (`Select` / `Where` / `ToArray` / `Aggregate` / …) | [ida/compiler-patterns.md](ida/compiler-patterns.md) |
| `MoveNext`, iterator, async / UniTask state machine | [ida/compiler-patterns.md](ida/compiler-patterns.md) and [ida/ida-quirks.md](ida/ida-quirks.md) |
| Unlabeled `sub_xxx` call that may be IL2CPP machinery | [ida/helpers.md](ida/helpers.md) |
| `vtable._N` slot calls | [ida/workflow.md](ida/workflow.md) (Vtable Call Resolution) |
| Field-offset noise (`BYTE4(Instance[40].monitor)`, `LOBYTE(...)`, …) | [ida/ida-quirks.md](ida/ida-quirks.md) |
| Truncated or failed decompile, suspected ICF folding | [ida/workflow.md](ida/workflow.md) and [ida/ida-usage.md](ida/ida-usage.md) |
| IDA MCP tool choice, prohibited tools, timeouts | [ida/ida-usage.md](ida/ida-usage.md) |

### Ghidra backend

Entry (task mode): read [ghidra/workflow.md](ghidra/workflow.md) completely before analyzing a method.

| Trigger | Read before restoring |
|---|---|
| First-time project creation, image import, symbol application | [ghidra/ghidra-setup.md](ghidra/ghidra-setup.md) |
| Query wrapper usage, batch syntax, address coordinates, query failures | [ghidra/ghidra-query.md](ghidra/ghidra-query.md) |
| `StringLiteral_N` | [ghidra/strings.md](ghidra/strings.md) |
| Concatenation, `string.Format`, boxing, interpolation lowering | [ghidra/string-formatting.md](ghidra/string-formatting.md) |
| `__c` / `b__` / `DisplayClass` / `g__` helpers | [ghidra/lambdas-closures.md](ghidra/lambdas-closures.md) |
| LINQ or shared generic bodies | [ghidra/linq-generics.md](ghidra/linq-generics.md) |
| Iterator / boolean `MoveNext` state machine | [ghidra/coroutines.md](ghidra/coroutines.md) |
| Awaiter / `Task` / UniTask state machine | [ghidra/async.md](ghidra/async.md) |
| Unlabeled `FUN_...` that may be IL2CPP machinery | [ghidra/helpers.md](ghidra/helpers.md), then [ghidra/runtime-memory.md](ghidra/runtime-memory.md) or [ghidra/runtime-exceptions.md](ghidra/runtime-exceptions.md) |
| Address drift, thunks, ICF labels, offcuts, decompiler type problems | [ghidra/ghidra-quirks.md](ghidra/ghidra-quirks.md) |

## 4. Scripts

- Shared tools, run from the skill root's `scripts/` directory: `lookup_strings.py` (`StringLiteral_N` / RVA / VA to string), `field_offset.py` (object / Fields offset arithmetic), `query_script_json.py` (Il2CppDumper method records).
- Ghidra wrapper scripts live under `ghidra/scripts/` — `ghidra_query.py`, `GhidraQuery.java`, `ApplyIl2CppSymbols.java` — and run from within `ghidra/`.

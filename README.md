# il2cpp-to-csharp-skill

[中文](README.zh-CN.md)

A skill for restoring readable C# from Unity IL2CPP binaries. It ships **two independent backends** that share the same goal and the same Il2CppDumper artifacts:

| Backend | Environment | Docs |
|---|---|---|
| **IDA** (original) | IDA Pro + IDA Pro MCP | [`ida/SKILL.md`](ida/SKILL.md) |
| **Ghidra** (custom) | Ghidra GUI or `analyzeHeadless` | [`ghidra/SKILL.md`](ghidra/SKILL.md) |

This is not a one-click decompiler. It helps an agent analyze user-provided VAs or function names and reconstruct C# while preserving strings, switch branches, lambdas, LINQ, async/coroutine state machines, and IL2CPP-specific quirks.

**Backend selection:** the root [`SKILL.md`](SKILL.md) is a thin dispatcher. It picks exactly one backend — IDA Pro MCP when IDA MCP tools are available, Ghidra when the Ghidra setup is available — and then follows that backend's own `SKILL.md`. The two backends never mix instructions, so neither workflow is diluted.

Output quality depends on the AI model and the available context. Restored code is for reference only and should be manually reviewed against the decompiler output, DummyDll stubs, and runtime behavior.

## Requirements

- **IDA backend:** IDA Pro with IDA Pro MCP enabled.
- **Ghidra backend:** Ghidra (GUI or `analyzeHeadless`).
- Both: Il2CppDumper output — `script.json`, `stringliteral.json`, `DummyDll/` or `dump.cs` — and Python 3 for the bundled helper scripts.

## Usage

Install or copy this folder as a skill named `il2cpp-to-csharp-skill`, then ask the agent to restore one function at a time. The dispatcher will pick the backend from the environment you state:

```text
Use $il2cpp-to-csharp-skill to restore 0x180000000.
IDA Pro MCP is ready. The dnSpy-exported stub project from DummyDll/Assembly-CSharp.dll is at C:\path\to\DummyDllExport, and stringliteral.json is at C:\path\to\stringliteral.json.
```

```text
Use $il2cpp-to-csharp-skill to restore rva:0x123456.
Ghidra is ready. Project at /path/to/ghidra-projects/game, program UnityFramework, stringliteral.json at /path/to/stringliteral.json.
```

## Repository Layout

```
SKILL.md               Dispatcher: backend selection + shared rules (start here)
ida/                   IDA backend (original skill, unmodified)
  SKILL.md             IDA workflow: ida-usage.md, ida-quirks.md, strings.md,
                       helpers.md, compiler-patterns.md, scripts/
ghidra/                Ghidra backend (custom skill, unmodified)
  SKILL.md             Ghidra workflow: ghidra-setup.md, ghidra-query.md,
                       ghidra-quirks.md, strings.md, helpers.md,
                       string-formatting.md, lambdas-closures.md, linq-generics.md,
                       coroutines.md, async.md, runtime-exceptions.md,
                       runtime-memory.md, scripts/, agents/
```

Each backend's `scripts/` tree is self-contained; run its scripts from within that backend's directory so relative references stay valid.

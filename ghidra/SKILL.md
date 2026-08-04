---
name: il2cpp-to-csharp
description: Reconstruct plausible C# from Unity IL2CPP methods using Ghidra and matching Il2CppDumper metadata. Use for method VA/RVA/name analysis, strings, vtables, compiler-generated lambdas, LINQ, coroutine or async state machines, and IL2CPP runtime cleanup. Do not use for Mono/.NET assemblies, generic native decompilation, or exploit development.
---

# Restore IL2CPP Methods to C#

Reconstruct each requested method from complete Ghidra control-flow evidence and metadata from the same binary build.

## Evidence Rules

- Treat complete decompiler C as the primary control-flow evidence. Preserve conditions, shared branches, call order, returns, and side effects before cleaning runtime machinery into C#.
- Use assembly only to verify a thunk, trivial folded body, field offset, or decompiler anomaly.
- Confirm names, signatures, fields, enum values, generics, and attributes with matching `DummyDll`, `dump.cs`, `script.json`, and imported `*_Fields` types.
- Resolve strings only through matching `stringliteral.json` data.
- Mark uncertainty explicitly. Never invent a missing branch, identifier, literal, enum label, or source intent.

## Inputs and Setup

Confirm that the native image and Il2CppDumper output belong to the same build. For a new project, locate the native image, `script.json`, and `DummyDll` or `dump.cs`. Locate `stringliteral.json` only when strings occur and `global-metadata.dat` only when raw metadata is required. Verify that an App Store Mach-O image is decrypted before analysis.

- Read [ghidra-setup.md](ghidra-setup.md) only to create a project, import the image, or apply symbols and signatures.
- Read [ghidra-query.md](ghidra-query.md) for wrapper actions, batch syntax, address coordinates, GUI equivalents, or query failures.

## Query Workflow

Use `scripts/ghidra_query.py` for routine read-only queries:

```bash
python3 scripts/ghidra_query.py query \
  --project-location /path/to/projects \
  --project-name game \
  --program UnityFramework \
  decompile rva:0x123456
```

Use `va:0x...`, `rva:0x...`, or `name:Exact.Symbol` selectors and quote shell-sensitive names. Run the script with `--help` for current options.

1. Map a method name with `scripts/query_script_json.py` when needed.
2. Query `info` when ownership, aliases, ICF folding, or address coordinates are uncertain.
3. Choose `--timeout` from the method's scale, decompile the target, and verify `complete: true`. Use the default for ordinary methods and several minutes for a large dispatcher, coroutine, or async state machine; raise `--process-timeout` with it when needed.
4. Inspect strings, computed calls, enum cascades, delegate targets, and helpers visible in the body.
5. Decompile every helper that changes a condition, result, or side effect.
6. Reconstruct C# and retain metadata attributes from any supplied stub.

The wrapper emits complete decompiler C regardless of size and also saves it as `decompile.c`. If `--no-inline` was explicitly requested, run `read` without a selector to emit the complete artifact. Use block indexes and call lists only for navigation, and inspect every behavior-relevant branch before reconstructing.

Treat independent requested methods as separate reconstructions. Batch only an exact helper set already discovered from one reconstruction, and inspect each saved body. For a dispatcher or state machine, restore the outer skeleton before its helpers.

## Conditional References

- Read [strings.md](strings.md) for `StringLiteral_N`; then read [string-formatting.md](string-formatting.md) only for concat, format, boxing, or interpolation lowering.
- Read [lambdas-closures.md](lambdas-closures.md) for `__c`, `b__`, `DisplayClass`, and `g__` helpers.
- Read [linq-generics.md](linq-generics.md) for LINQ or shared generic bodies.
- Read [coroutines.md](coroutines.md) for iterators and boolean `MoveNext` state machines.
- Read [async.md](async.md) for awaiters, builders, `Task`, and `UniTask` state machines.
- Read [helpers.md](helpers.md) when an unlabeled `FUN_...` may be IL2CPP machinery. Follow its routing to [runtime-memory.md](runtime-memory.md) or [runtime-exceptions.md](runtime-exceptions.md) only after classification.
- Read [ghidra-quirks.md](ghidra-quirks.md) only for address drift, ICF, thunks, field-layout noise, generic structure drift, offcuts, or decompiler type problems.

## Reconstruction Rules

- Map switches and subtraction cascades against explicit stub enum values. Merge branches only when the decompiler shows shared control flow or fallthrough.
- Map virtual calls from imported types or method order and confirm the candidate signature in the stub. A missing direct-callee edge does not exclude a computed call.
- Decompile referenced lambda, local-function, and `MoveNext` bodies. Restore LINQ, `yield`, or `await` only from their complete data flow and state transitions.
- Remove allocation plumbing, class-init guards, GC barriers, boxing, automatic exception helpers, builders, and runner promises only after positive identification. Preserve application logic.
- At an ICF-folded address, inspect aliases and restore the requested member using its own stub. Confirm pure accessors with a field offset. Restore standard delegate compare-exchange loops as events.

## Failure Handling

1. Retry an incomplete decompile once with a timeout materially larger than the first attempt. Scale it to the function size rather than treating the default as a fixed ceiling.
2. Query `info`, then check for a thunk, offcut, wrong image base, stale project, encryption, or mismatched dump. Use disassembly for diagnosis.
3. If the result remains incomplete, obtain the complete body from the GUI Decompiler.

Never reconstruct a complex method from partial C, call lists, or assembly guesses.

## Integrity Rules

- Do not introduce behavior, error handling, or source code unsupported by evidence. Report unresolved details instead of filling them with guessed C#.
- Do not remove `[Token]`, `[Address]`, `[FieldOffset]`, `[CompilerGenerated]`, or other metadata attributes from a supplied stub.
- Do not infer original source paths from native project metadata.

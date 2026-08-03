# Runtime Helper Router

Use this index when an unlabeled `FUN_...` may be IL2CPP infrastructure. Decompile the helper and match several independent signals; names, addresses, or argument count alone are insufficient.

## Identification Workflow

1. Inspect the caller branch, argument roles, return use, and whether the call returns.
2. Decompile the helper with `scripts/ghidra_query.py query ... decompile`.
3. Follow thunks only until behavior becomes identifiable.
4. Classify the helper with the table below.
5. Remove it only when positively identified as automatic runtime machinery.

| Signals | Likely category | Read |
|---|---|---|
| Field address, card-table bits, interlocked update | GC write barrier | [runtime-memory.md](runtime-memory.md) |
| TypeInfo, instance size, GC allocation | Object allocation | [runtime-memory.md](runtime-memory.md) |
| TypeInfo plus length, `il2cpp_array_new_specific` | Array allocation | [runtime-memory.md](runtime-memory.md) |
| TypeInfo before static access, initialization states | Type/class initialization | [runtime-memory.md](runtime-memory.md) |
| TypeInfo plus value address, `il2cpp_value_box` | Boxing | [runtime-memory.md](runtime-memory.md) |
| Non-returning helper after null or bounds check | Automatic exception | [runtime-exceptions.md](runtime-exceptions.md) |
| Assignability/interface test returning object or null | `is` / `as` type check | [runtime-exceptions.md](runtime-exceptions.md) |
| Failed class check followed by non-returning throw | Invalid cast | [runtime-exceptions.md](runtime-exceptions.md) |
| Array covariance check and shared throw path | Array type mismatch | [runtime-exceptions.md](runtime-exceptions.md) |

## Decision Rule

Remove allocation plumbing, barriers, automatic type initialization, boxing, and automatic exception transport only after classification. Restore the corresponding C# operation.

Preserve the helper or decompile deeper when it:

- reads or writes application fields;
- performs domain calculations or string manipulation;
- invokes application callbacks;
- contains source-visible cleanup, logging, or custom exception behavior;
- only partially resembles a catalog entry.

`Il2CppExceptionWrapper`, `_Interlocked*`, or an `il2cpp_*` call is supporting evidence, not permission to delete the whole helper.

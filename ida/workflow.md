---
name: il2cpp-to-csharp
description: Analyze Unity IL2CPP game binaries through IDA Pro MCP and reconstruct plausible C# source from user-provided VAs or function names. Use this for IL2CPP Unity reverse engineering workflows that require string literal resolution, vtable mapping, switch/enum cascade recovery, lambda/closure reconstruction, LINQ recovery, coroutine/async state machines, and IL2CPP runtime helper cleanup. Do not use it for generic decompilation, non-IL2CPP .NET binaries, or exploit development.
---

# IL2CPP to C# Source Restoration

Use IDA Pro MCP to analyze Unity IL2CPP binaries from user-provided VAs or function names and return reconstructed C# source.

**Note: all VAs, addresses, function names, class names, helper addresses, and other concrete identifiers in this skill are examples only. For real work, use the current game's IDA output and do not copy example values or names.**

## Core Principles

**IDA pseudo-C is the trusted primary input for source restoration.** The most common failures are invented string contents, inverted conditions, merged switch branches, and "more reasonable" rewrites that are not in IDA. Match the structure of IDA pseudo-C first; only clean it into natural C# after correctness is established.

If `decompile_function` output is truncated, missing its end, or clearly not the full function body, pause source restoration and ask the user to manually decompile the function in IDA Pro and paste the complete pseudo-C. Do not fill truncated regions from context.

Unless the user explicitly provides assembly and asks for assembly-based recovery, do not use assembly as the main reference for normal method restoration. Assembly may be used only for narrow local checks, such as trivial ICF bodies, field-offset noise, or a single object offset that pseudo-C cannot confirm directly. Confirm field names, signatures, enum values, and `[FieldOffset]` with dnSpy / DummyDll stubs, `*_Fields` structures, and `stringliteral.json`.

## Preparation

Before analyzing a function, confirm that the user has already prepared an analyzed IDA database and working IDA Pro MCP tools. Ideally, the user should also provide a dnSpy-exported C# stub project.

### Il2CppDumper Output

Ask the user to locate the main game assembly and metadata files, for example:

- Windows Unity IL2CPP: `GameAssembly.dll`
- Unity metadata: `global-metadata.dat`

Ask the user to process these files with Il2CppDumper and keep:

- `script.json`: method addresses, type information, and metadata mappings
- `stringliteral.json`: real values for `StringLiteral_N`; the user must provide the local path explicitly
- `DummyDll/`: C# type, field, method signature, and VA comment stubs

### IDA Pro Database

Ask the user to decompile the main assembly in IDA Pro, such as `GameAssembly.dll`, and wait for IDA's initial analysis to finish. After analysis, ask the user to run Il2CppDumper's `ida_with_struct_py3` script on the current IDA database.

After the script has run, if the project is large or the analysis will continue for a long time, suggest that the user back up the IDA database before renaming or doing experimental changes.

### IDA Pro MCP

Ask the user to install and enable the IDA Pro MCP plugin so the agent can:

- query and decompile functions
- view assembly for local checks
- query callees and xrefs
- query globals
- inspect structures and fields

Before real analysis, check that the MCP connection works. If MCP is unavailable, pause and ask the user to fix the plugin connection.

### DummyDll Stub Project

Recommend that the user open Il2CppDumper's `DummyDll/Assembly-CSharp.dll` in dnSpy and export it as a local C# project. The DLL contains only stubs, but it is important for source restoration:

- class, namespace, and method signatures
- field names and `[FieldOffset(...)]`
- method VA / RVA comments
- enum definitions and explicit enum values
- auto-properties, events, generic types, and inheritance

If the user does not provide this project, restoration can continue with IDA and Il2CppDumper outputs, but note any uncertainty around fields, enums, or signatures.

## Basic Workflow

1. The user provides a VA or function name.
2. Use `get_function_by_address(VA)` or `get_function_by_name(name)` to confirm the function and detect compiler folding.
3. Use `decompile_function(VA)` to get pseudo-C and check that it is complete. If it is truncated, ask the user to paste the full pseudo-C from IDA.
4. Resolve string literals, switch cascades, vtable calls, lambdas, closures, and other patterns using the sections below.
5. Remove IL2CPP runtime helper noise.
6. Return reconstructed C# source.

Analyze one function at a time. If the user gives multiple VAs, process them one by one and return each result before continuing.

## String Literal Resolution

See [strings.md](strings.md). For normal C# source restoration, do not search for strings as an entry point; only resolve `StringLiteral_N` values that already appear in the current decompile. Prefer `../scripts/lookup_strings.py` against the user-provided `stringliteral.json`. **Never invent string contents from context.**

String content search is an audit-only technique. Common case: traffic capture reveals part of an API route, and you need to locate the client logic for that route. Search the user-provided `stringliteral.json` directly, then use the matched RVA/address to locate the exact IDA global/xref and continue with targeted decompile. Do not use IDA string search.

## Switch / Enum Cascade Recovery

IDA often lowers `switch` into nested subtraction patterns:

```c
if (v) {                 // != 0
    v2 = v - 1;
    if (v2) {            // != 1
        v3 = v2 - 1;
        if (v3) { ... }  // != 2
        // body for v == 2
    }
    // body for v == 1
}
// body for v == 0 (fallthrough)
```

Mapping steps:

1. If the user provides the enum definition from the dump, map against the real explicit values.
2. Compare behavior in each branch: vtable slots, return values, and side effects.
3. **Do not** merge branches unless IDA shows a shared basic block through `goto` or fallthrough.

## Vtable Call Resolution

Common form: `obj->klass->vtable._N_unknown.methodPtr(obj, ...)`.

Slot `N` starts with base-class virtual methods, then methods declared by the current class or abstract methods in source order.

Resolution:

1. Look for IDA-preserved names such as `vtable._8_OnGetGuestName`.
2. If Il2CppDumper method lists are available, compute the virtual slot mapping.
3. For common helpers inlined into several vtable calls, restore the original high-level call.

## Lambda / Closure / LINQ / Local Functions

See [compiler-patterns.md](compiler-patterns.md). Core rules:

- `Type.__c` / `__9__N_M` usually indicate cached no-capture lambdas. Decompile the target `b__N_M` body.
- `DisplayClassN_M` is a closure object. Its fields are captured variables; `__4__this` captures outer `this`.
- `<Outer>g__Name|N_M` is a named local function. Prefer restoring it as a local function, not an anonymous lambda.
- For generic methods, keep the source-level generic shape from stubs and infer closed type arguments from call sites. Do not rewrite shared IL2CPP generic implementations as `object`.
- Recover LINQ chains by data flow: `Select` / `Where` / `Zip` produce sequences, while `ToArray` / `Sum` / `All` / `First` / `Aggregate` are materialization or terminal operations.
- Every selector or predicate must be decompiled. Do not guess conditions from `Func<T, bool>` or variable names.

## Large Methods and Compiler-Generated Helpers

When a method has these signals, analyze it as a dispatcher plus helpers:

- IDA pseudo-C is very long and clearly dispatches to helpers or repeated blocks.
- IDA MCP output is truncated. Ask the user to paste full pseudo-C before restoring the main body.
- The method allocates `DisplayClassN_M` or references `<Outer>b__N_M`, `<Outer>g__Helper|N_M`, or `_9__N_M`.
- The method has many repeated blocks that differ only in captured data or enum branch.

Strategy:

1. Restore the outer skeleton first: guards, loops, captured locals, and dispatcher / switch shape.
2. Map each branch to its enum value and helper target.
3. Analyze each helper body for captures, return values, and side effects.
4. Inline short single-use helpers as lambdas; keep shared or complex helpers as local functions.

For compiler-generated helper search, classification, and inlining, see [compiler-patterns.md](compiler-patterns.md).

## IL2CPP Runtime Helpers

See [helpers.md](helpers.md). When encountering a `sub_xxx` call, decompile the helper itself and compare it against the helper catalog. Remove runtime infrastructure such as exception throw helpers, GC write barriers, allocation helpers, and type-system helpers. Preserve helpers that contain real business logic.

## Compiler Folding: One VA, Many C# Methods

IL2CPP can merge semantically identical method bodies. If `get_function_by_address` returns an unrelated name and the body is tiny, usually under `0x20` bytes, it may be folded. Analyze the actual body, not the unrelated owner name.

Common folded bodies:

| Example VA | Body |
|---|---|
| `0x1803F20F0` | `return null;` |
| `0x18044FC00` | `return true;` |
| `0x1803EE500` | `{ }` |

## Coroutines and Async

`IEnumerator` and async methods usually wrap a state-machine type. To locate `MoveNext`:

- Use the wrapper's `jmp` target or `get_callees`.
- Use `list_globals_filter` to search MethodInfo globals for compiler-generated helpers, such as `Type.__c`, `DisplayClass7_0`, or `OnPostEnterSceneAsync_b__7`. IDA data comments usually expose helper implementation VAs.
- If `get_function_by_name` cannot find a helper, use `get_xrefs_to` on the corresponding `Method$...` global to confirm the owning `MoveNext`, then use nearby IDA data comments to obtain the real VA. Prefer this over `read_memory_bytes`.
- For simple one- or two-yield coroutines, infer from state-machine fields.
- For complex coroutines / async methods, first obtain the full `MoveNext` pseudo-C. If MCP output is truncated, ask the user to paste it.

For coroutine / async search entry points and state-machine principles, see [compiler-patterns.md](compiler-patterns.md) and [ida-quirks.md](ida-quirks.md). Complex state machines must not rely on truncated decompiler output. For `async` / `UniTask`, rebuild `await` from awaiter save / restore points in `MoveNext`; do not write builder, runnerPromise, or `AwaitUnsafeOnCompleted` scheduling details back to C#.

## Decompile Failure, Bad Output, or Truncation

For `local variable allocation has failed`, infinite loops, unrelated output, or obvious incompleteness:

1. Retry `decompile_function(VA)` once to rule out transient failure.
2. If output is truncated or incomplete, ask the user to manually copy the complete pseudo-C from IDA Pro.
3. `get_callees(VA)` may help confirm helper / runtime calls, but cannot replace the full method body.
4. Unless the user explicitly provides assembly, do not use assembly as the main basis for restoring full C#.

If IDA appears to hang through repeated timeouts, tell the user IDA may need to be restarted. Do not retry indefinitely.

## Auto-Properties and Events

Simple getters and setters are often folded into one shared binary body, such as every `return this._field` method. Verify by body shape, not by the function name returned by IDA.

Pure field getter assembly shape: `mov rax, [rcx+XX]` / `mov eax, [rcx+XX]` followed by `retn`. `XX` is usually object-relative. IL2CPP object headers are `0x10` bytes, so mapping to a `*_Fields` structure or C# stub `[FieldOffset]` usually uses `XX - 0x10`. If the current dump records `[FieldOffset]` as object-relative instead of Fields-relative, follow the current project's convention and cross-check with [ida-quirks.md](ida-quirks.md).

If a getter resolves to a folded shared body, restore it as a standard auto-property. Do not preserve an incorrect constant-return stub.

IDA pseudo-C expressions such as `BYTE4(Instance[40].monitor)`, `LOBYTE(instance[1].klass)`, or `*(_OWORD *)&instance[2].fields.X` are usually field-offset noise, not array access. When such expressions affect business logic, first use `../scripts/field_offset.py` to compute object and Fields offsets. Use assembly only as a single-offset local check if needed, then confirm the real field name with `*_Fields` or `[FieldOffset]`. See [ida-quirks.md](ida-quirks.md).

### Auto-Property Restoration Style

When a getter or setter is ICF-folded (shared binary body, no real logic), use the semicolon-terminated auto-property syntax and preserve **all** metadata attributes on each accessor. Do **not** use a brace block with `return null;` or `default(...)` for these accessors.

**ICF shared auto-property (getter and/or setter have no real logic):**

```csharp
public SomeType PropertyName
{
    [Token(Token = "0x6000001")]
    [Address(RVA = "0x3F9450", Offset = "0x3F7E50", VA = "0x1803F9450")]
    [CompilerGenerated]
    get; // By <Model>
    [Token(Token = "0x6000002")]
    [Address(RVA = "0x3FC090", Offset = "0x3FAA90", VA = "0x1803FC090")]
    [CompilerGenerated]
    private set; // By <Model>
}
```

**Auto-property with real logic in one or both accessors:**

```csharp
public SomeType PropertyName
{
    [Token(Token = "0x6000001")]
    [Address(RVA = "0x636F60", Offset = "0x635960", VA = "0x180636F60")]
    [CompilerGenerated]
    get; // By <Model>
    [Token(Token = "0x6000002")]
    [Address(RVA = "0x6388D0", Offset = "0x6372D0", VA = "0x1806388D0")]
    set
    {
        // By <Model>
        _backingField = value;
        SomeCallback?.Invoke(value);
    }
}
```

Key rules:

- The model signature (`// By <Model>`) goes **after** the semicolon for `get;` / `set;`, and **inside** the brace block for accessors with logic.
- `[CompilerGenerated]` is kept on every accessor that had it in the stub.
- `private set;` / `protected set;` retains its access modifier as declared in the stub.

Event add/remove pattern:

```c
do { ... = Delegate.Combine(old, new); ... } while (Interlocked.CompareExchange(...) != old);
```

This is the standard thread-safe lowering for `event +=` / `-=`. Restore it as a C# `event`.

## Common Failure Modes

| Category | Wrong | Correct |
|---|---|---|
| Strings | Invent `"starts generating order."` | Resolve `" Order Session"` |
| Conditions | `a || b` | `!a && b` |
| Scope | Put a block inside `if/else` | Place it after the `if/else` |
| Enum branches | Assume declaration order equals value | Check explicit values in the dump |
| Switch merging | Merge `NoMoney` and `ExceedEndurance` | Keep each branch separate |
| Formatting args | `$"{name} ({type})"` | Preserve the `il2cpp_value_box` argument order |
| Helper inlining | Keep `vtable._10` and `vtable._9` as separate low-level calls | Recombine into the high-level method |

## Prohibited

- **Do not** invent string literal contents.
- **Do not** merge switch branches unless IDA shows a shared basic block.
- **Do not** add error handling, comments, or features not present in IDA output.
- **Do not** remove metadata attributes (`[Token]`, `[Address]`, `[FieldOffset]`, `[CompilerGenerated]`, `[CleanupIgnore]`, etc.) from any method, property, or accessor. If structural changes require removing an attribute from its original position (e.g., converting a brace block to a semicolon accessor), the attribute **must** be preserved in its new syntactically valid position. If this is impossible, preserve the attribute data as a comment above the affected element.

IDA MCP tool rules, see [ida-usage.md](ida-usage.md):

- **Do not** use `list_functions`, `list_strings`, `list_strings_filter`, or `list_globals`.
- **Do not** call `get_callers` on `sub_xxx` functions.
- **Do not** use `get_metadata` to locate original source file paths.

## Supporting Files

- [helpers.md](helpers.md) - IL2CPP runtime helper catalog: decompile signatures, call patterns, recognition points, and C# treatment.
- [ida-usage.md](ida-usage.md) - IDA MCP usage manual: prohibited tools, recommended alternatives, search strategies, timeout handling, and quick reference.
- [strings.md](strings.md) - String literal handling: `StringLiteral_N` resolution, RVA calculation, `stringliteral.json` lookup, concatenation / formatting translation, and failure handling.
- [../scripts/lookup_strings.py](../scripts/lookup_strings.py) - Standard-library Python tool for resolving `StringLiteral_N`, RVA, or VA values against user-provided `stringliteral.json`.
- [../scripts/field_offset.py](../scripts/field_offset.py) - Standard-library Python tool for converting IDA pseudo-C noise such as `BYTE4(Instance[40].monitor)` into object and Fields offsets.
- [compiler-patterns.md](compiler-patterns.md) - Compiler-generated pattern recovery: lambdas, DisplayClass closures, generic methods, LINQ chains, named local functions, coroutine / iterator / async state machines.
- [ida-quirks.md](ida-quirks.md) - IDA / Il2CppDumper structural quirks: Color32 explicit-layout imported as 8 bytes, generic base offset drift, pseudo-array field-offset noise, async MoveNext jump decoding.

# IDA MCP Usage for IL2CPP Reverse Engineering

Rules for using IDA Pro MCP tools during IL2CPP reverse engineering. This document defines prohibited tools, reasons, and preferred alternatives.

**Note: all VAs, function names, class names, and search examples in this document are game-specific examples for methodology only. For real work, use the current game's IDA output and do not copy example values or names.**

---

## 1. Prohibited MCP Tools

The following tools must not be used in normal work. Violating these rules can overflow context, hang IDA, or produce useless results.

### 1.1 Large Unfiltered Listings

| Prohibited Tool | Reason |
|---|---|
| `list_strings` | Huge output; IL2CPP binaries often contain tens of thousands of strings |
| `list_strings_filter` | Same traversal cost as `list_strings`; can time out on large games. Exception: user explicitly accepts a potentially long wait |
| `list_functions` | Filtering is ignored in this MCP build; it starts from address 0 and can overflow context |
| `list_globals` | Huge output with no filter mechanism |

**Alternatives:**

- Need a global variable: use `list_globals_filter` with a partial name of at least 4 characters.
- Need a function: use `get_function_by_address` with an exact VA or `get_function_by_name` with an exact name. If exact name lookup fails, search `Method$...` globals with `list_globals_filter` using a unique function-name fragment.
- Need a string: see [strings.md](strings.md). Use `list_strings_filter` only if the user explicitly accepts the likely long wait.

### 1.2 `get_callers` on `sub_xxx` Functions

`sub_xxx` is an IDA-generated name with no symbol information. These functions are usually:

- IL2CPP runtime helpers, see [helpers.md](helpers.md)
- compiler-folded stubs
- very common small utility functions

**Do not call `get_callers` on `sub_xxx` functions.**

Reasons:

- Runtime helpers may have thousands of callers across the binary.
- Folded functions such as `return null` and `return true` also have huge caller lists.
- The caller list is rarely useful for source restoration.

**Exception:** use `get_callers` only when the function is confirmed to be a user-defined named function, not `sub_`, and the expected caller count is manageable.

### 1.3 Using `get_metadata` to Locate Source Files

`get_metadata` may be used to obtain the image base for RVA calculations.
**Do not** use `get_metadata` to infer or locate original C# source file paths.

IDA metadata does not contain original IL2CPP source paths. Use Il2CppDumper dump files such as `dump.cs` or `script.json` to understand class and namespace ownership.

### 1.4 Parsing Raw MethodInfo / `Method$` Memory

`Method$...` globals are metadata anchors for names and xrefs. They are not a stable API for recovering implementation VAs.

**Do not** use `read_memory_bytes`, `data_read_qword`, or other raw data reads on `Method$...`, MethodInfo, or TypeInfo objects to search for lambda / predicate / local-function / `MoveNext` implementation pointers.

Reasons:

- The layout is runtime-version dependent and may be relocated, encoded, or point to metadata rather than executable code.
- Raw bytes do not identify which pointer is the implementation.
- Guessing from MethodInfo memory is less reliable than IDA's existing function names, xrefs, and Il2CppDumper comments.

Correct treatment:

- Use `Method$...` names to derive an IDA function name.
- Prefer DummyDll stubs or `script.json` for compiler-generated helper RVA / VA lookup when name conversion fails.
- Use `get_xrefs_to(Method$_VA)` to find owners, delegate construction sites, or nearby commented data items.
- If no function VA can be found and the helper semantics matter, ask the user for the helper VA or complete pseudo-C.

---

## 2. Recommended MCP Tools

### 2.1 Core Analysis Tools

| Tool | Purpose | Notes |
|---|---|---|
| `get_function_by_address(VA)` | Query a function by exact VA | Preferred when VA comes from the user or dump |
| `get_function_by_name(name)` | Query a function by exact name | Name must be complete and accurate |
| `decompile_function(VA)` | Decompile a function to pseudo-C | Use one function at a time |
| `disassemble_function(VA)` | Read assembly | Local checks only; unless the user explicitly provides assembly, do not use it as the primary restoration basis |
| `get_callees(VA)` | List callees | Useful for confirming helper / runtime calls; usually bounded |

### 2.2 Auxiliary Query Tools

| Tool | Purpose | Notes |
|---|---|---|
| `get_callers(VA)` | List callers | Only for confirmed named functions; assess output size first |
| `get_xrefs_to(VA)` | Get xrefs | Useful for global references and MethodInfo anchors; do not parse raw MethodInfo memory |
| `list_globals_filter(filter)` | Search globals by fragment | Filter must be at least 4 characters |
| `get_current_address()` | Get current cursor address | Useful for user-guided sessions |
| `get_current_function()` | Get current cursor function | Useful for user-guided sessions |

### 2.3 Data Read Tools

| Tool | Purpose | Notes |
|---|---|---|
| `read_memory_bytes(addr, size)` | Read raw bytes | Last resort for fixed data only; never use it to parse MethodInfo / `Method$` / TypeInfo objects |
| `data_read_string(addr)` | Read one string at an address | Point reads only; no bulk enumeration |
| `data_read_byte/dword/qword/word(addr)` | Read one numeric value | Point reads only; not for MethodInfo pointer hunting |

---

## 3. Search Strategy

### 3.1 Finding Functions

```text
Priority 1: get_function_by_address(VA)       <- exact VA available
Priority 2: get_function_by_name(full name)   <- exact IDA function name available
Priority 3: DummyDll / script.json RVA lookup <- best fallback for compiler-generated helpers
Priority 4: list_globals_filter(fragment)     <- search Method$ globals, e.g. "PostEvaluation"
Priority 5: get_xrefs_to(Method$_VA)          <- find owners / delegate construction / nearby comments
```

### 3.2 Finding Helpers / MoveNext

For compiler-generated helper functions in coroutine / async state machines, such as `<Outer>g__Helper|N_M` or `<Outer>b__N_M`:

1. Search short fragments with `list_globals_filter`, such as `Type.__c`, `DisplayClass7_0`, or `OnPostEnterSceneAsync_b__7`.
2. If a matching `Method$...` global is found, treat it as a name anchor only.
3. Look up the same compiler-generated method in the dnSpy-exported DummyDll C# stubs or `script.json`; use the RVA / VA comment if present.
4. If a likely IDA function name is known, try `get_function_by_name`.
5. If only a `Method$...` VA is known, use `get_xrefs_to` to find the owner or nearby commented data; do not expect the xref itself to be the helper.
6. Decompile the found helper VA directly with `decompile_function(VA)`.
7. If no function VA is exposed, ask the user for the helper VA or complete pseudo-C. Do not read raw MethodInfo bytes to guess it.

### 3.3 String Resolution

**Never query string contents directly through IDA bulk string tools.** See [strings.md](strings.md).

### 3.4 Special Characters and IDA Naming

C# names containing special characters, such as `<`, `>`, `$`, and `.`, are rewritten differently depending on whether you query a function name or a `Method$` global.

#### Function Names: `get_function_by_name` / `get_function_by_address`

| Original | In IDA Function Name | Notes |
|---|---|---|
| `.` | `.` | Preserved |
| `<` | `_` | Single underscore |
| `>` | `_` | Single underscore |
| `$` | `$` | Preserved |

Example:

```text
C# name:  Common.LoadingSceneManager.<MainLoadingCycle>d__67.MoveNext
IDA name: Common.LoadingSceneManager._MainLoadingCycle_d__67$$MoveNext
```

#### `Method$` Globals: `list_globals_filter`

| Original | In `Method$` | Notes |
|---|---|---|
| `.` | `.` | Preserved |
| `<` | `_` | Single underscore |
| `>` | `_` | Single underscore |
| `$` | `_` | Converted to underscore, unlike function names |

Example:

```text
C# name: Common.LoadingSceneManager.<>c.<MainLoadingCycle>b__67_0
Method$: Method$Common.LoadingSceneManager.__c._MainLoadingCycle_b__67_0()
```

#### Inferring Function Names from `Method$` Globals

Some `Method$...` names can be converted to IDA function names, but this is a heuristic. Prefer a VA / RVA from DummyDll stubs or `script.json` when available.

| `Method$` Global | IDA Function Name |
|---|---|
| `Method$Foo.__c._Bar_b__N_M()` | `Foo.__c$$_Bar_b__N_M` |
| `Method$Foo.__c__DisplayClassX_Y._Bar_b__N()` | `Foo.__c__DisplayClassX_Y$$_Bar_b__N` |
| `Method$...Start_Foo._Bar_d__N_()` | `Foo._Bar_d__N$$MoveNext` |

Heuristic: remove the `Method$` prefix and trailing `()`, then insert `$$` between the owning type and method part. If it fails, do not keep inventing name variants; move to DummyDll / `script.json` lookup or ask the user.

#### Search Recommendations

1. Search unique fragments first, such as `MainLoadingCycle`, `DisplayClass30`, or `OnCustomEventEnd`.
2. For `list_globals_filter`, replace `<`, `>`, and `$` with `_`; keep `.` and alphanumerics.
3. For `get_function_by_name`, use exact names where `<` and `>` become `_`, while `.` and `$` remain.
4. For compiler-generated helpers, check DummyDll stubs / `script.json` for RVA / VA before trying broad IDA searches.
5. Fallback: use xrefs from known anchors such as `StringLiteral` or `Method$` globals.
6. For coroutine / local function TypeInfo lookup, if the `MoveNext` name is unknown, xref `..._d_TypeInfo`; owner functions often reveal IDA's nested-type spelling.
7. If a `Method$` global is found but no function name / VA can be derived, ask the user for the helper location. Do not inspect raw MethodInfo memory for implementation pointers.

#### DisplayClass / Lambda Caller Notes

`get_callers` often returns call-site addresses rather than function starts. Passing that address to `decompile_function` usually makes IDA move back to the real function start and expose the full nested helper name. Do not switch to assembly as the primary restoration material because of this.

Tail-call closures of the form `jmp SomeMethod` may not appear in `get_callers(SomeMethod)`. If the expected `b__N` is missing, try one likely `get_function_by_name` form such as `Type.__c__DisplayClassX_Y$$_Method_b__N`. If that fails, return to DummyDll / `script.json` RVA lookup or ask the user for the helper; do not keep trying guessed names.

---

## 4. IDA Output Problems

### 4.1 Hangs / Timeouts

When IDA times out repeatedly on small functions:

1. First timeout: wait 5 seconds and retry once.
2. Second timeout: tell the user IDA may be hung and ask them to restart IDA before continuing.
3. Never retry indefinitely.

### 4.2 Truncated Output

`decompile_function` may truncate large functions, leaving incomplete pseudo-C or missing the end.

Handling:

- Ask the user to manually copy the complete decompiler output from IDA Pro.
- Provide the VA and name for easy navigation: `Please manually copy the IDA pseudo-C for <function name> (VA: <address>).`
- **Never** invent missing truncated content or guess it from context.
- `get_callees` may list helper / runtime calls, but it cannot replace complete pseudo-C.
- Unless the user explicitly provides assembly and asks for assembly-based recovery, do not switch to assembly as the main material.

---

## 5. Quick Reference

| Scenario | Do Not Use | Use |
|---|---|---|
| Find function | `list_functions` | `get_function_by_address(VA)` or `list_globals_filter("fragment")` |
| Find global | `list_globals` | `list_globals_filter("fragment")` |
| Find string | `list_strings` | `list_globals_filter` + RVA calculation + `stringliteral.json` |
| `sub_xxx` callers | `get_callers(sub_xxx)` | Do not need callers; decompile the helper body if needed |
| Locate source file | `get_metadata` path guesses | Il2CppDumper dump files |
| Decompile | - | `decompile_function(VA)` |
| Decompile failure / truncation | Fill missing source from assembly | Retry `decompile_function`; if still failed or truncated, ask user for complete pseudo-C |

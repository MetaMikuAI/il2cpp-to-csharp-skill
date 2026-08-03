# IL2CPP String Literal Handling

Rules for recognizing, resolving, translating, and handling failures for `StringLiteral_N`.
This covers how strings appear in IDA, the resolution workflow, C# translation style, and what
to do when a string cannot be resolved.

**Note: all VAs, image bases, RVAs, `StringLiteral_N` ids, and string values in this document are examples only. For real work, use the current game's IDA output and `stringliteral.json`.**

---

## 1. How `StringLiteral_N` Appears in IDA

IL2CPP-compiled strings appear as globals named `StringLiteral_N`.
Decompiler output refers to them directly, for example `StringLiteral_8179`.

Each `StringLiteral_N` stores a string handle in `.data`. IDA often shows the actual
string value as a data-line comment:

```text
.data:0000000184222200 StringLiteral_8179 dq 0A0002AA5h  ; Game Asset Loading: Load IzakayaMusicPackage
```

## 2. Resolution Workflow

Normal restoration does not use string search as discovery. Resolve only `StringLiteral_N`
values already present in the function being restored. Broad string-content search is for
reverse-engineering audits, such as finding API routes or protocol keys.

### 2.1 Preferred: Use the Lookup Script

This skill includes `scripts/lookup_strings.py`. The user must provide the path to
Il2CppDumper's `stringliteral.json`; the script intentionally has no project-specific default path.

Common usage:

```bash
python scripts/lookup_strings.py --json-path /path/to/stringliteral.json StringLiteral_8179
python scripts/lookup_strings.py --json-path /path/to/stringliteral.json 8179 17614
python scripts/lookup_strings.py --json-path /path/to/stringliteral.json --rva 0x4222200
python scripts/lookup_strings.py --json-path /path/to/stringliteral.json --base 0x180000000 --va 0x184222200
```

Environment variables can reduce repeated arguments:

```bash
IL2CPP_STRINGLITERAL_JSON=/path/to/stringliteral.json \
python scripts/lookup_strings.py StringLiteral_8179
```

PowerShell:

```powershell
$env:IL2CPP_STRINGLITERAL_JSON = "C:\path\to\stringliteral.json"
python scripts\lookup_strings.py StringLiteral_8179
```

Batch extraction from decompiler text:

```bash
python scripts/lookup_strings.py --json-path /path/to/stringliteral.json --from-file decompile.txt
```

### 2.2 Audit-only: Search JSON, Then Return to IDA

When an audit needs string clues, search the user-provided `stringliteral.json` directly
for the string value. A common case is starting from a route fragment learned through
traffic capture and locating the client logic that builds or calls that API. Do not use
IDA string search.

Workflow:

1. Search `stringliteral.json` for the value or route fragment, such as a captured API path.
2. Read the matched `address` field; it is an RVA.
3. Convert to VA if needed: `VA = image_base + RVA`.
4. In IDA, locate the exact `StringLiteral_N` global or use xrefs to that VA.
5. Decompile only the referenced function(s).

This is for audit/discovery work only. For routine source restoration, start from the user-provided
VA/function and resolve only literals already visible in that decompile.

### 2.3 Conservative: VA to RVA to JSON

If you need to verify whether `StringLiteral_N` matches JSON order, or if label lookup fails,
use the RVA path through IDA MCP:

| Step | Tool | Notes |
|---|---|---|
| 1 | `list_globals_filter("StringLiteral_N")` | Search by id to locate the global VA, such as `0x184222200` |
| 2 | `get_metadata` | Get image base, such as `0x180000000` |
| 3 | Calculate RVA | `RVA = VA - base`, such as `0x4222200` |
| 4 | `scripts/lookup_strings.py --rva` | Query the user-provided JSON by `"address"` |

### 2.4 `stringliteral.json` Format

Il2CppDumper's string table dump is usually a JSON array:

```json
[
  {"value": "Key Agreement", "address": "0x41D5A90"},
  {"value": "Game Asset Loading: Load IzakayaMusicPackage", "address": "0x4222200"}
]
```

`address` is an RVA hex string, and `value` is the real string content.
In common Il2CppDumper output, `StringLiteral_N` usually maps to the Nth JSON entry
using 1-based indexing, so the script supports direct `StringLiteral_N` lookup.
If a project does not follow this convention, prefer RVA lookup.

### 2.5 Example

For `StringLiteral_8179`:

```text
list_globals_filter("StringLiteral_8179") -> VA 0x184222200
get_metadata                              -> base 0x180000000
RVA = 0x184222200 - 0x180000000           -> 0x4222200
python scripts/lookup_strings.py --rva 0x4222200
                                          -> "Game Asset Loading: Load IzakayaMusicPackage"
```

## 3. C# Translation Rules

### 3.1 Concatenation and Formatting

| IDA Call | C# Translation |
|---|---|
| `String.Concat(a, b)` with 2 args | `$"{a}{b}"` or `a + b` |
| `String.Concat(a, b, c, d)` with 4 args | Usually compiler-lowered string interpolation `$"...{x}...{y}..."` |
| `String.Format(fmt, arg0, arg1)` | `$"...{arg0}...{arg1}..."` |

### 3.2 `String.Format` Argument Order

The argument order for `String.Format` comes from the order of `il2cpp_value_box(TypeInfo, &field)`
calls in IDA. The first boxed value maps to `{0}`, the next maps to `{1}`, and so on.
The format string reveals placeholder intent; do not reorder arguments based on what seems
semantically nicer.

Example: if IDA boxes `name` first and `type` second, `{0}` maps to `name` and `{1}` maps to `type`.

When restoring `String.Format`, prefer numeric placeholders as interpolated strings instead of
leaving `String.Format`:

```csharp
// IDA / IL2CPP semantics
String.Format("{0} {1}", value1, num2)

// Preferred restoration
$"{value1} {num2}"
```

If the format string has repeated placeholders, reordered placeholders, format specifiers, or escaped
braces, interpolation is still acceptable, but preserve the exact semantics:

```csharp
String.Format("{1}: {0:0.00}", value, label)
// restore as
$"{label}: {value:0.00}"
```

Never change the `{0}` / `{1}` mapping just to make variable names feel more natural.

### 3.3 Style

- Prefer interpolation `$"{a}{b}"` over `String.Format` or `String.Concat`.
- `il2cpp_value_box` is only boxing for `String.Format`; it disappears naturally after interpolation.
- For common `"{0} {1}"` formats, prefer `$"{value1} {num2}"` style interpolation.
- Keep `String.Format` only when interpolation would clearly reduce readability or when the format string is dynamic.

## 4. Failure Handling

### 4.1 When `stringliteral.json` Is Unavailable

If the user did not provide the `stringliteral.json` path, the string cannot be resolved.
Keep `"StringLiteral_N"` as a placeholder and do not invent content.

Example output:

```csharp
Debug.Log("StringLiteral_8179");  // unresolved: VA=0x184222200, RVA=0x4222200
```

This format clearly tells the user what remains unresolved and provides the data needed to resolve it manually.

### 4.2 Common Failure Modes

| Wrong | Correct |
|---|---|
| Invent `"starts generating order."` from context | Keep `"StringLiteral_N"` until resolved |
| Guess content from variable names | Run the resolution workflow or keep a placeholder |
| Replace `StringLiteral_N` with an empty string | Keep the `"StringLiteral_N"` placeholder |
| Generate AI-made log / debug strings | Always query `stringliteral.json`; experience shows AI-generated values are almost always wrong |

## 5. Additional Rules

- **Never** infer string contents from context, function names, or variable names.
- Resolve every `StringLiteral_N` that appears in decompiler output independently.
- Do not use string search during ordinary source restoration; it is an audit/discovery technique only.
- For audit string search, search `stringliteral.json`, then use the matched RVA/address to return to IDA.
- `StringLiteral_N` usually supports 1-based JSON order lookup. If the current dump does not, match by RVA.
- Do not search strings directly in IDA. `list_strings` and `list_strings_filter` are prohibited; see [ida-usage.md](ida-usage.md).

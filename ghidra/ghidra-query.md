# Bounded Ghidra Queries

Read this file for wrapper syntax, batch queries, address coordinates, GUI equivalents, or query failures. Use the current binary, project, and Il2CppDumper output.

## Contents

- [Query Wrapper](#query-wrapper)
- [Batch and Artifact Reads](#batch-and-artifact-reads)
- [Search Strategy](#search-strategy)
- [Address Coordinates](#address-coordinates)
- [Bounded Query Rules](#bounded-query-rules)
- [GUI Equivalents](#gui-equivalents)
- [Failure Handling](#failure-handling)

## Query Wrapper

Use the Python wrapper for routine read-only queries. It captures Ghidra logs and full results as artifacts while returning a compact summary:

```bash
python3 /path/to/skill/scripts/ghidra_query.py query \
  --project-location /path/to/ghidra-projects \
  --project-name game \
  --program UnityFramework \
  <action> <selector>
```

Selectors:

| Selector | Meaning |
|---|---|
| `va:0x100123456` | Loaded virtual address |
| `rva:0x123456` | Image-base-relative address |
| `name:Namespace.Type$$Method` | Exact imported Ghidra label |

Quote `name:` selectors containing `$`, `<`, `>`, spaces, or other shell-sensitive characters. Run `ghidra_query.py query --help` for current options.

Actions:

| Action | Use |
|---|---|
| `info` | Resolve address, aliases, bounds, and thunk status |
| `decompile` | Save complete C and return bounded evidence metadata |
| `callees` / `callers` | Inspect bounded direct call edges |
| `xrefs` | Inspect bounded references to an exact address |
| `disassemble` | Inspect a short instruction window for diagnosis |

For `decompile`, verify `complete: true` and use the reported `decompile.c` as the authoritative body. `index.json` and `semantic.tsv` are navigation aids, not replacements for reading relevant C. A missing direct callee does not exclude a vtable or function-pointer call.

Successful complete queries are cached. Use `--no-cache` for a fresh diagnostic run; failures and incomplete queries are not reused.

## Batch and Artifact Reads

Batch several exact helpers only after one outer method has identified them:

```bash
python3 /path/to/skill/scripts/ghidra_query.py batch \
  --project-location /path/to/ghidra-projects \
  --project-name game --program UnityFramework \
  decompile rva:0x111111 rva:0x222222
```

Do not use batch mode for discovery. Inspect every saved helper body separately.

Read large decompiles in bounded slices:

```bash
python3 /path/to/skill/scripts/ghidra_query.py read \
  /path/to/decompile.c --lines 1:120
python3 /path/to/skill/scripts/ghidra_query.py read \
  /path/to/decompile.c --around StringLiteral_123 --context 25
python3 /path/to/skill/scripts/ghidra_query.py read \
  --index /path/to/index.json --block B0002 --block-context 2
```

Block reads verify the indexed artifact before returning a bounded region. Continue until every behavior-relevant branch, continuation, and return path has been inspected.

Use raw `GhidraQuery.java` only to debug the wrapper or when the artifact path is inaccessible:

```bash
"$(brew --prefix ghidra)/libexec/support/analyzeHeadless" \
  /path/to/ghidra-projects game \
  -process UnityFramework -readOnly -noanalysis \
  -scriptPath /path/to/skill/scripts \
  -postScript GhidraQuery.java <action> <selector> [number]
```

## Search Strategy

Prefer metadata lookup before querying Ghidra:

```bash
python3 scripts/query_script_json.py \
  --json-path /path/to/script.json --contains ExampleMethod
python3 scripts/query_script_json.py \
  --json-path /path/to/script.json --rva 0x123456
```

Search in this order:

1. Exact user-provided VA or RVA.
2. Exact `ScriptMethod` name or address from `script.json`.
3. Unique MethodInfo or type fragment in `script.json` or `dump.cs`.
4. Bounded xrefs from exact imported metadata or string-literal labels.

Do not enumerate the whole function, symbol, string, or xref database to locate one method.

If an exact name fails, search `script.json` for a unique method fragment, query its RVA, and use `info` to inspect aliases. Do not trust the primary Ghidra name at an ICF-folded address.

For `b__`, `g__`, `DisplayClass`, and `_d__N.MoveNext` helpers, search metadata by the outer method and numeric suffix, then query the exact RVA. Use bounded xrefs only if ownership remains unclear.

## Address Coordinates

Il2CppDumper `script.json` addresses are normally RVAs. The importer adds the Ghidra image base:

```text
VA = image base + RVA
RVA = VA - image base
```

`GhidraQuery.java` performs this conversion for `rva:` selectors. Do not add the image base twice. Verify the current project instead of assuming common Mach-O or PE bases.

## Bounded Query Rules

- Decompile one function body per query; batch only a known helper set.
- Use `info` before calls or xrefs when ownership is uncertain.
- Do not request callers for `FUN_...` or known allocation, throw, class-init, or GC helpers.
- Keep caller, callee, and xref results bounded unless the user requests a deliberate audit.
- Use disassembly only for a local offset, thunk, ICF body, or decompiler sanity check.
- Resolve strings through `stringliteral.json`; do not bulk-list Ghidra strings.
- Use `-readOnly` for non-mutating raw Ghidra queries.

## GUI Equivalents

When headless output is incomplete or visual control flow matters:

- **Go To**: press `G` and enter the VA.
- **Symbol Tree / Search Program Text**: use an exact imported label.
- **Decompiler**: inspect and copy the complete function C.
- **References > Show References To**: inspect exact xrefs.
- **Function Call Trees**: perform bounded caller/callee exploration.
- **Data Type Manager**: inspect imported `*_Fields` structures.
- **Script Manager**: add the skill `scripts/` path and run the Java scripts.

## Failure Handling

For a decompiler timeout or failure:

1. Retry once with a larger timeout.
2. Run `info` and check for a thunk, offcut, or data address.
3. Use a short `disassemble` query to verify instruction validity.
4. Confirm the project, image base, and dump belong to the same decrypted binary.
5. If headless still fails, obtain the complete body from the GUI Decompiler.

Trust wrapper output only when `complete: true` and the artifact is present. If correct addresses repeatedly resolve into unrelated data, compare the project image base and build, then create a fresh project rather than forcing definitions into a stale one.

# Ghidra Queries

Read this file for wrapper syntax, batch queries, address coordinates, GUI equivalents, or query failures. Use the current binary, project, and Il2CppDumper output.

## Contents

- [Query Wrapper](#query-wrapper)
- [Batch and Artifact Reads](#batch-and-artifact-reads)
- [Timeout Scaling](#timeout-scaling)
- [Search Strategy](#search-strategy)
- [Address Coordinates](#address-coordinates)
- [Query Rules](#query-rules)
- [GUI Equivalents](#gui-equivalents)
- [Failure Handling](#failure-handling)

## Query Wrapper

Use the Python wrapper for routine read-only queries. It captures Ghidra logs and results as artifacts while emitting complete query results:

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
| `decompile` | Emit and save complete C with complete evidence metadata |
| `callees` / `callers` | Inspect all direct call edges |
| `xrefs` | Inspect all references to an exact address |
| `disassemble` | Inspect the remaining instructions in the containing function |

For `decompile`, verify `complete: true` and use the reported `decompile.c` as the authoritative body. `index.json` and `semantic.tsv` are navigation aids, not replacements for reading relevant C. A missing direct callee does not exclude a vtable or function-pointer call.

Successful complete queries are cached. Use `--no-cache` for a fresh diagnostic run; failures and incomplete queries are not reused.

## Timeout Scaling

Keep a timeout as protection against a stuck decompiler, but scale it to the method. The default is suitable for ordinary methods; pass a larger value for a large dispatcher, `MoveNext`, or async state machine:

```bash
python3 /path/to/skill/scripts/ghidra_query.py query \
  --project-location /path/to/ghidra-projects \
  --project-name game --program UnityFramework \
  --timeout 600 --process-timeout 900 \
  decompile rva:0x123456
```

The wrapper always gives the outer process at least 60 seconds beyond the decompiler timeout. Batch mode also scales its outer deadline with the number of selectors. If decompilation is incomplete, retry once with a materially larger timeout based on the function size.

## Batch and Artifact Reads

Batch several exact helpers only after one outer method has identified them:

```bash
python3 /path/to/skill/scripts/ghidra_query.py batch \
  --project-location /path/to/ghidra-projects \
  --project-name game --program UnityFramework \
  decompile rva:0x111111 rva:0x222222
```

Do not use batch mode for discovery. Inspect every saved helper body separately.

Read an entire saved decompile, or request a specific region for navigation:

```bash
python3 /path/to/skill/scripts/ghidra_query.py read \
  /path/to/decompile.c
python3 /path/to/skill/scripts/ghidra_query.py read \
  /path/to/decompile.c --lines 1:120
python3 /path/to/skill/scripts/ghidra_query.py read \
  /path/to/decompile.c --around StringLiteral_123 --context 25
python3 /path/to/skill/scripts/ghidra_query.py read \
  --index /path/to/index.json --block B0002 --block-context 2
```

Artifact reads have no implicit line-count or line-length cap. Explicit `--lines`, `--around`, and `--block` selections return the complete requested region. Block reads also verify the indexed artifact.

Use raw `GhidraQuery.java` only to debug the wrapper or when the artifact path is inaccessible:

```bash
"$(brew --prefix ghidra)/libexec/support/analyzeHeadless" \
  /path/to/ghidra-projects game \
  -process UnityFramework -readOnly -noanalysis \
  -scriptPath /path/to/skill/scripts \
  -postScript GhidraQuery.java <action> <selector> [timeout-for-decompile]
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
4. Xrefs from exact imported metadata or string-literal labels.

If an exact name fails, search `script.json` for a unique method fragment, query its RVA, and use `info` to inspect aliases. Do not trust the primary Ghidra name at an ICF-folded address.

For `b__`, `g__`, `DisplayClass`, and `_d__N.MoveNext` helpers, search metadata by the outer method and numeric suffix, then query the exact RVA. Use xrefs if ownership remains unclear.

## Address Coordinates

Il2CppDumper `script.json` addresses are normally RVAs. The importer adds the Ghidra image base:

```text
VA = image base + RVA
RVA = VA - image base
```

`GhidraQuery.java` performs this conversion for `rva:` selectors. Do not add the image base twice. Verify the current project instead of assuming common Mach-O or PE bases.

## Query Rules

- Decompile one function body per query; batch only a known helper set.
- Use `info` before calls or xrefs when ownership is uncertain.
- Use disassembly only for a local offset, thunk, ICF body, or decompiler sanity check.
- Resolve strings through `stringliteral.json`.
- Use `-readOnly` for non-mutating raw Ghidra queries.

## GUI Equivalents

When headless output is incomplete or visual control flow matters:

- **Go To**: press `G` and enter the VA.
- **Symbol Tree / Search Program Text**: use an exact imported label.
- **Decompiler**: inspect and copy the complete function C.
- **References > Show References To**: inspect exact xrefs.
- **Function Call Trees**: inspect caller/callee relationships.
- **Data Type Manager**: inspect imported `*_Fields` structures.
- **Script Manager**: add the skill `scripts/` path and run the Java scripts.

## Failure Handling

For a decompiler timeout or failure:

1. Retry once with a materially larger timeout based on the function size.
2. Run `info` and check for a thunk, offcut, or data address.
3. Use a `disassemble` query to verify instruction validity.
4. Confirm the project, image base, and dump belong to the same decrypted binary.
5. If headless still fails, obtain the complete body from the GUI Decompiler.

Trust wrapper output only when `complete: true` and the artifact is present. If correct addresses repeatedly resolve into unrelated data, compare the project image base and build, then create a fresh project rather than forcing definitions into a stale one.

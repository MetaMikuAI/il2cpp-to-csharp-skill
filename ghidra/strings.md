# String Literal Resolution

Read this file when `StringLiteral_N` appears in the current decompile. Resolve only literals used by the requested method; broad content search is for explicit audit/discovery work.

## Preferred Lookup

Use the matching Il2CppDumper `stringliteral.json`:

```bash
python3 scripts/lookup_strings.py \
  --json-path /path/to/stringliteral.json \
  StringLiteral_8179 StringLiteral_17614
```

Resolve every label from a saved decompile in one bounded call:

```bash
python3 scripts/lookup_strings.py \
  --json-path /path/to/stringliteral.json \
  --from-file /path/to/decompile.c
```

The script rejects more than 100 results by default instead of silently flooding the tool output. Narrow the input or pass an explicit `--limit` for a deliberate audit.

Alternative inputs:

```bash
python3 scripts/lookup_strings.py --json-path /path/to/stringliteral.json --rva 0x4222200
python3 scripts/lookup_strings.py --json-path /path/to/stringliteral.json \
  --base 0x180000000 --va 0x184222200
```

Il2CppDumper addresses are normally RVAs. `StringLiteral_N` commonly uses one-based JSON order; if that convention fails for the current dump, resolve by RVA.

## Audit Discovery

Only when the task explicitly starts from string content:

1. Search `stringliteral.json` for the known value or fragment.
2. Read the matched RVA.
3. Query bounded Ghidra xrefs for that RVA or imported label.
4. Decompile only the relevant owners.

Do not enumerate Ghidra's global string database.

## Failure Handling

If the matching JSON is unavailable or lookup fails, keep an explicit placeholder such as `"StringLiteral_8179"` and report the label/RVA. Never infer content from function names, variables, surrounding branches, or likely log wording.

Resolve labels independently. Do not replace an unresolved literal with an empty string or generated text.

For `String.Concat`, `String.Format`, boxing, format specifiers, or interpolation lowering, read [string-formatting.md](string-formatting.md) after resolving the exact literals.

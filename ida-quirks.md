# IDA / Il2CppDumper Structural Quirks

Use this document when IDA structure layout disagrees with real type layout, or when IDA list / search tools produce misleading edge cases.

**Note: all VAs, class names, field names, structure names, and offsets in this document are game-specific examples for methodology only. For real work, use the current game's IDA output.**

---

## Offset Coordinate System

IL2CPP runtime objects have a `0x10` byte object header before `Fields` data:

```text
object + 0x00 = klass
object + 0x08 = monitor
object + 0x10 = fields start
```

Assembly expressions such as `[reg+XX]` are usually object-relative offsets. To map to a `*_Fields` structure:

```text
Fields offset = object offset - 0x10
```

This is not a separate bug. It is the coordinate system used by all field-offset checks below.
Different dump tools may record `[FieldOffset]` as object-relative or Fields-relative; use the current project's stub and IDA `*_Fields` structures to determine the convention.

---

## 1. Color32 Explicit Layout Imported as 8 Bytes

Unity's runtime `Color32` is not really 8 bytes. The issue is that IDA / Il2CppDumper imported an overlapping layout as sequential fields.

The real semantics are close to:

```c
union Color32 {
    uint32_t rgba;
    struct { uint8_t r, g, b, a; };
}; // size = 4
```

But the current IDA type may be:

```c
struct UnityEngine_Color32_Fields {
    int32_t rgba; // +0
    uint8_t r;    // +4
    uint8_t g;    // +5
    uint8_t b;    // +6
    uint8_t a;    // +7
}; // size = 8, is_union=false
```

The bug is that `rgba` and `r/g/b/a` should overlap the same 4 bytes, but IDA adds them together into 8 bytes. This pollutes every outer structure that contains `Color32` value-type fields.

Consequence: in a class containing N `Color32` fields, fields declared after that `Color32` block are shifted by `N * 4` bytes in IDA. Normalize object offsets / Fields offsets using the coordinate-system rule above before comparing.

```text
IDA Fields offset = real Fields offset + N * 4
IDA object offset = real object offset + N * 4
```

### Detection

1. Inspect `UnityEngine_Color32_Fields`. If size is 8, `rgba` is at +0, and `r/g/b/a` are at +4..+7, this import bug is present.
2. Inspect the current class C# stub / metadata `[FieldOffset]`. Real `Color32` fields should advance every 4 bytes.
3. For logic-relevant fields, correct using the real field table and `[FieldOffset]`. If needed, use a direct assembly object offset such as `[this+XX]` only as a local check. Do not use assembly as the main basis for restoring the whole method.

### Example

A controller has 12 consecutive `Color32` fields:

```csharp
[FieldOffset(0x50)] Color32 phase1TitleColor;
...
[FieldOffset(0x7C)] Color32 phase3Bar2Color;
[FieldOffset(0x80)] int currentProgress;
[FieldOffset(0x84)] bool invert;
[FieldOffset(0x88)] int maxValue;
[FieldOffset(0x98)] string targetContext;
```

IDA lays out those 12 `Color32` fields as 8 bytes each, shifting later fields by `12 * 4 = 0x30`:

| Assembly Object Offset | Real Field | Possible IDA Pseudo-C |
|---|---|---|
| `[this+80h]` | `currentProgress` | `phase1Bar1Color.fields.rgba` |
| `[this+84h]` | `invert` | `phase1Bar1Color.fields.r` |
| `[this+88h]` | `maxValue` | `phase1Bar2Color.fields.rgba` |
| `[this+98h]` | `targetContext` | `phase2Bar2Color` |
| `[this+A0h]` | `targetProgress` | `phase3Bar1Color.fields.rgba` |

Restore field names from real `[FieldOffset]` and structure layout. Assembly offsets are only local confirmation. IDA pseudo-field names are a side effect of the wrong type layout.

---

## 2. Generic Base-Class Field Offset Drift

When a class inherits from a generic base such as `UIPanelParam<TOpen, TClose>`:

- IDA may use the generic structure definition where each type parameter is represented as `Il2CppObject*`, usually 8 bytes.
- If the actual specialization replaces a type parameter with a value type larger than 8 bytes, every later field shifts.

```text
drift = sizeof(actual type) - 8
```

### Example

For a derived class inheriting from a generic base where one actual value type is 16 bytes, the drift is 8 bytes. Fields declared by the derived class may appear one field slot off in IDA.

Verification: normalize object / Fields offsets, then compare with the C# `[FieldOffset]` table.

This does not apply when IDA has a fully resolved specialized structure. Check by searching IDA local types for the specialized structure name.

---

## 3. Finding Async / Coroutine MoveNext

`list_functions` cannot be trusted for filtering. `list_globals_filter` can search symbol fragments. To locate `MoveNext` from a wrapper:

- Read the wrapper's tail `jmp` target when present.
- Decode rel32 if needed: `target = address_of_next_instruction + signed_int32(jmp_operand)`.
- Or use `get_callees(VA)` on the wrapper.

`MoveNext` is often adjacent in the function list, but do not rely on unfiltered `list_functions`.

---

## 4. Search Tool Notes

Full tool rules live in [ida-usage.md](ida-usage.md). This section records only tool behavior quirks:

| Tool | Behavior |
|---|---|
| `list_functions(filter=...)` | Filter is ignored; it returns from address 0 |
| `list_globals_filter(filter=...)` | Works normally |
| `list_strings` / `list_strings_filter` | Scans all strings; too slow and too large for big games |
| Exact VA lookup | Reliable |

When IDA appears to hang while decompiling several small functions in a row, ask the user to restart IDA instead of retrying indefinitely.

---

## 5. ICF Shared Function Addresses

IL2CPP may use ICF, Identical Code Folding, to merge semantically identical method bodies and assign the same VA to many C# methods.

`get_function_by_address(VA)` returns only one of the possible names. It does not prove that the current method is that owner. Use the pseudo-C / local body behavior, not the returned owner name.

### Common ICF Patterns

| Body Feature | Meaning | C# Restoration |
|---|---|---|
| `xor edx, edx; jmp SomeBase$$_ctor` | Empty constructor that only calls base | Empty C# constructor |
| `xor edx, edx; jmp UnityEngine_ScriptableObject$$_ctor` | Empty ScriptableObject constructor | Empty constructor |
| `retn` only | Empty virtual / override | Empty method body |
| `mov rax, [rcx+XX]; retn` | Pure field getter | Auto-property `{ get; }` |
| Base-field writes followed by `jmp` to base constructor | Base default initialization | Derived empty constructor plus `base()` |

### Strategy

1. Do not trust the function name returned by IDA. Verify the body.
2. If the body is one of the trivial patterns above, restore by behavior and ignore unrelated owner names.
3. The owner name of an ICF body may vary between binaries, but the body pattern is stable.

---

## 6. Pseudo-Array Field-Offset Noise

If IDA types a real object pointer as `Il2CppObject *`, a base object pointer, or another too-small / wrong structure pointer, pseudo-C may contain expressions like:

```c
BYTE4(Instance[40].monitor)
LOBYTE(instance[1].klass)
*(_OWORD *)&instance[2].fields.debugLabel
```

These are usually not array accesses and not business fields named `klass` or `monitor`. IDA is expressing the real memory offset as:

```text
element size * index + member offset + BYTE/WORD/DWORD extra offset
```

### Formula

```text
object offset = index * sizeof(pseudo element type) + member offset + extra byte offset
```

Common built-in member offsets:

| Pseudo Field | Member Offset |
|---|---:|
| `klass` | `0x0` |
| `monitor` | `0x8` |
| `fields` | `0x10` |

`BYTE4(x)` means add `4` to the address of `x`; `LOBYTE(x)` adds `0`; `BYTE1(x)` adds `1`.
`*(_OWORD *)&...` is a 16-byte block copy and does not imply a matching source field name.

### Example: `BYTE4(Instance[40].monitor)`

If the pseudo element type is `Il2CppObject`, size `0x10`:

```text
object offset = 0x28 * 0x10 + 0x8 + 0x4 = 0x28C
Fields offset = 0x28C - 0x10 = 0x27C
```

Then inspect the real type's `*_Fields`:

```text
NightScene_EventUtility_EventManager_Fields + 0x27C = _ShouldSkip_k__BackingField
```

Restore:

```csharp
if (EventManager.Instance.ShouldSkip) {
    ...
}
```

Do not write `Instance[40].monitor` or any array access.

### When to Do an Assembly Local Check

If pseudo-C contains `BYTE4(...)`, `LOBYTE(...)`, or `instance[N].klass/monitor/fields` in logic-relevant branches or assignments, you may inspect assembly once to confirm the single object offset. This is a local check only; it is not permission to reconstruct the whole method from assembly. Assembly usually shows:

```asm
cmp byte ptr [rax+28Ch], 0
mov byte ptr [rax+34h], 1
movups xmmword ptr [rbx+0D0h], xmm0
```

These `[reg+offset]` values are object offsets. Subtract `0x10`, then compare with `*_Fields` or C# stub `[FieldOffset]`.

### Helper Script

Use `scripts/field_offset.py` for arithmetic checks:

```bash
python scripts/field_offset.py --object-size 0x10 --index 0x28 --member monitor --byte-offset 4
python scripts/field_offset.py --object-offset 0x34
```

The script only computes offsets. It does not query IDA and does not decide field names. Field names must come from `analyze_struct_detailed(Type_Fields)` or Il2CppDumper stubs.

### Consecutive Block Copies

If assembly shows consecutive `movups` / `movsd` instructions:

```asm
movups xmmword ptr [rbx+68h], xmm1
movups xmmword ptr [rbx+78h], xmm2
...
```

After subtracting `0x10` from object offsets, these often copy a nested struct or a run of consecutive fields. Do not trust pseudo-C names like `instance[1].monitor` or `instance[2].fields...` literally. Restore by the real target type's `*_Fields` layout as high-level field assignments or struct copy.

---

## 7. Access-Level Drift

Il2CppDumper stubs may have inaccurate field access levels such as `private` / `protected`.
If IDA pseudo-C shows a same-assembly sibling class directly reading another component's field, but the dump stub marks it `private`, treat this as access-level drift.

Prefer restoring such fields as `internal` instead of adding reflection, wrappers, or dictionary workarounds just to satisfy a bad stub.

### Verification

If the actual access is a direct field read through `[rcx+offset]` or equivalent pseudo-C field access from another class, the original source must have been `internal` or `public`, not `private`.

---

## 8. Unity PlayableAsset / Timeline Pattern

Unity Timeline `PlayableAsset.CreatePlayable` has a fixed IL2CPP lowering pattern. Do not let temporary type annotations in IDA pseudo-C mislead the high-level restoration.

### Standard Pattern

```c
// IDA pseudo-C shape:
ScriptPlayable_object___Create(graph, 0)  // actually ScriptPlayable<TBehaviour>.Create
v_behaviour = GetBehaviour(v_playable);
v_behaviour->field1 = this->field1;       // asset field -> behaviour field
v_behaviour->field2 = this->field2;
```

### C# Restoration

```csharp
public override Playable CreatePlayable(PlayableGraph graph, GameObject owner) {
    var playable = ScriptPlayable<TBehaviour>.Create(graph, 0);
    var behaviour = playable.GetBehaviour();
    behaviour.field1 = field1;
    behaviour.field2 = field2;
    return playable;
}
```

### Common Noise

- IDA may type `GetBehaviour()` as an unrelated reference type.
- Field writes may display as `Behaviour[N].monitor` / `LOBYTE(v13[N].klass)` noise.
- Shared `object` helper names should not drive the high-level type choice.
- Prefer mapping write order back through the current `*_Behaviour` stub and `[FieldOffset]`.

### Derived Behaviour with No New Fields

If a derived behaviour adds no new fields but the asset uses `ScriptPlayable<TDerived>.Create` to carry a base effect flow, IDA may only show low-offset writes into the behaviour object. Preserve `ScriptPlayable<TDerived>.Create(...)` and map those offsets back to base initialization; do not downgrade to `ScriptPlayable<TBase>`.

---

## 9. Static Arrays and PrivateImplementationDetails

`dump.cs` entries such as `<PrivateImplementationDetails>.__StaticArrayInitTypeSize=N HASH /*Metadata offset 0x...*/` only identify the blob's metadata offset. They do not contain the actual array values.

### Strategy

- If local source files such as `global-metadata.dat` are unavailable, **do not guess** constants behind `RuntimeHelpers.InitializeArray`.
- For unresolved small static arrays, leave `// NOTE: static array constants need confirmation` and skip the exact values.
- If the array is only used for `Contains` or grouping decisions, first look for an existing high-level grouping source in the same or nearby system. Rebuilding a group dynamically is safer than guessing blob constants.

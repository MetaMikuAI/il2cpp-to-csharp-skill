# Ghidra and Il2CppDumper Structural Quirks

Use this reference when Ghidra types, addresses, or decompiler expressions disagree with IL2CPP metadata and C# stubs.

All names and offsets are examples. Verify them against the current build.

## Contents

- [1. Offset Coordinate System](#1-offset-coordinate-system)
- [2. Image Base and Il2CppDumper Addresses](#2-image-base-and-il2cppdumper-addresses)
- [3. Multiple Labels at One Function](#3-multiple-labels-at-one-function)
- [4. Thunks and Tail Calls](#4-thunks-and-tail-calls)
- [5. Explicit-Layout Value Types](#5-explicit-layout-value-types)
- [6. Generic Base-Class Drift](#6-generic-base-class-drift)
- [7. Pointer-Arithmetic and Pseudo-Array Noise](#7-pointer-arithmetic-and-pseudo-array-noise)
- [8. Block Copies and Struct Returns](#8-block-copies-and-struct-returns)
- [9. Function Starts and Offcuts](#9-function-starts-and-offcuts)
- [10. Decompiler Type Propagation](#10-decompiler-type-propagation)
- [11. Static Arrays and PrivateImplementationDetails](#11-static-arrays-and-privateimplementationdetails)
- [12. Mach-O Encryption and Stub Padding](#12-mach-o-encryption-and-stub-padding)

## 1. Offset Coordinate System

Reference-type IL2CPP objects normally have a `0x10`-byte header on 64-bit targets:

```text
object + 0x00 = klass
object + 0x08 = monitor
object + 0x10 = fields start
```

An instruction or pointer expression such as `[x0,#0x28c]`, `[rax+0x28c]`, or `*(byte *)((char *)obj + 0x28c)` is usually object-relative.

```text
Fields offset = object offset - 0x10
```

Some dump tools record `[FieldOffset]` as object-relative and others as Fields-relative. Determine the current convention from several known fields before applying the subtraction globally.

Value types embedded by value have no object header. Do not subtract `0x10` from a standalone struct offset.

## 2. Image Base and Il2CppDumper Addresses

Il2CppDumper `script.json` addresses are normally RVAs. `ApplyIl2CppSymbols.java` adds Ghidra's image base.

If a method label lands in invalid memory:

1. Compare the Ghidra image base with the loaded PE/ELF/Mach-O header.
2. Confirm the script came from the same binary and metadata pair.
3. Check whether the dumper emitted VAs instead of RVAs for this format/version.
4. Test one known method before bulk import.

Do not compensate by blindly rebasing until one known method and one known metadata label both agree.

## 3. Multiple Labels at One Function

Identical Code Folding can map many C# methods to one native body. Ghidra has one primary function symbol but can retain multiple labels at the entry.

`ghidra_query.py query ... info` returns every alias and saves the complete normalized result as an artifact. The displayed function name is not proof of source ownership.

Common folded shapes:

| Native body | Likely C# restoration |
|---|---|
| `ret` only | Empty method or accessor |
| constant zero/null return | `return null`, `false`, or zero according to the stub type |
| constant one return | `return true` or numeric one according to the stub type |
| one field load plus return | Pure getter / auto-property |
| branch to a base constructor | Empty derived constructor with `base()` |

Restore the requested member using its own stub signature plus shared body behavior.

## 4. Thunks and Tail Calls

Ghidra may represent a branch-only wrapper as a thunk, a one-block function, or a tail call.

- x86-64 often uses `jmp target`.
- ARM64 often uses `b target` after light argument setup.

Run `info` to check `thunk=true`, then query the destination. A wrapper is still useful for its source-level signature and captured arguments even when all logic lives in the destination.

Direct `callees` may omit a tail branch depending on analysis. Use local disassembly when the decompile contains no call but the function clearly forwards control.

## 5. Explicit-Layout Value Types

Unity types such as `Color32` use overlapping fields:

```c
union Color32 {
    uint32_t rgba;
    struct { uint8_t r, g, b, a; };
}; // 4 bytes
```

If a generated header or Ghidra C parser imports the overlapping members as sequential fields, it may model the type as 8 bytes. Every later field in a containing structure then drifts by 4 bytes per `Color32`.

Detection:

1. Inspect the type in Ghidra Data Type Manager.
2. Compare its size and member offsets with C# `[FieldOffset]` values.
3. Check a logic-relevant field with one native load/store offset.

For N incorrectly expanded `Color32` values:

```text
Ghidra Fields offset = real Fields offset + N * 4
```

Correct the data type or map through the real stub. Do not preserve a wrong Ghidra field name in reconstructed C#.

## 6. Generic Base-Class Drift

A generated generic base may model each type parameter as an 8-byte `Il2CppObject *`. A closed instantiation using a larger value type shifts later derived fields.

```text
drift = sizeof(actual closed value type) - 8
```

Check whether Ghidra has a truly specialized closed type before applying this correction. Prefer `[FieldOffset]` tables and actual native offsets over an open generic structure layout.

## 7. Pointer-Arithmetic and Pseudo-Array Noise

When Ghidra has the wrong pointer type, decompiler C may show:

```c
obj[40].monitor
*(byte *)((long)obj + 0x28c)
*(undefined8 *)&obj[2].fields
*(undefined1 *)(obj + 0x34)
```

These expressions do not prove source array access or business fields named `klass`, `monitor`, or `fields`.

For typed pseudo-array expressions:

```text
object offset = index * sizeof(pseudo element) + member offset + extra byte offset
```

Common IL2CPP object member offsets:

| Member | Offset |
|---|---:|
| `klass` | `0x0` |
| `monitor` | `0x8` |
| `fields` | `0x10` |

Example for `obj[40].monitor` plus four bytes with a `0x10` element size:

```text
object offset = 0x28 * 0x10 + 0x8 + 4 = 0x28c
Fields offset = 0x28c - 0x10 = 0x27c
```

Use:

```bash
python ../scripts/field_offset.py --object-size 0x10 --index 0x28 --member monitor --byte-offset 4
python ../scripts/field_offset.py --object-offset 0x28c
```

Resolve the resulting offset in Data Type Manager, `DummyDll`, or `dump.cs`. The helper performs arithmetic only.

## 8. Block Copies and Struct Returns

Ghidra may express value-type assignment as `memcpy`, `CONCAT`, vector loads/stores, or several adjacent 8/16-byte assignments.

Examples:

```asm
ldp x8, x9, [x0,#0x68]
stp x8, x9, [x1,#0x68]
```

```c
*(undefined8 *)(dst + 0x68) = *(undefined8 *)(src + 0x68);
*(undefined8 *)(dst + 0x70) = *(undefined8 *)(src + 0x70);
```

After mapping offsets, this may be one source-level struct assignment. Do not emit unrelated field assignments simply because the decompiler split the copy.

Hidden return-storage parameters and `retstr`-like patterns commonly represent a returned value type or tuple. Confirm the source signature before translating them.

## 9. Function Starts and Offcuts

Il2CppDumper's `Addresses` list helps create missing functions, but Ghidra can still merge a tail block into the preceding function or create an offcut label.

If the requested RVA resolves inside another function:

1. Check whether it is a legitimate ICF/shared tail.
2. Compare nearby `Addresses` values and native branch targets.
3. Inspect a small instruction window.
4. Avoid forcing a new function if control naturally falls into the existing body.

The bundled importer attempts to create missing functions but does not destructively clear existing code/data definitions.

## 10. Decompiler Type Propagation

One wrong function signature can contaminate callers and produce misleading field access, return widths, or argument order.

When Ghidra C conflicts with strong metadata evidence:

1. Compare the imported function signature with `DummyDll`.
2. Check whether `--signatures` was applied before types existed.
3. Correct the callee signature or parameter type in Ghidra.
4. Re-decompile the caller.

Do not rewrite C# around a clearly wrong `undefined8`/pointer type when metadata supplies the exact type.

For ICF bodies with incompatible source signatures, do not force one native function signature to represent every alias. Use the requested stub signature during restoration.

## 11. Static Arrays and PrivateImplementationDetails

`dump.cs` entries such as `<PrivateImplementationDetails>.__StaticArrayInitTypeSize=N HASH` identify a metadata blob but not its values.

- Extract values from the matching `global-metadata.dat` when available.
- Do not guess constants behind `RuntimeHelpers.InitializeArray`.
- If exact constants remain unavailable, leave a clear unresolved note instead of manufacturing an array.

## 12. Mach-O Encryption and Stub Padding

For App Store binaries, inspect `LC_ENCRYPTION_INFO_64`:

- `cryptid = 0`: the protected range is marked decrypted
- nonzero `cryptid`: Ghidra will decompile ciphertext unless the process image was dumped after decryption

Do not treat all odd instructions as encryption. Mach-O/Objective-C stubs may contain `brk` padding, and exception tables or literal data may sit in executable segments. Decompile defined functions and code sections rather than linearly decoding an entire encrypted page range.

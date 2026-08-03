# IL2CPP Memory and Initialization Helpers

Read this file only after [helpers.md](helpers.md) classifies an unknown helper as allocation, GC, boxing, or initialization machinery. Addresses differ by build; identify behavior from the current helper body and call site.

## GC Write Barrier

Signals:

- called immediately after a reference-field or static-field assignment;
- receives the destination field address, sometimes through thunks that discard the value argument;
- inner body uses card-table bit arithmetic, prefetch, or interlocked bit updates.

Restore only the C# assignment. Omit the barrier because the CLR supplies it.

## Lazy Type Initialization

Signals:

- receives a TypeInfo before static field or static method use;
- may pass a fixed mode flag into a larger loading-state helper;
- often contains interlocked operations and several initialization states.

Omit it. Preserve any visible source-level static access; CLR type initialization provides the guard.

## Object Allocation

Signals:

- receives one TypeInfo and returns an object pointer;
- reads instance size and reference-containing flags;
- interacts with allocation counters, GC registration, or runtime class initialization.

Restore `new T(...)` only after constructor calls and field initialization establish the source shape. Allocation alone proves `new T`, not constructor arguments.

## Array Allocation

Signals:

- receives element/array TypeInfo plus a length;
- calls `il2cpp_array_new_specific` or equivalent;
- result is indexed as an IL2CPP array.

Restore `new T[length]`. Preserve checked length logic visible outside the allocator.

## Boxing

Signals:

- `il2cpp_value_box` or equivalent receives TypeInfo plus the address of a value;
- result flows to `object`, formatting, reflection, or a nongeneric API.

Remove explicit runtime boxing when normal C# conversion or interpolation implies it. Preserve an explicit `(object)value` only when source-visible overload selection requires it.

## Static Class Initialization

Signals:

- preserved name such as `il2cpp_runtime_class_init`;
- one TypeInfo argument before first static access.

Omit the call. Do not omit surrounding business initialization performed by a separate method.

## Safety Check

Preserve a helper when its body reads application fields, performs domain calculations, creates source-visible values, or has side effects beyond runtime allocation/GC/type machinery. Similar argument counts alone are insufficient evidence.

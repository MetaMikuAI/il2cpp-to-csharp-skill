# IL2CPP Runtime Helper Catalog

IL2CPP inserts runtime helper calls into methods. These are implementation details, not business logic, and should usually be removed or simplified when restoring C#.

**The VAs and decompile snippets in this document come from one game and are only feature-matching examples. Helper addresses differ across games, but their internal logic, call patterns, and parameter shapes are highly stable. Identify them by decompiling and comparing against these features.**

---

## 1. GC Write Barrier

**Example VA:** `0x18033CD60` (thunk -> `0x1803544D0` -> `0x1803A0CC0`)

**Call pattern:** Appears after reference-type field assignments. Takes the field address and written value at the outer call site.

**Inner decompile feature:**

```c
signed __int64 __fastcall sub_1803A0CC0(unsigned __int64 a1)
{
    if ( dword_184425BE8 )
    {
        v1 = (__int64 *)((char *)&unk_18446D980 + 8 * (((a1 >> 12) & 0x1FFFFF) >> 6));
        _m_prefetchw(v1);
        do {
            v3 = *v1;
            result = _InterlockedCompareExchange64(v1, *v1 | (1LL << ((a1 >> 12) & 0x3F)), *v1);
        } while ( v3 != result );
    }
    return result;
}
```

**Recognition:** `_m_prefetchw` plus `_InterlockedCompareExchange64` marks a write barrier. The innermost helper may receive only the field address; thunk layers may discard the value argument.

**C# treatment:** Omit. The CLR handles GC write barriers.

---

## 2. NullReferenceException Throw Helper

**Example VA:** `0x18033D420` -> `0x180390110`

**Call pattern:** No args, or called from a failed null-check branch. Marked `__noreturn`.

**Feature:**

```c
void __noreturn sub_180390110()
{
    __int64 v0; // rax
    _BYTE v1[24]; // [rsp+20h] [rbp-18h] BYREF

    v0 = unknown_libname_6(v1);
    sub_1803900F0(v0);
}
```

**Recognition:** no args, `__noreturn`, calls exception infrastructure and a raise helper.

**C# treatment:** Omit. The CLR throws `NullReferenceException` on null dereference.

---

## 3. Type Initialization Guard

**Example VA:** `0x18033D260` -> `0x18034DF00` -> `0x1802E58A0`

**Call pattern:** One argument, usually TypeInfo, before static method or static field access.

**Middle-layer feature:**

```c
__int64 __fastcall sub_18034DF00(__int64 a1, __int64 a2)
{
    LOBYTE(a2) = 1;
    return sub_1802E58A0(a1, a2);
}
```

**Recognition:** fixed `a2 = 1`, then a large state-machine-like helper with `_InterlockedExchangeAdd64` and multiple loading states. This is IL2CPP lazy type initialization.

**C# treatment:** Omit. CLR static constructor semantics handle it.

---

## 4. Object Allocation

**Example VA:** `0x18033D3C0` -> `0x180376310`

**Call pattern:** One argument, TypeInfo / element class, returns an object pointer. Appears at `new T()`.

**Feature:**

```c
__int64 *__fastcall sub_180376310(__int64 element_class_0)
{
    sub_18034D100();
    if ( (unsigned __int8)sub_18034E740(element_class_0) )
        element_class_0 = mono_class_get_element_class_0(element_class_0);
    v2 = *(unsigned int *)(element_class_0 + 248);
    if ( (*(_BYTE *)(element_class_0 + 306) & 0x20) != 0 )
    {
        // type with references
        ...
    }
    else
    {
        // value type / no-reference type
        ...
    }
    _InterlockedIncrement64(&qword_184425428);
    ...
    il2cpp_runtime_class_init_0(element_class_0);
    return v6;
}
```

**Recognition:** accepts TypeInfo, reads type size, checks reference-containing flags, increments allocation counters, initializes class, and registers with GC as needed.

**C# treatment:** Restore as `new T()`.

---

## 5. Array Allocation

**Example VA:** `0x18033CDD0`

**Call pattern:** Two arguments, TypeInfo and length, at `new T[n]`.

**Feature:**

```c
__int64 __fastcall sub_18033CDD0(__int64 a1, unsigned int a2)
{
    return il2cpp_array_new_specific_0(a1, a2);
}
```

**Recognition:** TypeInfo plus count, direct call to `il2cpp_array_new_specific`.

**C# treatment:** Restore as `new T[n]`.

---

## 6. InvalidCastException Throw Helper

**Example VA:** `0x18033CD90`

**Call pattern:** Called when a cast check fails. Usually takes object TypeInfo and target TypeInfo, marked `__noreturn`.

**Feature:**

```c
void __fastcall __noreturn sub_18033CD90(__int64 a1, __int64 a2)
{
    __int64 v2; // rax
    __int64 v3; // rax
    _BYTE v4[40]; // [rsp+20h] [rbp-28h] BYREF

    sub_18030BA60(v4, *(_QWORD *)(*(_QWORD *)a1 + 64LL), a2);
    v2 = sub_1802DF070(v4);
    v3 = sub_18033D000(v2);
    sub_18033D3E0(v3, 0LL);
}
```

**Recognition:** two TypeInfo-like parameters, `__noreturn`, builds an exception message, then throws.
The preceding pseudo-C often checks type depth and parent matching:

```c
if (depth < klass->depth || klass->parents[depth-1] != TypeInfo)
    sub_18033CD90(obj, TypeInfo);
```

**C# treatment:** Omit. `(T)obj` throws `InvalidCastException` if it fails.

---

## 7. Type Check

**Example VA:** `0x18033CD70` -> `0x180375110`

**Call pattern:** Takes object pointer and target TypeInfo. Returns object pointer or null. Appears in `as T` / `is T`.

**Feature:**

```c
__int64 *__fastcall sub_180375110(__int64 *a1, __int64 a2)
{
    if ( !a1 )
        return 0LL;
    v4 = *a1;
    if ( (unsigned __int8)il2cpp_class_is_assignable_from_0(a2, *a1) )
        return a1;
    if ( (*(_BYTE *)(v4 + 307) & 0x10) == 0 )
        return 0LL;
    ...
    return result;
}
```

**Recognition:** `il2cpp_class_is_assignable_from_0`, interface checks, returns pointer or null.

**C# treatment:** Restore as `as T` or `is T`, depending on how the return value is used.

---

## 8. ArrayTypeMismatchException Throw Helper

**Example VAs:** `0x18033CFD0` (thunk -> `0x18038D610`) and `0x18033D3E0` (throw)

**Call pattern:** Called when array covariance assignment checks fail.

**Throw feature:**

```c
void __fastcall __noreturn sub_18038FFD0(__int64 a1)
{
    char pExceptionObject;
    sub_18038FC30();
    sub_18038BAA0(&pExceptionObject, a1);
    throw (Il2CppExceptionWrapper *)&pExceptionObject;
}
```

**Recognition:** cleanup helpers plus exception type lookup and `Il2CppExceptionWrapper` throw.
Any function containing `Il2CppExceptionWrapper` is a throw path and should normally be removed.

**C# treatment:** Omit. CLR array assignment throws `ArrayTypeMismatchException` automatically.

---

## 9. IndexOutOfRangeException Throw Helper

**Example VA:** `0x18033D410` -> `0x1803900D0`

**Call pattern:** Called when array index checks fail. No args, `__noreturn`.

**Feature:**

```c
void __noreturn sub_1803900D0()
{
    __int64 v0; // rax

    v0 = sub_18038E0A0();
    sub_18038FFD0(v0, 0LL);
}
```

**Recognition:** no args, gets exception type, then throws. Similar to null throw helper but uses index exception type.

**C# treatment:** Omit. CLR throws `IndexOutOfRangeException`.

---

## 10. Boxing

**Name:** `il2cpp_value_box`

**Example VA:** `0x18033CD40`

**Call pattern:** Two arguments: TypeInfo and address of a value type. Returns boxed object pointer. Common before `String.Format`.

**Feature:**

```c
__int64 __fastcall il2cpp_value_box(__int64 a1, __int64 a2)
{
    return il2cpp_value_box_0(a1, a2);
}
```

**Recognition:** preserved `il2cpp_value_box` name, two arguments, appears in formatting or boxing contexts.

**C# treatment:** Usually disappears when restoring interpolation.

---

## 11. Static Class Initialization

**Name:** `il2cpp_runtime_class_init`

**Example VA:** `0x18033D4C0`

**Call pattern:** One TypeInfo argument before static method / static field first access.

**Feature:**

```c
__int64 __fastcall il2cpp_runtime_class_init(__int64 a1)
{
    return il2cpp_runtime_class_init_0(a1);
}
```

**Recognition:** preserved `il2cpp_runtime_class_init` name and one TypeInfo argument.

**C# treatment:** Omit. CLR triggers static constructors automatically.

---

## Identification Workflow

When seeing an unknown `sub_xxx` call:

1. **Compare against this catalog first:** match argument count, `__noreturn`, internal call patterns, and surrounding call context.
2. **Decompile the helper body:** if no catalog entry matches, use `decompile_function(VA)`.
3. **Decide treatment:**
   - Contains `Il2CppExceptionWrapper` / `throw`: exception helper, remove.
   - Contains `_Interlocked*` plus bit operations: barrier / lock infrastructure, remove.
   - Contains `il2cpp_*` / `mono_*` internals: runtime infrastructure, usually remove.
   - Contains business logic such as non-IL2CPP string manipulation, calculations, or field access: preserve and translate.

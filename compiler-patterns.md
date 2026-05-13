# IL2CPP Compiler-Generated Pattern Recovery

This document describes how to recover common C# compiler and IL2CPP lowering patterns:
lambdas, closures, LINQ chains, named local functions, coroutine / iterator / async state machines.

**Addresses, function names, and type names here are examples only. For real analysis, use the current IDA output, Il2CppDumper stubs, and user-provided materials.**

## Table of Contents

- [1. Overall Principles](#1-overall-principles)
- [2. Symbol Pattern Quick Reference](#2-symbol-pattern-quick-reference)
- [3. Searching Delegate / Closure Targets](#3-searching-delegate--closure-targets)
- [4. No-Capture Lambdas](#4-no-capture-lambdas)
- [5. Capturing Lambdas / DisplayClass](#5-capturing-lambdas--displayclass)
- [6. Named Local Functions `g__`](#6-named-local-functions-g)
- [7. LINQ Chain Recovery](#7-linq-chain-recovery)
- [8. Generic Method Recovery](#8-generic-method-recovery)
- [9. Large Methods and Helpers](#9-large-methods-and-helpers)
- [10. Coroutine / Iterator / Async State Machines](#10-coroutine--iterator--async-state-machines)
- [11. Common Failure Modes](#11-common-failure-modes)

---

## 1. Overall Principles

When seeing compiler-generated patterns, do not immediately make IDA pseudo-C "look nicer".
First do three things:

1. Identify the outer method's real skeleton: normal control flow, locals, branches, loops, and higher-order calls.
2. Identify every delegate target: `__c`, `DisplayClass`, `b__`, `g__`, and `__9__N_M`.
3. Decompile every delegate target to confirm captured fields, parameters, return values, and side effects.

Only after the information is closed should short single-use helpers be inlined as lambdas. Shared helpers, side-effecting helpers, or helpers reused by multiple call sites should remain local functions or private methods.

---

## 2. Symbol Pattern Quick Reference

| Symbol Shape | Meaning | Restoration Direction |
|---|---|---|
| `Type.__c` | Compiler-generated singleton class for no-capture lambdas | `x => ...`, no capture |
| `__9` | Usually the singleton instance of `Type.__c` | Ignore as compiler cache |
| `__9__N_M` | Usually a static delegate cache slot for a no-capture lambda | Decompile target `b__N_M` |
| `<Outer>b__N_M` / `_Outer_b__N_M` | Anonymous lambda or anonymous delegate | Recover from delegate type and body |
| `DisplayClassN_M` | Closure object for captured variables | Fields are captured variables |
| `<Outer>g__Name|N_M` / `_Outer_g__Name_N_M` | Named local function | Prefer a C# local function |
| `<Outer>d__N.MoveNext` | Iterator / async state-machine body | Recover as a state machine |

`N` usually corresponds to the outer method's metadata number, and `M` is the helper index inside that method. Use the numbers for search and correlation only; do not infer semantics from them.

---

## 3. Searching Delegate / Closure Targets

### 3.1 Preferred Search Order

1. Inspect the type-initialization region in the outer method. It often lists `Method_Foo___c__Bar_b__N_M__` entries used by the method.
2. Look up the compiler-generated method in the dnSpy-exported DummyDll C# stubs or `script.json`; use its RVA / VA comment when available.
3. Try `get_function_by_address(VA)` or `decompile_function(VA)` for that helper.
4. If no VA is available, try `get_function_by_name` for an already visible IDA name.
5. If exact name lookup fails, use `list_globals_filter("Bar_b__N_M")` to search `Method$...` globals.
6. Use `get_xrefs_to` on the found `Method$...` global. The xref owner is often the outer method constructing the delegate, not the helper itself.
7. If these steps do not reveal the helper function VA, ask the user for the helper VA or full pseudo-C.

Do not use `list_functions`. Do not call `get_callers` on `sub_xxx` runtime helpers. Do not read raw MethodInfo / `Method$` memory to hunt for implementation pointers.

### 3.2 Name Conversion Rules

`get_function_by_name` and `Method$...` rewrite characters differently. See `ida-usage.md`. Treat name conversion as a heuristic, not the primary source of truth.
Common mappings:

| `Method$` Global | IDA Function Name |
|---|---|
| `Method$Foo.__c._Bar_b__N_M()` | `Foo.__c$$_Bar_b__N_M` |
| `Method$Foo.__c__DisplayClassX_Y._Bar_b__N()` | `Foo.__c__DisplayClassX_Y$$_Bar_b__N` |
| `Method$Foo._Bar_g__Name_N_M()` | `Foo$$_Bar_g__Name_N_M` |

If the inferred name fails, use shorter search fragments such as `Bar_b__N_M`, `DisplayClassX_Y`, or the local function name. Then prefer DummyDll / `script.json` VA lookup over additional guessed name variants.

`Method$...` is only a naming and xref anchor. It is not a promise that the implementation pointer can be recovered by reading the MethodInfo object's raw bytes.

---

## 4. No-Capture Lambdas

### 4.1 IDA Signals

No-capture lambdas usually have a fixed cache pattern:

```c
cached = Type___c_TypeInfo->static_fields->__9__N_M;
if (!cached) {
    target = Type___c_TypeInfo->static_fields->__9;
    cached = new Func<...>(target, Method_Type___c__Outer_b__N_M__);
    Type___c_TypeInfo->static_fields->__9__N_M = cached;
    write_barrier(&Type___c_TypeInfo->static_fields->__9__N_M, cached);
}
Enumerable.Where(source, cached, Method_Enumerable_Where_...);
```

### 4.2 Recovery Steps

1. Record the delegate type, for example `System_Func_Product__bool__TypeInfo` means `Func<Product, bool>`.
2. Decompile the target function referenced by `Method_Type___c__Outer_b__N_M__`.
3. Use the target function parameters and return value to determine the lambda shape.
4. If the body is short and used only in the current expression, inline it as a lambda.
5. If the target has complex side effects or is reused by multiple outer methods, keep a named helper.

### 4.3 Example Shape

```c
bool __c___RefreshFund_b__26_1(__c *this, Product *x) {
    return x->fields.productType == 3;
}
```

Restoration:

```csharp
x => x.productType == SomeEnumValue
```

Confirm enum values from stubs. Do not name them from the numeric value alone.

---

## 5. Capturing Lambdas / DisplayClass

### 5.1 IDA Signals

Capturing lambdas allocate a `DisplayClass`:

```c
display = new Type.__c__DisplayClassN_M();
display->__4__this = this;
display->arg = arg;
display->local = local;
delegate = new Func<...>(display, Method_Type___c__DisplayClassN_M__Outer_b__K__);
```

Field assignments are the capture list. `__4__this` is the captured outer `this`; other fields usually correspond to captured parameters or locals.

### 5.2 Recovery Steps

1. Restore where the outer method allocates the `DisplayClass`.
2. List captured fields in assignment order: `__4__this`, parameters, locals, cached delegates, and so on.
3. Decompile every `DisplayClass...b__` target.
4. Replace `this->fields.X` in helper bodies with the corresponding captured variable.
5. If a DisplayClass field stores a delegate cache, that means the closure reuses a lambda. Do not mistake it for a business field.

### 5.3 Constraints

- Do not rename a DisplayClass field into a semantic variable unless stubs or outer assignments confirm it.
- Do not turn a capturing lambda into a no-capture lambda. If there is a DisplayClass, capture semantics exist.
- Do not delete closure side effects. Closure methods often mutate captured queues, lists, or state flags.

---

## 6. Named Local Functions `g__`

### 6.1 IDA Signals

Named local functions usually appear in MethodInfo names:

```c
Method_Type__Outer_g__OnMoveFinish_159_1__
Method_Type__Outer_g__OnPatientDepleted_159_2__
```

IDA function names often look like:

```text
Type$$Outer_g__OnMoveFinish_159_1
```

If the local function accesses outer `this`, delegate construction usually targets the outer instance:

```c
new Action<T>(this, Method_Type__Outer_g__OnMoveFinish_159_1__)
```

### 6.2 Recovery Strategy

1. Prefer a C# local function over an anonymous lambda because the original name is preserved.
2. If `g__A` constructs a delegate to `g__B`, restore this as local-function calls or nested callback registration.
3. If the local function is passed as a callback, a method group or lambda can both be valid; prefer the named method group when a name exists.

### 6.3 Example Shape

```c
void Outer_g__OnMoveFinish(thisObj, group) {
    group.OnStopInQueueCallback?.Invoke(group);
    callback = new Action<Group>(thisObj, Method_Outer_g__OnPatientDepleted);
    thisObj.AddToPatientCountdown(group, callback);
}

void Outer_g__OnPatientDepleted(thisObj, guest) {
    thisObj.RemoveFromPatientCountdown(guest);
    guest.MoveToSpawn();
}
```

Restoration:

```csharp
void OnMoveFinish(GuestGroupController group) {
    group.OnStopInQueueCallback?.Invoke(group);
    AddToPatientCountdown(group, OnPatientDepleted);
}

void OnPatientDepleted(GuestGroupController guest) {
    RemoveFromPatientCountdown(guest);
    guest.MoveToSpawn();
}
```

---

## 7. LINQ Chain Recovery

### 7.1 Recognizing LINQ Chains

The type-initialization region often lists methods used in the chain:

```c
Method_System_Linq_Enumerable_Select_...
Method_System_Linq_Enumerable_Where_...
Method_System_Linq_Enumerable_ToArray_...
Method_System_Linq_Enumerable_Sum_...
Method_System_Linq_Enumerable_All_...
Method_System_Linq_Enumerable_First_...
Method_System_Linq_Enumerable_Zip_...
```

The body usually looks like:

```c
seq1 = Enumerable.Select(source, selector, Method_Select_...);
seq2 = Enumerable.Where(seq1, predicate, Method_Where_...);
sum  = Enumerable.Sum(seq2, selector2, Method_Sum_...);
```

Recover by data flow from source to terminal operation, not by variable declaration order.

### 7.2 Operator Table

| IDA Call | C# Restoration | Notes |
|---|---|---|
| `Enumerable.Select(source, selector)` | `source.Select(x => ...)` | Decompile selector |
| `Enumerable.Where(source, predicate)` | `source.Where(x => ...)` | Decompile predicate |
| `Enumerable.ToArray(source)` | `.ToArray()` | Explicit materialization |
| `Enumerable.ToList(source)` | `.ToList()` | Explicit materialization |
| `Enumerable.Sum(source, selector)` | `.Sum(x => ...)` | Not `Aggregate` |
| `Enumerable.All(source, predicate)` | `.All(x => ...)` | Do not rewrite as `Count == ...` |
| `Enumerable.First(source, predicate)` | `.First(x => ...)` | Do not change to `FirstOrDefault` |
| `Enumerable.Zip(a, b, selector)` | `a.Zip(b, (x, y) => ...)` | Selector often returns a ValueTuple |
| `Enumerable.Aggregate(source, seed, func)` | `.Aggregate(seed, (a, b) => ...)` | Do not simplify to `Sum` |
| `DefaultIfEmpty(value)` | `.DefaultIfEmpty(value)` | Not equivalent to null check / `ToArray` |

### 7.3 Restoring Selectors / Predicates

Every LINQ delegate must be decompiled. Do not infer from generic type names alone.

Common short helpers:

```c
return x->fields.productType == 3;
return x->fields.productAmount;
return x->fields.m_Product;
return UnityEngine_Object__op_Inequality(x, 0LL);
```

Restoration notes:

- `Func<T, bool>` is a predicate.
- `Func<T, TResult>` is a selector.
- `Func<TFirst, TSecond, TResult>` commonly appears in `Zip`.
- If a helper returns a struct, IDA may use `retstr` and `memcpy` style. This is often just `x => x.SomeStructField`.

### 7.4 LINQ Mixed with Explicit Loops

IL2CPP may recover code as "LINQ sequence construction plus manual enumerator loop":

```c
seq = Enumerable.Select(...);
enumerator = seq.GetEnumerator();
try {
    while (enumerator.MoveNext()) {
        item = enumerator.Current;
        ...
    }
} finally {
    enumerator.Dispose();
}
```

This does not prove the source lacked `foreach`. If the loop only enumerates `seq` and the `try/finally` only disposes the enumerator, restore:

```csharp
foreach (var item in seq) {
    ...
}
```

Do not force the loop body into LINQ unless IDA explicitly shows a terminal operation such as `ToArray`, `Sum`, `First`, `All`, or `Aggregate`.

### 7.5 Outer Method Only Builds Delegates

Some outer trigger methods only construct predicates / callbacks and then call a higher-order business helper:

```c
return CompleteMissionCondition(
    currentLabel,
    filter,
    shouldBlock,
    preProcess,
    postAction,
    onFinish);
```

In this case:

1. Restore the outer delegate lambdas first.
2. Decompile the higher-order helper.
3. Restore LINQ chains and loops inside the helper.
4. Do not move helper-internal LINQ back into the outer method unless the original method is only a wrapper.

---

## 8. Generic Method Recovery

Generic methods are often easier to recover from signatures and call sites than from the exact native function body. IL2CPP may share one native implementation across multiple reference-type instantiations, and IDA may display `object`, `Il2CppObject*`, or generic MethodInfo names even when the source was strongly typed.

### 8.1 Recovery Principles

1. Recover the source-level generic shape from DummyDll / dnSpy stubs first, such as `T`, `TResult`, `TKey`, or `where T : ...`.
2. At each call site, infer closed type arguments from MethodInfo names, generic API names, delegate types, return assignment targets, and surrounding casts.
3. Do not rewrite a generic method as `object` just because IDA shows shared `object` / `Il2CppObject*` lowering.
4. Do not invent constraints. Keep constraints only if they appear in the stub, metadata, or are required by calls in the pseudo-C, such as `new T()` / `typeof(T)` / interface calls.
5. If a generic method body only uses runtime helpers such as type checks, boxing, or array allocation, restore the high-level generic operation rather than the helper plumbing.

### 8.2 Call-Site Type Argument Clues

Use these clues together:

| Clue | Example Meaning |
|---|---|
| `Method_Foo_Bar_Tis_Product_...` / `Method$Foo.Bar<T>` | Generic method or closed instantiation anchor |
| Return value assigned to `List<Product>` / `Product[]` / `UniTask<GameObject>` | Confirms `T` or `TResult` |
| Delegate type `Func<Product, bool>` / `Action<GameObject>` | Confirms lambda parameter and return types |
| Callee name `LoadSingleLargeResourceAndShowProgress_GameObject_` | Often confirms `T = GameObject` |
| `il2cpp_array_new_specific(T_TypeInfo, n)` | `new T[n]` or `new Product[n]` depending on closed type |
| `il2cpp_value_box(T_TypeInfo, &value)` | Boxing for generic formatting or object conversion, not a reason to erase `T` |

When clues disagree, prefer the C# stub signature and the typed destination in pseudo-C. If the MCP output is truncated, ask for full pseudo-C instead of resolving the generic method from call names alone.

### 8.3 Generic Delegates and LINQ

LINQ and callback-heavy methods expose generic types through delegate TypeInfo:

```c
System_Func_Product__bool__TypeInfo
System_Func_Product__int32_t__TypeInfo
System_Action_GameObject__TypeInfo
```

Use those to type lambda parameters:

```csharp
products.Where((Product x) => ...)
products.Sum((Product x) => ...)
onLoaded += (GameObject obj) => ...
```

The explicit parameter type can be omitted in final C# when obvious, but it is useful during recovery. Do not infer predicate semantics from `Func<T,bool>` alone; still decompile the helper body.

### 8.4 Shared Generic Implementations

IL2CPP may share one native body for many reference-type instantiations. This is not evidence that the source used `object`.

Restore source-level generics when:

- the DummyDll method is generic;
- call sites close it with specific types;
- the body is type-agnostic except for TypeInfo / MethodInfo plumbing;
- casts or assignments immediately recover a concrete type after the call.

Keep a concrete non-generic method only when the stub and all call sites show a concrete method.

---

## 9. Large Methods and Helpers

When a method contains many `Method_...b__...`, `Method_...g__...`, `DisplayClass...TypeInfo`, or `System_Linq_Enumerable...` references:

1. List all MethodInfo entries from the static-initialization region.
2. Classify them as no-capture lambdas, capturing lambdas, named local functions, LINQ operators, or business helpers.
3. Decompile short helpers first and annotate inputs, outputs, and side effects.
4. Return to the outer method and keep only the control-flow skeleton and higher-order calls.
5. Inline helpers or keep them as local functions as appropriate.

Do not try to produce final C# on the first pass. Large methods need a helper map first. If a required predicate / selector body cannot be located, ask the user for the missing helper instead of marking it as "unconfirmed" and continuing with guessed C#.

---

## 10. Coroutine / Iterator / Async State Machines

### 10.1 Outer Wrapper

Outer methods returning `IEnumerator` or `IEnumerable<T>` are usually just state-machine factories:

```c
stateMachine = new Type._Method_d__N();
stateMachine->__1__state = 0;      // common for IEnumerator coroutine
stateMachine->__1__state = -2;     // common for IEnumerable<T> iterator property
stateMachine->__4__this = this;
stateMachine->arg = arg;
return stateMachine;
```

Do not treat the wrapper as the method body. It only tells you:

- state-machine type name: `_Method_d__N`
- captured `this` and arguments
- initial state
- whether the return type is `IEnumerator` or `IEnumerable<T>`

If the wrapper sets `__1__state = -2` and records a thread id field, it is usually an `IEnumerable<T>` iterator. If it sets `0` and returns `IEnumerator` directly, it is usually a Unity coroutine.

`async` / `UniTask` / `Task` wrappers are also state-machine factories, but with a different shape:

```c
memset(&stateMachine.__t__builder, 0, sizeof(...));
stateMachine.__4__this = this;
stateMachine.arg = arg;
stateMachine.__1__state = -1;
Type._MethodAsync_d__N.MoveNext(&stateMachine, ...);
return stateMachine.__t__builder.Task;
```

If the wrapper has `__return_ptr retstr`, it often returns a value type such as `UniTask` / `UniTask<T>`.
Do not treat `AsyncUniTaskMethodBuilder_Start`, `MoveNext`, or builder task extraction in the wrapper as business logic. The real method body is still in `MoveNext`.

### 10.2 Locating `MoveNext`

Preferred order:

1. Derive the state-machine name from the wrapper TypeInfo, for example `Type._FollowTargetCoroutine_d__54_TypeInfo`.
2. Try `get_function_by_name("Type._FollowTargetCoroutine_d__54$$MoveNext")`.
   For async, derive `_MethodAsync_d__N` from wrapper local type or `Method_...Start_MethodAsync_d__N`, then query `Type._MethodAsync_d__N$$MoveNext`.
3. If the full state-machine name is unknown, search `list_globals_filter("FollowTargetCoroutine")`.
   For coroutines, searching the outer method name often finds Reset Method$ and TypeInfo entries together.
4. If naming still fails, use `get_xrefs_to` on `..._d__N_TypeInfo` or `Method$...Reset()`; the xref owner or neighboring function often exposes the real IDA name for `MoveNext`.
5. If the wrapper tail is a `jmp`, decode the target using the rel32 rule in `ida-quirks.md`.

Do not use `list_functions` to search `MoveNext`.

### 10.3 Core `MoveNext` Fields

| Field | Meaning | Restoration |
|---|---|---|
| `__1__state` | State-machine state | Non-negative state per `yield` / `await`; `-1` running; `-2` completed |
| `__t__builder` | Async method builder | `AsyncTaskMethodBuilder` / `AsyncUniTaskMethodBuilder`; remove as infrastructure |
| `__2__current` | Current yielded value | Coroutine / iterator only; assignment plus state plus return true is `yield return` |
| `__4__this` | Captured outer instance | Restore as outer method `this` |
| `arg` / parameter fields | Captured parameters | Written by wrapper |
| `__8__1` etc. | DisplayClass / locals alive across yield | Restore as locals alive across yield points |
| `_local_5__2` | Ordinary local promoted across yield | Restore as a normal local |
| `__u__1` / `__u__2` | Awaiter saved across await | Recover `await UniTask`, `await UniTask<T>`, or `await AsyncOperation` from field type and use |

`return true` means `MoveNext` paused and yielded `Current`.
`return false` means the coroutine ended or `yield break` occurred.
Async `MoveNext` does not return `bool`; on suspension it saves the awaiter, calls `AwaitUnsafeOnCompleted`, and returns. On resume, it reloads the awaiter for that state and calls `GetResult()`.

### 10.4 Recovering `yield return` from State

Typical pattern:

```c
this->__2__current = value;
write_barrier(&this->__2__current, value);
this->__1__state = 1;
return 1;
```

Restoration:

```csharp
yield return value;
```

After restoration, continue reading from the `state == 1` branch. That is the code after the `yield return`.

Multi-yield coroutines often look like:

```text
state 0: yield A; state = 1; return true
state 1: yield B; state = 2; return true
state 2: yield C; state = 3; return true
state 3: return false
```

Do not treat state branches as business `switch` logic. They are compiler continuation points.

### 10.5 `yield return null` and Unity Constants

`__2__current = 0LL; state = N; return true` usually means:

```csharp
yield return null;
```

If `__2__current` comes from a static field, such as `UnityCoroutineExtension.HalfSecondDelay`, preserve it:

```csharp
yield return UnityCoroutineExtension.HalfSecondDelay;
```

If `__2__current` is another `IEnumerator` result, such as `LerpPosition(...)` or `InstantiateTimedC(...)`, restore:

```csharp
yield return LerpPosition(...);
yield return InstantiateTimedC(...);
```

### 10.6 Looping Coroutines

Looping coroutines repeatedly yield with the same state:

```c
if (state > 1) return false;
state = -1;
if (!condition) return false;
body();
__2__current = null;
state = 1;
return true;
```

Restoration:

```csharp
while (condition) {
    body();
    yield return null;
}
```

To decide whether this is a loop, check whether resuming from `state == 1` re-enters the same condition and body. Do not write a one-shot `if`.

### 10.7 `IEnumerable<T>` Iterator Properties

`IEnumerable<T>` `MoveNext` may be a large switch where each case constructs a `ValueTuple`, writes `__2__current`, sets the next state, and returns true.

Example shape:

```c
case 0:
  current = (kind0, button0, panel0);
  state = 1;
  return true;
case 1:
  current = (kind1, button1, panel1);
  state = 2;
  return true;
...
default:
  return false;
```

Restoration:

```csharp
yield return (kind0, button0, panel0);
yield return (kind1, button1, panel1);
```

If the wrapper starts with state `-2` and records a thread id, still restore it as an iterator property. Do not rewrite it as a list construction unless the source explicitly built a collection.

### 10.8 Async / Await State Machines

Async `MoveNext` static-initialization regions usually list MethodInfo entries like:

```text
Method_AsyncUniTaskMethodBuilder_AwaitUnsafeOnCompleted_...
Method_UniTask_Awaiter_T__GetResult__
Method_UniTask_Awaiter_T__get_IsCompleted__
Method_UniTask_T__GetAwaiter__
```

Recover each await point by block:

1. Find the await expression. It is usually a business method returning `UniTask` / `UniTask<T>`, followed by `GetAwaiter()`.
2. Check `IsCompleted`: if already complete, control falls through to continuation; otherwise, the awaiter is saved.
3. Suspension block shape: `__1__state = N`, `__u__K = awaiter`, `AwaitUnsafeOnCompleted(..., this, ...)`, `return`.
4. Resume block shape: reload `__u__K`, clear the field, set `__1__state = -1`, call `GetResult()`, continue with post-await business logic.
5. End-of-method `__1__state = -2`, `runnerPromise`, and builder completion notifications are async infrastructure; restore them as normal return or method end.

Example restoration:

```csharp
var value = await LoadSingleLargeResourceAndShowProgress<GameObject>(map);
Initialize(data, value);
```

Do not write `IStateMachineRunnerPromise`, source/token checks, `sub_180004110`, or awaiter scheduling details back to C#. They are only used to decide whether await completed or suspended.

### 10.9 DisplayClass in Async

Async state machines may promote closures or locals into fields. For example, state-machine field `__8__1` may hold a `DisplayClass` that survives across await:

```c
this->__8__1 = new DisplayClass1_0();
this->__8__1->__4__this = this->__4__this;
this->__8__1->specialNPCInteractData = this->specialNPCInteractData;
...
this->__8__1->prefabHandle = awaiter.GetResult();
new Action(this->__8__1, Method_DisplayClass_b__0);
```

Restore `__8__1` as a closure local alive across await, then decompile `DisplayClass...b__` / `g__` helpers. Do not treat it as a business object field, and do not move captured assignments before their actual await point.

### 10.10 Huge Async Methods

Huge async `MoveNext` functions often have `switch (__1__state)` plus many repeated await templates. Do not rewrite the whole function in one pass. First build an await table:

```text
state N
awaiter field: __u__1 / __u__2
await expression: ExecuteTimed(() => LoadXAsync(), label)
continuation: counter increment or next await after GetResult()
```

Common business shape:

```c
func = new Func<UniTask>(this, Method_Type_LoadDependenciesAsync__);
task = ExecuteTimed(func, StringLiteral_N);
await task;
```

Restoration:

```csharp
await ExecuteTimed(() => LoadDependenciesAsync(), label);
```

Only do this after confirming the delegate target. If the target is `__c.__9__N_M`, decompile `b__N_M`; if the target is an instance MethodInfo, restore as a method group or lambda only after the target method is identified from pseudo-C, DummyDll / `script.json`, or a real IDA function. Do not guess the loading step from `Func<UniTask>` or MethodInfo naming alone.

If IDA output for a large `MoveNext` is truncated, ask the user to provide complete pseudo-C. `get_callees(MoveNext)` may help identify key await targets, helpers, and Unity APIs, but do not use a call list or assembly to fill missing source unless the user explicitly provides assembly and asks for assembly-based recovery.

### 10.11 DisplayClass in Coroutines

Complex coroutines often combine a state-machine object and a DisplayClass:

```c
this->__8__1 = new DisplayClass16_0();
this->__8__1->spellExecutionContext = this->spellExecutionContext;
this->__8__1->__4__this = this->__4__this;
```

Fields like `__8__1` mean the closure object must survive across a `yield`. Recovery:

1. Restore `__8__1` as a local closure variable at the start of the coroutine method.
2. Map DisplayClass fields to variables captured by local functions / lambdas.
3. Decompile `DisplayClass...b__` and `DisplayClass...g__` helpers.
4. Restore local functions, lambdas, and nested iterators in their original scope.

Do not treat state-machine field `__8__1` as a business field. It is usually a compiler-promoted local closure.

### 10.12 Local Functions and Nested Coroutines

If a local function itself contains `yield`, it generates a nested state machine:

```text
Outer.DisplayClass16_0.__OnPositiveBuffExecute_g__ThrowPlate_8_d
Outer.DisplayClass16_0.__OnPositiveBuffExecute_g__ThrowPlate_8_d$$MoveNext
```

Strategy:

1. Restore the outer coroutine `MoveNext` sequence and yields first.
2. Restore `g__Name` helpers as local functions.
3. If `g__Name` returns `IEnumerator`, analyze its `_g__Name_..._d$$MoveNext`.
4. `yield break` in nested coroutines often appears as a branch directly returning false.

For this composite pattern, do not inline every helper at once. First build:

```text
outer coroutine state machine
DisplayClass captured fields
ordinary lambda helpers
local function helpers
nested coroutine state machine
```

Then assemble C#.

### 10.13 LINQ in Coroutines

When `Enumerable.Where/Any/Select/...` appears inside coroutine `MoveNext`, still apply LINQ rules. Watch scope:

- If a LINQ predicate uses DisplayClass fields, it captured coroutine locals.
- If LINQ is inside a nested coroutine state machine, do not lift it to the outer coroutine.
- If `Any()` is followed by a business extension like `RandomSelectOne()`, preserve the data-flow chain.

Example shape:

```csharp
var bevs = RunTimeAlbum.GetAlbumBevsOrderByDatabase()
    .Where(x => x.Id != 0 && x.Level == level);
if (bevs.Any()) {
    var bev = bevs.RandomSelectOne();
    ...
}
```

### 10.14 State-Machine Decompile Failure

Complex `MoveNext` functions can be truncated, have bad local variable allocation, or contain field-name noise. In that case:

1. Use the wrapper and TypeInfo to confirm the state-machine type.
2. Retry `decompile_function(MoveNext)` once to rule out transient failure.
3. If MCP output is truncated, ask the user to copy the full `MoveNext` pseudo-C from IDA.
4. `get_callees(MoveNext)` may list key business calls, LINQ, helpers, and Unity APIs, but cannot replace complete pseudo-C.

Do not fill missing state branches from experience just because the function "looks like a coroutine."

---

## 11. Common Failure Modes

| Failure | Correct Handling |
|---|---|
| Seeing `__9__N_M` and ignoring the lambda body | Decompile `b__N_M` |
| Guessing a condition from `Func<T,bool>` | Condition comes only from helper body |
| Simplifying `Aggregate` to `Sum` | Preserve `Aggregate` lambda |
| Changing `First` to `FirstOrDefault` | Only if IDA calls `FirstOrDefault` |
| Forcing a LINQ-created sequence plus `foreach` into one chain | Merge only when a terminal operation is explicit |
| Treating `DisplayClass` as a business class | It is a closure object; fields are captures |
| Rewriting `g__Name` as an anonymous lambda | Prefer local function when a name exists |
| Giving up when `get_function_by_name` fails | Check DummyDll / `script.json` for the helper RVA, then use `Method$` search / xrefs as anchors |
| Reading raw MethodInfo bytes to find a helper pointer | Never do this; ask for the helper VA / pseudo-C if metadata and xrefs do not expose it |
| Rewriting shared generic instantiations as `object` | Preserve source-level generic type parameters and close them at call sites |
| Inventing generic constraints | Use only constraints from stubs, metadata, or operations visible in pseudo-C |
| Treating an async wrapper as method body | Wrapper only initializes the state machine; real logic is in `MoveNext` |
| Writing `AwaitUnsafeOnCompleted` / `runnerPromise` into C# | Scheduling infrastructure; restore as `await` |

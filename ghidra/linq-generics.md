# LINQ and Generic Recovery

Read this file when decompiler C contains `System.Linq.Enumerable`, generic MethodInfo labels, generic delegate TypeInfo, or shared generic native bodies.

## LINQ Workflow

1. Follow data flow from the source sequence through each operator to the terminal operation.
2. Identify every selector, predicate, accumulator, and result selector from its delegate TypeInfo and MethodInfo.
3. Decompile every delegate body. Generic types alone establish shape, not semantics.
4. Preserve operator identity and evaluation order.
5. Restore explicit materialization and loops only where the decompile shows them.

## Operator Map

| Native call | C# form | Constraint |
|---|---|---|
| `Select(source, selector)` | `source.Select(...)` | Decompile selector |
| `Where(source, predicate)` | `source.Where(...)` | Decompile predicate |
| `ToArray` / `ToList` | `.ToArray()` / `.ToList()` | Preserve materialization |
| `Sum(source, selector)` | `.Sum(...)` | Do not rewrite as `Aggregate` |
| `All(source, predicate)` | `.All(...)` | Do not replace with counting |
| `First(source, predicate)` | `.First(...)` | Do not change to `FirstOrDefault` |
| `Zip(a, b, selector)` | `a.Zip(b, ...)` | Confirm result selector and tuple shape |
| `Aggregate(source, seed, func)` | `.Aggregate(seed, ...)` | Do not simplify to `Sum` |
| `DefaultIfEmpty(value)` | `.DefaultIfEmpty(value)` | Preserve the supplied default |

Recover a sequence built by LINQ and consumed through an enumerator as `foreach` only when the `try/finally` solely implements enumerator disposal. Keep the loop body explicit. Do not force it into another LINQ operator.

If an outer method only builds delegates and calls a higher-order business helper, restore its delegates, then decompile that helper. Do not move helper-internal LINQ into the wrapper.

## Delegate Shapes

- `Func<T,bool>` identifies a predicate signature, not its condition.
- `Func<T,TResult>` identifies a selector.
- `Func<T1,T2,TResult>` commonly identifies `Zip` or `Aggregate` logic.
- Struct returns may appear through hidden return storage or block copies; confirm the source type from stubs.

## Generic Types

Recover the source generic declaration and constraints from `DummyDll` or `dump.cs` first. Then close type arguments using several agreeing clues:

- generic MethodInfo labels;
- delegate TypeInfo;
- typed assignment destinations;
- surrounding casts;
- closed API names;
- `T_TypeInfo` used by allocation, boxing, or runtime type checks.

IL2CPP may share one native body across reference-type instantiations. `Il2CppObject*`, `undefined8`, boxing, or a shared entry point is not evidence that the C# source used `object`.

Do not invent constraints. Retain only constraints found in metadata/stubs or required by visible operations such as `new T()`, `typeof(T)`, or interface dispatch.

## Validation

- Confirm every enum label from the stub rather than a numeric guess.
- Keep `Aggregate`, `First`, materialization, and supplied defaults exact.
- Preserve explicit loops mixed with LINQ.
- Decompile all callbacks that affect a result or side effect.
- If the decompile is incomplete, do not recover generic behavior from call names alone.

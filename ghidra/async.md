# Async State-Machine Recovery

Read this file for `Task`, `UniTask`, async builders, awaiter fields, or non-boolean `_d__N$$MoveNext` methods.

## Find the Business Body

An async wrapper initializes a state machine, copies `this` and arguments, sets state `-1`, invokes builder `Start`, and returns the builder's task. Treat the wrapper as ownership/signature evidence. Business logic lives in the state machine's `MoveNext`.

Use the wrapper TypeInfo or builder `Start<..._d__N>` MethodInfo to locate the exact `MoveNext` RVA in `script.json`. Do not reconstruct the method from the wrapper.

## Core Fields

| Field | Meaning |
|---|---|
| `__1__state` | Await continuation state |
| `__t__builder` | Async builder infrastructure |
| `__4__this` and parameter fields | Captured receiver and arguments |
| `__u__N` | Awaiter saved across suspension |
| `__8__N` / `_local_5__N` | Closure or local surviving an await |

## Recover Each Await

For each state, identify this complete pattern:

1. A business expression returns an awaitable and `GetAwaiter()` is called.
2. `IsCompleted` branches either to immediate continuation or suspension.
3. Suspension stores the awaiter, assigns a state, calls `AwaitUnsafeOnCompleted`, and returns.
4. Resume reloads and clears the awaiter, restores state `-1`, calls `GetResult()`, and continues.

Restore the expression as `await ...`. Remove builder scheduling, runner promises, source/token checks, and completion plumbing only after the full pattern is confirmed.

At normal completion, state `-2` and builder completion calls restore to a normal return or method end. Preserve exceptions and catches only when the decompile shows source-visible behavior rather than builder plumbing.

## Closures and Callbacks

A `DisplayClass` stored in the state machine is a closure local alive across await. Preserve the actual assignment order around await points. Decompile every referenced `b__` or `g__` target using [lambdas-closures.md](lambdas-closures.md).

For a delegate passed to a timing/loading helper, confirm its target before restoring a lambda or method group. `Func<UniTask>` alone does not identify the business operation.

## Large Async Methods

Build an await table before producing final C#:

```text
state | awaiter field | awaited expression | GetResult type | continuation side effects
```

Use `index.json` only to navigate to state and control-flow regions. Read every await, continuation, catch/finally region, and return path from `decompile.c`. A callee list cannot fill a missing state.

## Failure Handling

Retry an incomplete `MoveNext` once with a larger timeout. Check the exact state-machine type, binary/dump match, and function entry. If it remains incomplete, obtain full GUI decompiler C; do not infer missing await states from repeated templates.
